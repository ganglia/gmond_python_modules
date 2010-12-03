#!/usr/bin/env python
# -*- coding: utf-8 -*-


import json
import os
import re
import sys
import time


NAME_PREFIX = 'mongodb_'
PARAMS = {
    'stats_command' : 'mongo --quiet --eval "printjson(db.serverStatus())"'
}
METRICS = {
    'time'   : 0,
    'values' : {}
}
DELTA_METRICS = {}
METRICS_CACHE_MAX = 1


def flatten(d, pre = '', sep = '_'):
    """Flatten a dict (i.e. dict['a']['b']['c'] => dict['a_b_c'])"""

    new_d = {}
    for k,v in d.items():
        if type(v) == dict:
            new_d.update(flatten(d[k], '%s%s%s' % (pre, k, sep)))
        else:
            new_d['%s%s' % (pre, k)] = v
    return new_d


def get_metrics():
    """Return all metrics"""

    global METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

        # get raw metric data
        io = os.popen(PARAMS['stats_command'])

        # clean up
        metrics_str = ''.join(io.readlines()).strip() # convert to string
        metrics_str = re.sub('\w+\((.*)\)', r"\1", metrics_str) # remove functions

        # convert to flattened dict
        fresh_metrics = flatten(json.loads(metrics_str))

        # update cache
        METRICS['time'] = time.time()
        for name,value in fresh_metrics.items():
            METRICS['values'][name] = value

    return METRICS


def get_value(name):
    """Return a value for the requested metric"""

    metrics = get_metrics()

    try:
        name = name[len(NAME_PREFIX):] # remove prefix from name
        result = metrics['values'][name]
    except KeyError:
        result = 0

    return result


def get_delta(name):
    """Return change over time for the requested metric"""

    global DELTA_METRICS

    # get current metrics
    curr_metrics = get_metrics()

    # get delta
    try:
        name = name[len(NAME_PREFIX):] # remove prefix from name
        delta = (curr_metrics['values'][name] - DELTA_METRICS[name]['value'])/(curr_metrics['time'] - DELTA_METRICS[name]['time'])
    except KeyError:
        delta = 0

    # update last metrics
    DELTA_METRICS[name] = {
        'value' : get_metrics()['values'][name],
        'time'  : get_metrics()['time']
    }

    return delta


def get_globalLock_ratio(name):
    """Return the global lock ratio"""

    try:
        result = get_delta(NAME_PREFIX + 'globalLock_lockTime') / get_delta(NAME_PREFIX + 'globalLock_totalTime') * 100
    except ZeroDivisionError:
        result = 0

    return result


def indexCounters_btree_missRatio(name):
    """Return the btree miss ratio"""

    try:
        result = get_delta(NAME_PREFIX + 'indexCounters_btree_misses') / get_delta(NAME_PREFIX + 'indexCounters_btree_accesses') * 100
    except ZeroDivisionError:
        result = 0

    return result


def metric_init(lparams):
    """Initialize metric descriptors"""

    global PARAMS

    # set parameters
    for key in lparams:
        PARAMS[key] = lparams[key]

    # define descriptors
    time_max = 60
    groups = 'mongodb'
    descriptors = [
        {
            'name': NAME_PREFIX + 'opcounters_insert',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%.0f',
            'description': 'Inserts',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'opcounters_query',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%.0f',
            'description': 'Queries',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'opcounters_update',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%.0f',
            'description': 'Updates',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'opcounters_delete',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%.0f',
            'description': 'Deletes',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'opcounters_getmore',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%.0f',
            'description': 'Get mores',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'opcounters_command',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%.0f',
            'description': 'Commands',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'backgroundFlushing_flushes',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%.0f',
            'description': 'Flushes',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'mem_mapped',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'MB',
            'slope': 'both',
            'format': '%u',
            'description': 'Memory-mapped Data',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'mem_virtual',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'MB',
            'slope': 'both',
            'format': '%u',
            'description': 'Process Virtual Size',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'mem_resident',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'MB',
            'slope': 'both',
            'format': '%u',
            'description': 'Process Resident Size',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'extra_info_page_faults',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%.0f',
            'description': 'Page Faults',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'globalLock_ratio',
            'call_back': get_globalLock_ratio,
            'time_max': time_max,
            'value_type': 'float',
            'units': '%',
            'slope': 'both',
            'format': '%.0f',
            'description': 'Global Write Lock Ratio',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'indexCounters_btree_missRatio',
            'call_back': indexCounters_btree_missRatio,
            'time_max': time_max,
            'value_type': 'float',
            'units': '%',
            'slope': 'both',
            'format': '%.0f',
            'description': 'BTree Page Miss Ratio',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'globalLock_currentQueue_total',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Ops',
            'slope': 'both',
            'format': '%u',
            'description': 'Total Operations Waiting for Lock',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'globalLock_currentQueue_readers',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Ops',
            'slope': 'both',
            'format': '%u',
            'description': 'Readers Waiting for Lock',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'globalLock_currentQueue_writers',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Ops',
            'slope': 'both',
            'format': '%u',
            'description': 'Writers Waiting for Lock',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'connections_current',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Connections',
            'slope': 'both',
            'format': '%u',
            'description': 'Open Connections',
            'groups': groups
        }
    ]

    return descriptors


def metric_cleanup():
    """Cleanup"""

    pass


# the following code is for debugging and testing
if __name__ == '__main__':
    descriptors = metric_init({'stats_command': 'ssh mongodb.example.com mongo --quiet --eval "printjson\(db.serverStatus\(\)\)"'})
    while True:
        for d in descriptors:
            print '%s = %s' % (d['name'], d['call_back'](d['name']))
        print "\n"
        time.sleep(10)
