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

# gmond python module for collection ZFS ARC stats.  Based on the
# arcstat command line tool: http://github.com/mharsch/arcstat

import abc
import copy
import decimal
import logging
import logging.handlers
import optparse
import time
import sys

log = None

METRIC_PREFIX = 'zfs_arc_'

DESCRIPTION_SKELETON = {
    'name'        : 'XXX',
    'time_max'    : 60,
    'value_type'  : 'uint', # (string, uint, float, double)
    'format'      : '%d', #String formatting ('%s', '%d','%f')
    'units'       : 'XXX',
    'slope'       : 'both',
    'description' : 'XXX',
    'groups'      : 'zfs_arc'
    }


METRICS = [
    {'name': 'hits',
     'description': 'ARC reads per second',
     'units': 'hits/s'},
    {'name': 'misses',
     'description': 'ARC misses per second',
     'units': 'misses/s'},
    {'name': 'read',
     'description': 'Total ARC accesses per second',
     'units': 'reads/s'},
    {'name': 'hit_percent',
     'description': 'ARC Hit percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'miss_percent',
     'description': 'ARC miss percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'dhit',
     'description': 'Demand Data hits per second',
     'units': 'hits/s'},
    {'name': 'dmis',
     'description': 'Demand Data misses per second',
     'units': 'misses/s'},
    {'name': 'dh_percent',
     'description': 'Demand Data hit percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'dm_percent',
     'description': 'Demand Data miss percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'phit',
     'description': 'Prefetch hits per second',
     'units': 'hits/s'},
    {'name': 'pmis',
     'description': 'Prefetch misses per second',
     'units': 'misses/s'},
    {'name': 'ph_percent',
     'description': 'Prefetch hits percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'pm_percent',
     'description': 'Prefetch miss percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'mhit',
     'description': 'Metadata hits per second',
     'units': 'hits/s'},
    {'name': 'mmis',
     'description': 'Metadata misses per second',
     'units': 'misses/s'},
    {'name': 'mread',
     'description': 'Metadata accesses per second',
     'units': 'accesses/s'},
    {'name': 'mh_percent',
     'description': 'Metadata hit percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'mm_percent',
     'description': 'Metadata miss percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'size',
     'description': 'ARC Size',
     'units': 'bytes'},
    {'name': 'c',
     'description': 'ARC Target Size',
     'units': 'bytes'},
    {'name': 'mfu',
     'description': 'MFU List hits per second',
     'units': 'hits/s'},
    {'name': 'mru',
     'description': 'MRU List hits per second',
     'units': 'hits/s'},
    {'name': 'mfug',
     'description': 'MFU Ghost List hits per second',
     'units': 'hits/s'},
    {'name': 'mrug',
     'description': 'MRU Ghost List hits per second',
     'units': 'hits/s'},
    {'name': 'eskip',
     'description': 'evict_skip per second',
     'units': 'hits/s'},
    {'name': 'mtxmis',
     'description': 'mutex_miss per second',
     'units': 'misses/s'},
    {'name': 'rmis',
     'description': 'recycle_miss per second',
     'units': 'misses/s'},
    {'name': 'dread',
     'description': 'Demand data accesses per second',
     'units': 'accesses/s'},
    {'name': 'pread',
     'description': 'Prefetch accesses per second',
     'units': 'accesses/s'},
    {'name': 'l2hits',
     'description': 'L2ARC hits per second',
     'units': 'hits/s'},
    {'name': 'l2misses',
     'description': 'L2ARC misses per second',
     'units': 'misses/s'},
    {'name': 'l2read',
     'description': 'Total L2ARC accesses per second',
     'units': 'reads/s'},
    {'name': 'l2hit_percent',
     'description': 'L2ARC access hit percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'l2miss_percent',
     'description': 'L2ARC access miss percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'l2size',
     'description': 'Size of the L2ARC',
     'units': 'bytes'},
    {'name': 'l2asize',
     'description': 'Actual (compressed) size of the L2ARC',
     'units': 'bytes'},
    {'name': 'l2bytes',
     'description': 'bytes read per second from the L2ARC',
     'units': 'bytes/s'},
    ]

def sbool(s):
    """ convert a string that is probably supposed to be a boolean
    value into an actual bool type."""
    if isinstance(s, str):
        return s.lower() in ['true', '1', 't', 'y', 'yes', 'yeah', 'yup', 'certainly', 'uh-huh']
    else:
        return bool(s)


