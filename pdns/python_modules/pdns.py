#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
import copy
import socket

descriptors = list()
Desc_Skel   = {}
Debug = False

METRICS = {
    'time' : 0,
    'data' : {}
}

LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_MAX = 5

def dprint(f, *v):
    if Debug:
        print >>sys.stderr, "DEBUG: "+f % v

def get_metrics():
    '''Return all metrics'''

    global METRICS, LAST_METRICS, params

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

        new_metrics = {}

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(params['pdns_socket'])
        s.send('SHOW *\n')
        output = s.recv(1024)

        for i in (filter(None, output.split(','))):
            pair = i.split('=')
            new_metrics[pair[0]] = pair[1]

        LAST_METRICS = copy.deepcopy(METRICS)
        METRICS = {
            'time': time.time(),
            'data': new_metrics
        }

    return [METRICS, LAST_METRICS]

def get_delta(name):
    '''Return change over time for the requested metric'''

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()
    name = name.replace('pdns_', '')

    try:
        delta = ((int(curr_metrics['data'][name]) - int(last_metrics['data'][name]))/(curr_metrics['time'] - last_metrics['time']))
        if delta < 0:
            print name + " is less 0"
            delta = 0
    except KeyError:
        delta = 0.0

    return delta


def metric_init(param):
    global descriptors, Desc_Skel, Debug, params
    params = copy.deepcopy(param)

    descriptors = []

    print '[pdns] pdns'
    print params

    # gmond/modules/python/mod_python.c
    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_delta,
        'time_max'    : 60,
        'value_type'  : 'float', # string | uint | float | double
        'format'      : '%.3f',   # %s     | %d   | %f    | %f
        'units'       : 'q/s',
        'slope'       : 'both', # zero|positive|negative|both',
        'description' : 'XXX',
        'groups'      : 'XXX',
        }

    if "refresh_rate" not in params:
        params["refresh_rate"] = 10
    if "debug" in params:
        Debug = params["debug"]
    dprint("%s", "Debug mode on")

    metrics = get_metrics()[0]

    for item in metrics['data']:
        descriptors.append(create_desc(Desc_Skel, {
            'name'      : params['metric_prefix'] + "_" + item,
            'groups'    : params['metric_prefix']
            }))

    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

if __name__ == '__main__':
    params = {
        "pdns_socket": "/var/run/pdns.controlsocket",
        "metric_prefix" : "pdns",
        "debug" : True,
        }
    metric_init(params)

    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print ('value for %s is '+d['format']) % (d['name'],  v)
        print 'Sleeping 5 seconds'
        time.sleep(5)

