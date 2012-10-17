#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# BlueEyes gmond module for Ganglia
#
# Copyright (C) 2011 by Michael T. Conigliaro <mike [at] conigliaro [dot] org>.
# All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#


import json
import os
import re
import time
import copy


PARAMS = {
    'service_name'    : 'stats',
    'service_version' : 'v1'
}
PARAMS['stats_command'] = 'curl --silent http://appserver11.example.com:30040/blueeyes/services/%s/%s/health' % \
                          (PARAMS['service_name'], PARAMS['service_version'])
NAME_PREFIX = 'blueeyes_service_%s_%s_' % (PARAMS['service_name'], PARAMS['service_version'])
METRICS = {
    'time' : 0,
    'data' : {}
}
LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_TTL = 1


def flatten(obj, pre = '', sep = '_'):
    """Flatten a dict (i.e. dict['a']['b']['c'] => dict['a_b_c'])"""

    if type(obj) == dict:
        result = {}
        for k,v in obj.items():
            if type(v) == dict:
                result.update(flatten(obj[k], '%s%s%s' % (pre, k, sep)))
            else:
                result['%s%s' % (pre, k)] = v
    else:
        result = obj

    return result


def get_metrics():
    """Return all metrics"""

    global METRICS, LAST_METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_TTL:

        # get raw metric data
        io = os.popen(PARAMS['stats_command'])

        # clean up
        metrics_str = ''.join(io.readlines()).strip() # convert to string
        metrics_str = re.sub('\w+\((.*)\)', r"\1", metrics_str) # remove functions

        # convert to flattened dict
        try:
            metrics = flatten(json.loads(metrics_str))
        except ValueError:
            metrics = {}

        # update cache
        LAST_METRICS = copy.deepcopy(METRICS)
        METRICS = {
            'time': time.time(),
            'data': metrics
        }

    return [METRICS, LAST_METRICS]


def get_value(name):
    """Return a value for the requested metric"""

    metrics = get_metrics()[0]

    name = name[len(NAME_PREFIX):] # remove prefix from name
    try:
        result = metrics['data'][name]
    except StandardError:
        result = 0

    return result


def get_rate(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    # get delta
    name = name[len(NAME_PREFIX):] # remove prefix from name
    try:
        delta = (curr_metrics['data'][name] - last_metrics['data'][name])/(curr_metrics['time'] - last_metrics['time'])
        if delta < 0:
            delta = 0
    except StandardError:
        delta = 0

    return delta


def get_requests(name):
    """Return requests per second"""

    return reduce(lambda memo,obj: memo + get_rate('%srequests_%s_count' % (NAME_PREFIX, obj)),
                 ['DELETE', 'GET', 'POST', 'PUT'], 0)


def get_errors(name):
    """Return errors per second"""

    return reduce(lambda memo,obj: memo + get_rate('%srequests_%s_errors_errorCount' % (NAME_PREFIX, obj)),
                 ['DELETE', 'GET', 'POST', 'PUT'], 0)


def metric_init(lparams):
    """Initialize metric descriptors"""

    global NAME_PREFIX, PARAMS

    # set parameters
    for key in lparams:
        PARAMS[key] = lparams[key]
    NAME_PREFIX = 'blueeyes_service_%s_%s_' % (PARAMS['service_name'], PARAMS['service_version'])

    # define descriptors
    time_max = 60
    groups = 'blueeyes service %s %s' % (PARAMS['service_name'], PARAMS['service_version'])
    descriptors = [
        {
            'name': NAME_PREFIX + 'requests',
            'call_back': get_requests,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Requests/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Requests',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'errors',
            'call_back': get_errors,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Errors/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Errors',
            'groups': groups
        }
    ]

    return descriptors


def metric_cleanup():
    """Cleanup"""

    pass


# the following code is for debugging and testing
if __name__ == '__main__':
    descriptors = metric_init(PARAMS)
    while True:
        for d in descriptors:
            print (('%s = %s') % (d['name'], d['format'])) % (d['call_back'](d['name']))
        print ''
        time.sleep(METRICS_CACHE_TTL)
