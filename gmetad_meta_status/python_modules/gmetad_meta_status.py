#!/usr/bin/env python

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# UNIVERSITY OF CALIFORNIA BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# gmond module for collecting stats from the new gmetad status call
# and sending them back through the system.  This allows the existing
# rrdtool & gweb infrastructure to graph them, but has obvious
# downsides for monitoring when something goes wrong.  See
# https://github.com/OHamm/monitor-core/wiki/Gmetad-Internal-Metrics-(developers)
# for metrics descriptions

import collections
import copy
import json
import logging
import logging.handlers
import optparse
import sys
import time
import urllib2

log = None

METRIC_PREFIX = 'gmetad_meta_status_'

DESCRIPTION_SKELETON = {
    'name': 'XXX',
    'time_max': 60,
    'value_type': 'uint',  # (string, uint, float, double)
    'units': 'XXX',
    'slope': 'both',
    'description': '',  # See Docs
    'groups':  'gmetad_meta_status'
    }

TYPE_FORMAT = {
    'uint': '%d',
    'string': '%s',
    'double': '%f',
}

BASIC_METRICS = [
    {'name': 'check.success.time',
     'description': 'Time since last check succeeded',
     'units': 'seconds'},
    # Instance Information
    {'name': 'host',
     'value_type': 'string',
     'units': 'N/A'},
    {'name': 'gridname',
     'value_type': 'string',
     'units': 'N/A'},
    {'name': 'version',
     'value_type': 'string',
     'units': 'N/A'},
    {'name': 'boottime',
     'units': 'seconds'},
    {'name': 'uptime',
     'units': 'seconds'},
]

RAW_METRICS = [
    {'name': 'metrics.received.all',
     'value_type': 'double',
     'units': 'metrics'},
    # metrics.sent
    {'name': 'metrics.sent.all.num',
     'value_type': 'double',
     'units': 'metrics'},
    {'name': 'metrics.sent.all.totalMillis',
     'value_type': 'double',
     'units': 'ms'},
    {'name': 'metrics.sent.rrdtool.num',
     'value_type': 'double',
     'units': 'metrics'},
    {'name': 'metrics.sent.rrdtool.totalMillis',
     'value_type': 'double',
     'units': 'ms'},
    {'name': 'metrics.sent.rrdtool.lastTime',
     'value_type': 'double',
     'units': 'ms'},
    {'name': 'metrics.sent.rrdcached.num',
     'value_type': 'double',
     'units': 'metrics'},
    {'name': 'metrics.sent.rrdcached.totalMillis',
     'value_type': 'double',
     'units': 'ms'},
    {'name': 'metrics.sent.rrdcached.lastTime',
     'value_type': 'double',
     'units': 'ms'},
    {'name': 'metrics.sent.graphite.num',
     'value_type': 'double',
     'units': 'metrics'},
    {'name': 'metrics.sent.graphite.totalMillis',
     'value_type': 'double',
     'units': 'ms'},
    {'name': 'metrics.sent.graphite.lastTime',
     'value_type': 'double',
     'units': 'ms'},
    {'name': 'metrics.sent.memcached.num',
     'value_type': 'double',
     'units': 'metrics'},
    {'name': 'metrics.sent.memcached.totalMillis',
     'value_type': 'double',
     'units': 'ms'},
    {'name': 'metrics.sent.memcached.lastTime',
     'value_type': 'double',
     'units': 'ms'},
    {'name': 'metrics.sent.riemann.num',
     'value_type': 'double',
     'units': 'metrics'},
    {'name': 'metrics.sent.riemann.totalMillis',
     'value_type': 'double',
     'units': 'ms'},
    {'name': 'metrics.sent.riemann.lastTime',
     'value_type': 'double',
     'units': 'ms'},
    # metrics.summarize
    {'name': 'metrics.summarize.cluster',
     'value_type': 'double',
     'units': 'metrics'},
    {'name': 'metrics.summarize.root',
     'value_type': 'double',
     'units': 'metrics'},
    {'name': 'metrics.summarize.totalMillis',
     'value_type': 'double',
     'units': 'ms'},
    {'name': 'metrics.summarize.lastTime',
     'value_type': 'double',
     'units': 'ms'},
    # metrics.requests
    {'name': 'metrics.requests.all.num',
     'value_type': 'double',
     'units': 'requests'},
    {'name': 'metrics.requests.all.totalMillis',
     'value_type': 'double',
     'units': 'ms'},
    {'name': 'metrics.requests.interactive.num',
     'value_type': 'double',
     'units': 'requests'},
    {'name': 'metrics.requests.interactive.totalMillis',
     'value_type': 'double',
     'units': 'ms'},
    {'name': 'metrics.requests.xml.num',
     'value_type': 'double',
     'units': 'requests'},
    {'name': 'metrics.requests.xml.totalMillis',
     'value_type': 'double',
     'units': 'ms'},
    # metrics.polls
    {'name': 'metrics.polls.ok.num',
     'value_type': 'double',
     'units': 'polls'},
    {'name': 'metrics.polls.ok.totalMillis',
     'value_type': 'double',
     'units': 'ms'},
    {'name': 'metrics.polls.failed.num',
     'value_type': 'double',
     'units': 'polls'},
    {'name': 'metrics.polls.failed.totalMillis',
     'value_type': 'double',
     'units': 'ms'},
    {'name': 'metrics.polls.misses',
     'units': 'poll misses'},
    ]

