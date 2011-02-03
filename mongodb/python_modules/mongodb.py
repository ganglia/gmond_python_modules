#!/usr/bin/env python
################################################################################
# MongoDB gmond module for Ganglia
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


NAME_PREFIX = 'mongodb_'
PARAMS = {
    'stats_command' : 'ssh mongodb04.example.com mongo --quiet --eval "printjson\(db.serverStatus\(\)\)"'
}
METRICS = {
    'time' : 0,
    'data' : {}
}
LAST_METRICS = dict(METRICS)
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


def get_globalLock_ratio(name):
    """Return the global lock ratio"""

    try:
        result = get_delta(NAME_PREFIX + 'globalLock_lockTime') / get_delta(NAME_PREFIX + 'globalLock_totalTime') * 100
    except ZeroDivisionError:
        result = 0

    return result


def indexCounters_btree_miss_ratio(name):
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
            'format': '%f',
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
            'format': '%f',
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
            'format': '%f',
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
            'format': '%f',
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
            'format': '%f',
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
            'format': '%f',
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
            'format': '%f',
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
            'format': '%f',
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
            'format': '%f',
            'description': 'Global Write Lock Ratio',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'indexCounters_btree_miss_ratio',
            'call_back': indexCounters_btree_miss_ratio,
            'time_max': time_max,
            'value_type': 'float',
            'units': '%',
            'slope': 'both',
            'format': '%f',
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
    descriptors = metric_init(PARAMS)
    while True:
        for d in descriptors:
            print (('%s = %s') % (d['name'], d['format'])) % (d['call_back'](d['name']))
        print ''
        time.sleep(1)
