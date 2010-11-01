#!/usr/bin/python


import json
import os
import re
import sys
import time


name_prefix = 'mongodb_'
params = {
    'stats_command' : 'mongo --quiet --eval "printjson(db.serverStatus())"'
}
metrics = {
    'time'   : 0,
    'values' : {}
}
delta_metrics = {}
metrics_cache_max = 1


# flatten a dict (i.e. dict['a']['b']['c'] => dict['a_b_c'])
def flatten(d, pre = '', sep = '_'):
    new_d = {}
    for k,v in d.items():
        if type(v) == dict:
            new_d.update(flatten(d[k], '%s%s%s' % (pre, k, sep)))
        else:
            new_d['%s%s' % (pre, k)] = v
    return new_d


# return all metrics
def get_metrics():

    global metrics

    if (time.time() - metrics['time']) > metrics_cache_max:

        # get raw metric data
        io = os.popen(params['stats_command'])

        # clean up
        metrics_str = ''.join(io.readlines()).strip() # convert to string
        metrics_str = re.sub('\w+\((.*)\)', r"\1", metrics_str) # remove functions

        # convert to flattened dict
        fresh_metrics = flatten(json.loads(metrics_str))

        # update cache
        metrics['time'] = time.time()
        for name,value in fresh_metrics.items():
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
        delta = (curr_metrics['values'][name] - delta_metrics[name]['value'])/(curr_metrics['time'] - delta_metrics[name]['time'])
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
    groups = 'mongodb'
    descriptors = [
        {
            'name': name_prefix + 'opcounters_insert',
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
            'name': name_prefix + 'opcounters_query',
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
            'name': name_prefix + 'opcounters_update',
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
            'name': name_prefix + 'opcounters_delete',
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
            'name': name_prefix + 'opcounters_getmore',
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
            'name': name_prefix + 'opcounters_command',
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
            'name': name_prefix + 'backgroundFlushing_flushes',
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
            'name': name_prefix + 'mem_mapped',
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
            'name': name_prefix + 'mem_virtual',
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
            'name': name_prefix + 'mem_resident',
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
            'name': name_prefix + 'extra_info_page_faults',
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
            'name': name_prefix + 'globalLock_ratio',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'float',
            'units': '%',
            'slope': 'both',
            'format': '%.0f',
            'description': 'Global Write Lock Ratio',
            'groups': groups
        },
        {
            'name': name_prefix + 'indexCounters_btree_missRatio',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'float',
            'units': '%',
            'slope': 'both',
            'format': '%.0f',
            'description': 'BTree Page Miss Ratio',
            'groups': groups
        },
        {
            'name': name_prefix + 'globalLock_currentQueue_total',
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
            'name': name_prefix + 'globalLock_currentQueue_readers',
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
            'name': name_prefix + 'globalLock_currentQueue_writers',
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
            'name': name_prefix + 'connections_current',
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


# cleanup
def metric_cleanup():
    pass


# the following code is for debugging and testing
if __name__ == '__main__':
    descriptors = metric_init({'stats_command': 'ssh mongodb.example.com mongo --quiet --eval "printjson\(db.serverStatus\(\)\)"'})
    while True:
        for d in descriptors:
            print '%s = %s' % (d['name'], d['call_back'](d['name']))
        print "\n"
        time.sleep(10)