##### Data Access
class ArcStats(object):
    __metaclass__ = abc.ABCMeta
    
    kstats = None
    kstats_last = None
    now_ts = -1
    last_ts = -1
    values = {}

    def __init__(self, min_poll_seconds):
        self.min_poll_seconds = int(min_poll_seconds)

    def should_update(self):
        return (self.now_ts == -1 or time.time() - self.now_ts  > self.min_poll_seconds)

    def k_name(self, name):
        return name.split(METRIC_PREFIX)[-1]
    
    @abc.abstractmethod
    def update_kstats(self):
        raise NotImplementedError()

    # Primarily for debugging
    def _get_raw_metric_value(self, name, last=False):
        try:
            key = self.k_name(name)
            if last is False:
                return self.kstats[key]
            else:
                return self.kstats_last[key]
        except KeyError as e:
            log.warn('unable to find metric %s/%s (last:%s)' % (name, self.k_name(name), last))
            return None


    def get_metric_value(self, name):
        if self.should_update() is True:
            self.update_kstats()
            self.calculate_all()
        if self.kstats is None or self.kstats_last is None or len(self.values) == 0:
            log.debug('Not enough kstat data has been collected yet now_ts:%r  last_ts:%r' % (self.now_ts, self.last_ts))
            return None
        val = self.values[self.k_name(name)]
        log.debug('on call_back got %s = %r' % (self.k_name(name), val))
        if NAME_2_DESCRIPTOR[name]['value_type'] == 'uint':
            return long(val)
        else:
            return float(val)

    def l2exist(self):
        return self.kstats is not None and'l2_size' in self.kstats

    def calculate_all(self):
        if self.kstats is None or self.kstats_last is None:
            return None
        snap = {}
        for key in self.kstats:
            snap[key] = self._get_raw_metric_value(key) - self._get_raw_metric_value(key, last=True)
        v = dict()
        sint = self.now_ts - self.last_ts
        v["hits"] = snap["hits"] / sint
        v["misses"] = snap["misses"] / sint
        v["read"] = v["hits"] + v["misses"]
        v["hit_percent"] = 100 * v["hits"] / v["read"] if v["read"] > 0 else 0
        v["miss_percent"] = 100 - v["hit_percent"] if v["read"] > 0 else 0

        v["dhit"] = (snap["demand_data_hits"] + snap["demand_metadata_hits"]) / sint
        v["dmis"] = (snap["demand_data_misses"] + snap["demand_metadata_misses"]) / sint

        v["dread"] = v["dhit"] + v["dmis"]
        v["dh_percent"] = 100 * v["dhit"] / v["dread"] if v["dread"] > 0 else 0
        v["dm_percent"] = 100 - v["dh_percent"] if v["dread"] > 0 else 0

        v["phit"] = (snap["prefetch_data_hits"] + snap["prefetch_metadata_hits"]) / sint
        v["pmis"] = (snap["prefetch_data_misses"] +
                     snap["prefetch_metadata_misses"]) / sint

        v["pread"] = v["phit"] + v["pmis"]
        v["ph_percent"] = 100 * v["phit"] / v["pread"] if v["pread"] > 0 else 0
        v["pm_percent"] = 100 - v["ph_percent"] if v["pread"] > 0 else 0

        v["mhit"] = (snap["prefetch_metadata_hits"] +
                     snap["demand_metadata_hits"]) / sint
        v["mmis"] = (snap["prefetch_metadata_misses"] +
                     snap["demand_metadata_misses"]) / sint

        v["mread"] = v["mhit"] + v["mmis"]
        v["mh_percent"] = 100 * v["mhit"] / v["mread"] if v["mread"] > 0 else 0
        v["mm_percent"] = 100 - v["mh_percent"] if v["mread"] > 0 else 0

        v["size"] = self._get_raw_metric_value("size")
        v["c"] = self._get_raw_metric_value("c")
        v["mfu"] = snap["mfu_hits"] / sint
        v["mru"] = snap["mru_hits"] / sint
        v["mrug"] = snap["mru_ghost_hits"] / sint
        v["mfug"] = snap["mfu_ghost_hits"] / sint
        v["eskip"] = snap["evict_skip"] / sint
        v["rmis"] = snap["recycle_miss"] / sint
        v["mtxmis"] = snap["mutex_miss"] / sint

        if self.l2exist():
            v["l2hits"] = snap["l2_hits"] / sint
            v["l2misses"] = snap["l2_misses"] / sint
            v["l2read"] = v["l2hits"] + v["l2misses"]
            v["l2hit_percent"] = 100 * v["l2hits"] / v["l2read"] if v["l2read"] > 0 else 0
            
            v["l2miss_percent"] = 100 - v["l2hit_percent"] if v["l2read"] > 0 else 0
            v["l2size"] = self._get_raw_metric_value("l2_size")
            v["l2asize"] = self._get_raw_metric_value("l2_asize")
            v["l2bytes"] = snap["l2_read_bytes"] / sint
        self.values = v


class LinuxArcStats(ArcStats):

    def __init__(self,  min_poll_seconds):
        super(LinuxArcStats, self).__init__(min_poll_seconds)

    def update_kstats(self):
        self.kstats_last = self.kstats
        self.last_ts = self.now_ts
        self.kstats = {}

        with open('/proc/spl/kstat/zfs/arcstats') as f:
            k = [line.strip() for line in f]

        # header
        del k[0:2]

        for s in k:
            if not s:
                continue

            name, unused, value = s.split()
            self.kstats[name] = decimal.Decimal(value)
        self.now_ts = int(time.time())


#### module functions

def metric_init(params):
    global ARC_STATS, NAME_2_DESCRIPTOR
    if log is None:
       setup_logging('syslog', params['syslog_facility'], params['log_level'])
    log.debug('metric_init: %r' % params)
    if params['os'] == 'linux':
        ARC_STATS = LinuxArcStats(params['min_poll_seconds'])
    else:
        log.error('unsupported os type: %s' % params)
        return None
    descriptors = []
    for metric in METRICS:
        d = copy.copy(DESCRIPTION_SKELETON)
        d.update(metric)
        d['name'] = METRIC_PREFIX + d['name']
        d['call_back'] = ARC_STATS.get_metric_value
        descriptors.append(d)
        if sbool(params['force_double']) is True:
            d['value_type'] = 'double'
            d['format'] = '%f'
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

    log = logging.getLogger('gmond_python_zfs_arc')
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
    params = {'os': 'linux', 'min_poll_seconds': 5, 'force_double': True}
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

