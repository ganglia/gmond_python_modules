# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE UNIVERSITY OF CALIFORNIA BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import abc
import copy
import logging
import logging.handlers
import optparse
import time
import sys

import pybindxml.reader

log = None

QUERY_TYPES = ['A', 'SOA', 'DS' 'UPDATE', 'MX', 'AAAA', 'DNSKEY', 'QUERY', 'TXT', 'PTR']

METRIC_PREFIX = 'bind_'

DESCRIPTION_SKELETON = {
    'name'        : 'XXX',
    'time_max'    : 60,
    'value_type'  : 'uint', # (string, uint, float, double)
    'format'      : '%d', #String formatting ('%s', '%d','%f')
    'units'       : 'XXX',
    'slope'       : 'both',
    'description' : 'XXX',
    'groups'      : 'bind_xml',
    'calc'        : 'scalar' # scalar
    }


METRICS = [
    {'name': 'mem_BlockSize',
     'description': '',
     'value_type': 'double',
     'format': '%f',
     'units': 'bytes'},
    {'name': 'mem_ContextSize',
     'description': '',
     'value_type': 'double',
     'format': '%f',
     'units': 'bytes'},
    {'name': 'mem_InUse',
     'description': '',
     'value_type': 'double',
     'format': '%f',
     'units': 'bytes'},
    {'name': 'mem_TotalUse',
     'description': '',
     'units': 'bytes',
     'value_type': 'double',
     'format': '%f'},
    ]


#### Data Acces

class BindStats(object):

    bind_reader = None

    stats = None
    stats_last = None
    now_ts = -1
    last_ts = -1

    def __init__(self, host, port, min_poll_seconds):
        self.host = host
        self.port = int(port)
        self.min_poll_seconds = int(min_poll_seconds)

    def short_name(self, name):
        return name.split('bind_')[1]

    def get_bind_reader(self):
        if self.bind_reader is None:
            self.bind_reader = pybindxml.reader.BindXmlReader(host=self.host, port=self.port)
        return self.bind_reader

    def should_update(self):
        return (self.now_ts == -1 or time.time() - self.now_ts  > self.min_poll_seconds)
        
    def update_stats(self):
        self.stats_last = self.stats
        self.last_ts = self.now_ts
        self.stats = {}

        self.get_bind_reader().get_stats()
        for element, value in self.get_bind_reader().stats.memory_stats.items():
            self.stats['mem_' + element] = value
        
        # Report queries as a rate of zero if none are reported
        for qtype in QUERY_TYPES:
            self.stats['query_' + qtype] = 0
        for element, value in self.get_bind_reader().stats.query_stats.items():
            self.stats['query_' + element] = value

        self.now_ts = int(time.time())


    def get_metric_value(self, name):
        if self.should_update() is True:
            self.update_stats()
        if self.stats is None or self.stats_last is None:
            log.debug('Not enough stat data has been collected yet now_ts:%r last_ts:%r' % (self.now_ts, self.last_ts))
            return None
        descriptor = NAME_2_DESCRIPTOR[name]
        if descriptor['calc'] == 'scalar':
            val = self.stats[self.short_name(name)]
        elif descriptor['calc'] == 'rate':
            val = (self.stats[self.short_name(name)] - self.stats_last[self.short_name(name)]) / (self.now_ts - self.last_ts)
        else:
            log.warn('unknokwn memtric calc type %s' % descriptor['calc'])
            return None
        log.debug('on call_back got %s = %r' % (self.short_name(name), val))
        if descriptor['value_type'] == 'uint':
            return long(val)
        else:
            return float(val)


#### module functions


def metric_init(params):
    global BIND_STATS, NAME_2_DESCRIPTOR
    if log is None:
       setup_logging('syslog', params['syslog_facility'], params['log_level'])
    log.debug('metric_init: %r' % params)
    BIND_STATS = BindStats(params['host'], params['port'], params['min_poll_seconds'])
    descriptors = []
    for qtype in QUERY_TYPES:
        METRICS.append({'name': 'query_' + qtype,
                        'description': '%s queries per second',
                        'value_type': 'double', 'format': '%f',
                        'units': 'req/s', 'calc': 'rate'})
    for metric in METRICS:
        d = copy.copy(DESCRIPTION_SKELETON)
        d.update(metric)
        d['name'] = METRIC_PREFIX + d['name']
        d['call_back'] = BIND_STATS.get_metric_value
        descriptors.append(d)
    log.debug('descriptors: %r' % descriptors)
    for d in descriptors:
        for key in ['name', 'units', 'description']:
            if d[key] == 'XXX':
                log.warn('incomplete descriptor definition: %r' % d)
        if d['value_type'] == 'uint' and d['format'] != '%d':
            log.warn('value/type format mismatch: %r' % d)
    NAME_2_DESCRIPTOR = {}
    for d in descriptors:
        NAME_2_DESCRIPTOR[d['name']] = d
    return descriptors



def metric_cleanup():
    logging.shutdown()


#### Main and Friends

def setup_logging(handlers, facility, level):
    global log

    log = logging.getLogger('gmond_python_bind_xml')
    formatter = logging.Formatter(' | '.join(['%(asctime)s', '%(name)s',  '%(levelname)s', '%(message)s']))
    if handlers in ['syslog', 'both']:
        sh = logging.handlers.SysLogHandler(address='/dev/log', facility=facility)
        sh.setFormatter(formatter)
        log.addHandler(sh)
    if handlers in ['stdout', 'both']:
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        log.addHandler(ch)
    lmap = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
        'NOTSET': logging.NOTSET
        }
    log.setLevel(lmap[level])


def parse_args(argv):
    parser = optparse.OptionParser()
    parser.add_option('--log',
                      action='store', dest='log', default='stdout', choices=['stdout', 'syslog', 'both'],
                      help='log to stdout and/or syslog')
    parser.add_option('--log-level',
                      action='store', dest='log_level', default='WARNING',
                      choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'],
                      help='log to stdout and/or syslog')
    parser.add_option('--log-facility',
                      action='store', dest='log_facility', default='user',
                      help='facility to use when using syslog')

    return parser.parse_args(argv)


def main(argv):
    """ used for testing """
    (opts, args) = parse_args(argv)
    setup_logging(opts.log, opts.log_facility, opts.log_level)
    params = {'min_poll_seconds': 5, 'host': 'asu101', 'port': 8053}
    descriptors = metric_init(params)
    try:
        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                if v is None:
                    print 'got None for %s' % d['name']
                else:
                    print 'value for %s is %r' % (d['name'], v)
            time.sleep(5)
            print '----------------------------'
    except KeyboardInterrupt:
        log.debug('KeyboardInterrupt, shutting down...')
        metric_cleanup()

if __name__ == '__main__':
    main(sys.argv[1:])

