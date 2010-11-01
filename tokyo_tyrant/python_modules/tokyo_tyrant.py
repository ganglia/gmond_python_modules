#!/usr/bin/python


import os
import sys
import time


name_prefix = 'tokyo_tyrant_'
params = {
    'stats_command' : 'tcrmgr inform -st localhost'
}
metrics = {
    'time'   : 0,
    'values' : {}
}
delta_metrics = {}
metrics_cache_max = 1


# return all metrics
def get_metrics():

    global metrics

    if (time.time() - metrics['time']) > metrics_cache_max:

        # get raw metric data
        io = os.popen(params['stats_command'])

        # convert to list
        metrics_list = io.readlines()

        metrics['time'] = time.time()
        for line in metrics_list:
            (name, value) = line.strip().split()
            metrics['values'][name] = value

    return metrics


# return a value for the requested metric
def get_value(name):

    metrics = get_metrics()

    try:
        name = name[len(name_prefix):] # remove prefix from name
        result = metrics['values'][name]
    except KeyError:
        result = 0

    return result


# return change over time for the requested metric
def get_delta(name):

    global delta_metrics

    # get current metrics
    curr_metrics = get_metrics()

    # get delta
    try:
        name = name[len(name_prefix):] # remove prefix from name
        delta = (float(curr_metrics['values'][name]) - float(delta_metrics[name]['value']))/(curr_metrics['time'] - delta_metrics[name]['time'])
    except KeyError:
        delta = 0

    # update last metrics
    delta_metrics[name] = {
        'value' : get_metrics()['values'][name],
        'time'  : get_metrics()['time']
    }

    return delta


# initialize metric descriptors
def metric_init(lparams):

    global params

    # set parameters
    for key in lparams:
        params[key] = lparams[key]

    # define descriptors
    time_max = 60
    groups = 'tokyo tyrant'
    descriptors = [
        {
            'name': name_prefix + 'rnum',
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
            'name': name_prefix + 'size',
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
            'name': name_prefix + 'delay',
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
            'name': name_prefix + 'cnt_put',
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
            'name': name_prefix + 'cnt_out',
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
            'name': name_prefix + 'cnt_get',
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
            'name': name_prefix + 'cnt_put_miss',
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
            'name': name_prefix + 'cnt_out_miss',
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
            'name': name_prefix + 'cnt_get_miss',
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


# cleanup
def metric_cleanup():
    pass


# the following code is for debugging and testing
if __name__ == '__main__':
    descriptors = metric_init({'stats_command': 'ssh tokyotyrant.example.com tcrmgr inform -st localhost'})
    while True:
        for d in descriptors:
            print '%s = %s' % (d['name'], d['call_back'](d['name']))
        print "\n"
        time.sleep(10)
