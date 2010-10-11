#!/usr/bin/python


import os
import sys
import time


name_prefix = 'tokyo_tyrant_'
stats_command = None
descriptors = list()


# return a value for the requested metric
def metric_handler(name):

    # remove prefix from name
    name = name[len(name_prefix):]

    # read command output
    cmd = os.popen(stats_command)
    stdout = cmd.readlines()

    # return value for selected metric
    for line in stdout:
        (metric, value) = line.strip().split()
        if metric == name:
            return value


# return change over time for the requested metric
def metric_delta_handler(name):

    # get current time/value
    curr_time = time.time()
    curr_value = float(metric_handler(name))

    # read last time/value from file
    last_value_file = "/tmp/%s.last" % (name)
    try:
        last_time = os.path.getmtime(last_value_file)
        f = open(last_value_file)
        last_value = float(f.read().strip())
    except OSError:
        last_time = None
        last_value = None

    # compute delta
    if not last_time:
        delta = 0.0
    else:
        delta = (curr_value - last_value)/(curr_time - last_time)

    # write current value to file
    f = open(last_value_file, 'w')
    f.write(str(curr_value))

    return delta


# initialize metric descriptors
def metric_init(params):
    global stats_command
    global descriptors

    stats_command = params['stats_command']

    time_max = 60
    groups = 'tokyo tyrant'

    descriptors = [
        {
            'name': name_prefix + 'rnum',
            'call_back': metric_handler,
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
            'call_back': metric_handler,
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
            'call_back': metric_handler,
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
            'call_back': metric_delta_handler,
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
            'call_back': metric_delta_handler,
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
            'call_back': metric_delta_handler,
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
            'call_back': metric_delta_handler,
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
            'call_back': metric_delta_handler,
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
            'call_back': metric_delta_handler,
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
    params = {'stats_command': 'cat ./tcrmgr'}
    metric_init(params)
    for d in descriptors:
        print '%s = %s' % (d['name'], d['call_back'](d['name']))