RATE_METRICS = [
    {'name': 'metrics.received.rate',
     'value_type': 'double',
     'units': 'metrics/s'},
    # metrics.sent
    {'name': 'metrics.sent.all.rate',
     'value_type': 'double',
     'units': 'metrics/s'},
    {'name': 'metrics.sent.rrdtool.rate',
     'value_type': 'double',
     'units': 'metrics/s'},
    {'name': 'metrics.sent.rrdcached.rate',
     'value_type': 'double',
     'units': 'metrics/s'},
    {'name': 'metrics.sent.graphite.rate',
     'value_type': 'double',
     'units': 'metrics/s'},
    {'name': 'metrics.sent.memcached.rate',
     'value_type': 'double',
     'units': 'metrics'},
    {'name': 'metrics.sent.riemann.rate',
     'value_type': 'double',
     'units': 'metrics'},
    # metrics.summarize
    {'name': 'metrics.summarize.cluster.rate',
     'value_type': 'double',
     'units': 'metrics'},
    {'name': 'metrics.summarize.root.rate',
     'value_type': 'double',
     'units': 'metrics/s'},
    # metrics.requests
    {'name': 'metrics.requests.all.rate',
     'value_type': 'double',
     'units': 'requests/s'},
    {'name': 'metrics.requests.interactive.rate',
     'value_type': 'double',
     'units': 'requests/s'},
    {'name': 'metrics.requests.xml.rate',
     'value_type': 'double',
     'units': 'requests/s'},
    # metrics.polls
    {'name': 'metrics.polls.ok.rate',
     'value_type': 'double',
     'units': 'polls/s'},
    {'name': 'metrics.polls.failed.rate',
     'value_type': 'double',
     'units': 'polls/s'},
    {'name': 'metrics.polls.misses.rate',
     'units': 'misses/s'},
    ]


def flatten_dict(d, parent_key='', sep='.'):
    """ Based on
    http://stackoverflow.com/questions/6027558/flatten-nested-python-dictionaries-compressing-keys
    """
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


class GmetadStatus(object):

    now_ts = -1
    last_ts = -1
    status_d = {}

    def __init__(self, host, port, check_every):
        self.host = host
        self.port = port
        self.check_every = int(check_every)
        self.last = {}
        self.current = {'check.success.time': -1}

    def should_update(self):
        return (self.now_ts == -1 or time.time() -
                self.now_ts > self.check_every)

    def _gen_url(self):
        return 'http://%s:%s/status' % (self.host, str(self.port))

    def fetch_new_status(self):
        self.last_ts = self.now_ts
        self.last = self.current
        f = urllib2.urlopen(self._gen_url())
        blob = f.read()
        self.current = flatten_dict(json.loads(blob))
        self.now_ts = int(time.time())
        self.current['check.success.time'] = self.now_ts

    def _metric_stem(self, name):
        return '.'.join(name.split('.')[:-1])

    def _parent_count(self, name):
        if self._metric_stem(name) == 'metrics.received':
            return 'metrics.received.all'
        elif self._metric_stem(name) == 'metrics.summarize.cluster':
            return 'metrics.summarize.cluster'
        elif self._metric_stem(name) == 'metrics.summarize.root':
            return 'metrics.summarize.root'
        elif self._metric_stem(name) == 'metrics.polls.misses':
            return 'metrics.polls.misses'
        return self._metric_stem(name) + '.num'

    def _calc_rate(self, name):
        parent_count = self._parent_count(name)
        return (float(self.current[parent_count] -
                      self.last[parent_count]) /
                (self.now_ts - self.last_ts))

    def calculate_rates(self):
        if self.last_ts == -1:
            log.debug('Not enough historical data to calculate rates yet')
            return None
        for metric in RATE_METRICS:
            if metric['name'].split('.')[-1] == 'rate':
                self.current[metric['name']] = self._calc_rate(metric['name'])
            else:
                log.warn('Unknown type in RATE_METRICS: ' + metric['name'])

    def flat_name(self, name):
        return name.split(METRIC_PREFIX)[-1]

    def get_metric_value(self, name):
        if self.should_update() is True:
            try:
                self.fetch_new_status()
            except Exception:
                log.exception('Error fetching latest status:')
                return None
            try:
                self.calculate_rates()
            except Exception:
                log.exception('Error calculating rates:')
        if self.last_ts == -1 and '.rate' in name:
            return None
        val = self.current[self.flat_name(name)]
        log.debug('on call_back got %s = %r' % (self.flat_name(name), val))
        if NAME_2_DESCRIPTOR[name]['value_type'] == 'uint':
            return long(val)
        elif NAME_2_DESCRIPTOR[name]['value_type'] == 'double':
            return float(val)
        else:
            return str(val)


