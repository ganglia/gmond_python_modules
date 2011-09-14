#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import subprocess
import re
import time

from subprocess import Popen, PIPE, STDOUT

descriptors = list()
Debug = False

last_mps_timestamp = float(0)
last_mps_value = 0

def dprint(f, *v):
    if Debug:
        print >>sys.stderr, "DEBUG: "+f % v

def GetOverallMessagesPerSecond(name):
    dprint("%s", name)

    global last_mps_timestamp, last_mps_value

    # get the current value
    rc, output = run_cmd(["/usr/sbin/scribe_ctrl", "counters"])

    # return 0 if command fails
    if rc:
        return float(0)

    match = re.compile(r"^scribe_overall:received good: (\d+)$", re.MULTILINE).search(output)
    value = int(match.group(1))

    # save current value
    value_diff = value - last_mps_value
    last_mps_value = value

    # calculate seconds that have passed since last call
    current_time = time.time()
    elapsed = current_time - last_mps_timestamp

    # save current timestamp
    first_run = last_mps_timestamp is 0
    last_mps_timestamp = current_time

    if first_run:
        return float(0)

    return float(value_diff / elapsed)

def run_cmd(arglist):
    '''Run a command and capture output.'''

    try:
        p = Popen(arglist, stdout=PIPE, stderr=PIPE)
        output, errors = p.communicate()
    except OSError, e:
        return (1, '')

    return (p.returncode, output)

def metric_init(params):
    '''Create the metric definition dictionary object for each metric.'''

    global descriptors
    
    d1 = {
        'name': 'scribe_overall_messages_per_second',
        'call_back': GetOverallMessagesPerSecond,
        'time_max': 90,
        'value_type': 'float',
        'units': 'msg/sec',
        'slope': 'both',
        'format': '%f',
        'description': 'Average number of messages sent per second',
        'groups': 'scribe'
        }

    descriptors = [d1]
    return descriptors    

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

if __name__ == '__main__':
    metric_init({})
    
    # setup last timestamp as 10 seconds ago
    last_mps_timestamp = time.time() - 10
    
    for d in descriptors:
        v = d['call_back'](d['name'])
        print '%s: %s' % (d['name'],  v)
