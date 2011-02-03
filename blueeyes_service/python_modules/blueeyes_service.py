#!/usr/bin/env python
################################################################################
# BlueEyes gmond module for Ganglia
# Copyright (c) 2011 Michael T. Conigliaro <mike [at] conigliaro [dot] org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
################################################################################

import json
import os
import re
import time


PARAMS = {
    'service_name'    : 'example',
    'service_version' : 'v1',
    'stats_command'   : 'curl --silent http://appserver01.example.com:30060/blueeyes/services/example/v1/health'
}
NAME_PREFIX = 'blueeyes_service_%s_%s_' % (PARAMS['service_name'], PARAMS['service_version'])
METRICS = {
    'time' : 0,
    'data' : {}
}
LAST_METRICS = dict(METRICS)
METRICS_CACHE_MAX = 1


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

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

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
        LAST_METRICS = dict(METRICS)
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


def get_time_value(name):
    """BlueEyes returns time values in ns, so convert to seconds"""

    return get_value(name)/1000000


def get_delta(name):
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
    descriptors = []
    for request in ['DELETE', 'GET', 'POST', 'PUT']:
        descriptors.extend([{
            'name': NAME_PREFIX + 'requests_' + request + '_count',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%f',
            'description': '%s Requests' % request,
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'requests_' + request + '_errors_errorCount',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'int',
            'units': 'Errors',
            'slope': 'both',
            'format': '%d',
            'description': '%s Errors' % request,
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'requests_' + request + '_timing_minimumTime',
            'call_back': get_time_value,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Seconds',
            'slope': 'both',
            'format': '%f',
            'description': '%s Request Minimum Time' % request,
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'requests_' + request + '_timing_maximumTime',
            'call_back': get_time_value,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Seconds',
            'slope': 'both',
            'format': '%f',
            'description': '%s Request Maximum Time' % request,
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'requests_' + request + '_timing_averageTime',
            'call_back': get_time_value,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Seconds',
            'slope': 'both',
            'format': '%f',
            'description': '%s Request Average Time' % request,
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'requests_' + request + '_timing_standardDeviation',
            'call_back': get_time_value,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Seconds',
            'slope': 'both',
            'format': '%f',
            'description': '%s Request Standard Deviation' % request,
            'groups': groups
        }])

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
        time.sleep(1)