# Module Functions #####


def metric_init(params):
    global GMETAD_STATUS, NAME_2_DESCRIPTOR
    if log is None:
        setup_logging('syslog', params['syslog_facility'], params['log_level'])
    log.debug('metric_init: %r' % params)
    GMETAD_STATUS = GmetadStatus(params['gmetad_host'],
                                 params['gmetad_port'],
                                 params['check_every'])
    descriptors = []
    if params['metrics'] == 'basic-only':
        metrics = BASIC_METRICS
    elif params['metrics'] == 'raw':
        metrics = BASIC_METRICS + RAW_METRICS
    elif params['metrics'] == 'rate':
        metrics = BASIC_METRICS + RATE_METRICS
    else:
        metrics = BASIC_METRICS + RAW_METRICS + RATE_METRICS
    for metric in metrics:
        d = copy.copy(DESCRIPTION_SKELETON)
        d.update(metric)
        d['name'] = METRIC_PREFIX + d['name']
        d['call_back'] = GMETAD_STATUS.get_metric_value
        if d['value_type'] in TYPE_FORMAT:
            d['format'] = TYPE_FORMAT[d['value_type']]
        descriptors.append(d)
    log.debug('descriptors: %r' % descriptors)
    for d in descriptors:
        for key in ['name', 'units', 'description']:
            if d[key] == 'XXX':
                log.warn('incomplete descriptor definition: %r' % d)
    NAME_2_DESCRIPTOR = {}
    for d in descriptors:
        NAME_2_DESCRIPTOR[d['name']] = d
    return descriptors


def metric_cleanup():
    logging.shutdown()


# Main and Friends #####


def setup_logging(handlers, facility, level):
    global log
    log = logging.getLogger('gmetad_meta_metrics')
    formatter = logging.Formatter(' | '.join(['%(asctime)s',
                                              '%(name)s',
                                              '%(levelname)s',
                                              '%(message)s']))
    if handlers in ['syslog', 'both']:
        sh = logging.handlers.SysLogHandler(address='/dev/log',
                                            facility=facility)
        sh.setFormatter(formatter)
        log.addHandler(sh)
    if handlers in ['stderr', 'both']:
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
                      action='store', dest='log', default='stderr',
                      choices=['stderr', 'syslog', 'both'],
                      help='log to stderr and/or syslog')
    parser.add_option('--log-level',
                      action='store', dest='log_level', default='WARNING',
                      choices=['CRITICAL', 'ERROR', 'WARNING',
                               'INFO', 'DEBUG', 'NOTSET'],
                      help='log to stderr and/or syslog')
    parser.add_option('--log-facility',
                      action='store', dest='log_facility', default='user',
                      help='facility to use when using syslog')
    parser.add_option('--gmetad-host',
                      action='store', dest='gmetad_host', default='localhost',
                      help='gmetad host')
    parser.add_option('--gmetad-port',
                      action='store', dest='gmetad_port', default=8652,
                      help='gmetad interactive port')
    parser.add_option('--check-every',
                      action='store', dest='check_every', default=10,
                      help='how often to check for new metrics')
    parser.add_option('--metrics',
                      action='store', dest='metrics', default='all',
                      choices=['basic-only', 'raw', 'rate', 'all'],
                      help='Which metrics to collect?')
    return parser.parse_args(argv)


def main(argv):
    """ used for testing """
    (opts, args) = parse_args(argv)
    setup_logging(opts.log, opts.log_facility, opts.log_level)
    params = {'gmetad_host': opts.gmetad_host, 'gmetad_port': opts.gmetad_port,
              'check_every': int(opts.check_every),
              'metrics': opts.metrics}
    descriptors = metric_init(params)
    try:
        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                if v is None:
                    print 'got None for %s' % d['name']
                else:
                    print 'value for %s is %r' % (d['name'], v)
            time.sleep(int(opts.check_every))
            print '----------------------------'
    except KeyboardInterrupt:
        log.debug('KeyboardInterrupt, shutting down...')
        metric_cleanup()

if __name__ == '__main__':
    main(sys.argv[1:])
