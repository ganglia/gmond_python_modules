#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import sys
import time


NAME_PREFIX = 'tokyo_tyrant_'
PARAMS = {
    'stats_command' : 'tcrmgr inform -st localhost'
}
METRICS = {
    'time'   : 0,
    'values' : {}
}
DELTA_METRICS = {}
METRICS_CACHE_MAX = 1


def get_metrics():
    """Return all metrics"""

    global METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

        # get raw metric data
        io = os.popen(PARAMS['stats_command'])

        # convert to list
        metrics_list = io.readlines()

        METRICS['time'] = time.time()
        for line in metrics_list:
            (name, value) = line.strip().split()
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
        delta = (float(curr_metrics['values'][name]) - float(DELTA_METRICS[name]['value']))/(curr_metrics['time'] - DELTA_METRICS[name]['time'])
    except KeyError:
        delta = 0

    # update last metrics
    DELTA_METRICS[name] = {
        'value' : get_metrics()['values'][name],
        'time'  : get_metrics()['time']
    }

    return delta


def metric_init(lparams):
    """Initialize metric descriptors"""

    global PARAMS

    # set parameters
    for key in lparams:
        PARAMS[key] = lparams[key]

    # define descriptors
    time_max = 60
    groups = 'tokyo tyrant'
    descriptors = [
        {
            'name': NAME_PREFIX + 'rnum',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': '',
            'slope': 'both',
            'format': '%u',
            'description': 'Record Number',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'size',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'double',
            'units': 'Bytes',
            'slope': 'both',
            'format': '%f',
            'description': 'File Size',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'delay',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Secs',
            'slope': 'both',
            'format': '%f',
            'description': 'Replication Delay',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'cnt_put',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Put Operations',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'cnt_out',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Out Operations',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'cnt_get',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Get Operations',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'cnt_put_miss',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Put Operations Missed',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'cnt_out_miss',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Out Operations Missed',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'cnt_get_miss',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Get Operations Missed',
            'groups': groups
        }
    ]

    return descriptors


def metric_cleanup():
    """Cleanup"""

    pass


# the following code is for debugging and testing
if __name__ == '__main__':
    descriptors = metric_init({'stats_command': 'ssh tokyotyrant.example.com tcrmgr inform -st localhost'})
    while True:
        for d in descriptors:
            print '%s = %s' % (d['name'], d['call_back'](d['name']))
        print "\n"
        time.sleep(10)
