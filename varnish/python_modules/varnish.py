#!/usr/bin/env python
################################################################################
# Varnish gmond module for Ganglia
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

import os
import time


NAME_PREFIX = 'varnish_'
PARAMS = {
    'stats_command' : 'ssh varnish01.example.com varnishstat -1'
}
METRICS = {
    'time' : 0,
    'data' : {}
}
LAST_METRICS = dict(METRICS)
METRICS_CACHE_MAX = 1


def get_metrics():
    """Return all metrics"""

    global METRICS, LAST_METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

        # get raw metric data
        io = os.popen(PARAMS['stats_command'])

        # convert to dict
        metrics = {}
        for line in io.readlines():
            values = line.split()[:2]
            metrics[values[0]] = int(values[1])

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


def get_cache_hit_ratio(name):
    """Return cache hit ratio"""

    try:
        result = get_delta(NAME_PREFIX + 'cache_hit') / get_delta(NAME_PREFIX + 'client_req') * 100
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
    groups = 'varnish'
    descriptors = [
        {
            'name': NAME_PREFIX + 'client_req',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Client Requests',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'backend_req',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Backend Requests',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'cache_hit_ratio',
            'call_back': get_cache_hit_ratio,
            'time_max': time_max,
            'value_type': 'float',
            'units': '%',
            'slope': 'both',
            'format': '%f',
            'description': 'Cache Hit Ratio',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'n_object',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Objects',
            'slope': 'both',
            'format': '%u',
            'description': 'Objects in Cache',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'sm_balloc',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Bytes',
            'slope': 'both',
            'format': '%u',
            'description': 'Allocated Storage',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'n_wrk',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Threads',
            'slope': 'both',
            'format': '%u',
            'description': 'Worker Threads',
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
        time.sleep(1)
