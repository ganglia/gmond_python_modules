#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# MongoDB gmond module for Ganglia
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
import socket
import string
import time
import copy

NAME_PREFIX = 'mongodb_'
PARAMS = {
    'server_status' : 'mongo --quiet --eval "printjson(db.serverStatus())"',
    'rs_status'     : 'mongo --quiet --eval "printjson(rs.status())"'
}
METRICS = {
    'time' : 0,
    'data' : {}
}
LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_TTL = 3


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

    if (time.time() - METRICS['time']) > METRICS_CACHE_TTL:

        metrics = {}
        for status_type in PARAMS.keys():

            # get raw metric data
            io = os.popen(PARAMS[status_type])

            # clean up
            metrics_str = ''.join(io.readlines()).strip() # convert to string
            metrics_str = re.sub('\w+\((.*)\)', r"\1", metrics_str) # remove functions
            metrics_str = metrics_str.replace(''', 1,''',''',''')
            
            # convert to flattened dict
            try:
                if status_type == 'server_status':
                    metrics.update(flatten(json.loads(metrics_str)))
                else:
                    metrics.update(flatten(json.loads(metrics_str), pre='%s_' % status_type))
            except ValueError,e:
                print e
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
     # get metrics
    metrics = get_metrics()[0]
    # get value
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

    # get rate
    name = name[len(NAME_PREFIX):] # remove prefix from name

    try:
        rate = (float(curr_metrics['data'][name]) - float(last_metrics['data'][name])) / \
               (float(curr_metrics['time']) - float(last_metrics['time']))
        if rate < 0:
            rate = float(0)
    except StandardError,e:
        rate = float(0)

    return rate


def get_opcounter_rate(name):
    """Return change over time for an opcounter metric"""

    master_rate = get_rate(name)
    repl_rate = get_rate(name.replace('opcounters_', 'opcountersRepl_'))

    return master_rate + repl_rate


def get_globalLock_ratio(name):
    """Return the global lock ratio"""

    try:
        result = get_rate(NAME_PREFIX + 'globalLock_lockTime') / \
                 get_rate(NAME_PREFIX + 'globalLock_totalTime') * 100
    except ZeroDivisionError:
        result = 0

    return result


def get_indexCounters_btree_miss_ratio(name):
    """Return the btree miss ratio"""

    try:
        result = get_rate(NAME_PREFIX + 'indexCounters_btree_misses') / \
                 get_rate(NAME_PREFIX + 'indexCounters_btree_accesses') * 100
    except ZeroDivisionError:
        result = 0

    return result


def get_connections_current_ratio(name):
    """Return the percentage of connections used"""

    try:
        result = float(get_value(NAME_PREFIX + 'connections_current')) / \
                 float(get_value(NAME_PREFIX + 'connections_available')) * 100
    except ZeroDivisionError:
        result = 0

    return result


def get_slave_delay(name):
    """Return the replica set slave delay"""

    # get metrics
    metrics = get_metrics()[0]

    # no point checking my optime if i'm not replicating
    if 'rs_status_myState' not in metrics['data'] or metrics['data']['rs_status_myState'] != 2:
        result = 0

    # compare my optime with the master's
    else:
        master = {}
        slave = {}
        try:
            for member in metrics['data']['rs_status_members']:
                if member['state'] == 1:
                    master = member
                if member['name'].split(':')[0] == socket.getfqdn():
                    slave = member
            result = max(0, master['optime']['t'] - slave['optime']['t']) / 1000
        except KeyError:
            result = 0

    return result


def get_asserts_total_rate(name):
    """Return the total number of asserts per second"""

    return float(reduce(lambda memo,obj: memo + get_rate('%sasserts_%s' % (NAME_PREFIX, obj)),
                       ['regular', 'warning', 'msg', 'user', 'rollovers'], 0))


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
            'call_back': get_opcounter_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Inserts/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Inserts',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'opcounters_query',
            'call_back': get_opcounter_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Queries/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Queries',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'opcounters_update',
            'call_back': get_opcounter_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Updates/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Updates',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'opcounters_delete',
            'call_back': get_opcounter_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Deletes/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Deletes',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'opcounters_getmore',
            'call_back': get_opcounter_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Getmores/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Getmores',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'opcounters_command',
            'call_back': get_opcounter_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Commands/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Commands',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'backgroundFlushing_flushes',
            'call_back': get_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Flushes/Sec',
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
            'call_back': get_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Faults/Sec',
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
            'call_back': get_indexCounters_btree_miss_ratio,
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
            'units': 'Operations',
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
            'units': 'Operations',
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
            'units': 'Operations',
            'slope': 'both',
            'format': '%u',
            'description': 'Writers Waiting for Lock',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'globalLock_activeClients_total',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Clients',
            'slope': 'both',
            'format': '%u',
            'description': 'Total Active Clients',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'globalLock_activeClients_readers',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Clients',
            'slope': 'both',
            'format': '%u',
            'description': 'Active Readers',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'globalLock_activeClients_writers',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Clients',
            'slope': 'both',
            'format': '%u',
            'description': 'Active Writers',
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
        },
        {
            'name': NAME_PREFIX + 'connections_current_ratio',
            'call_back': get_connections_current_ratio,
            'time_max': time_max,
            'value_type': 'float',
            'units': '%',
            'slope': 'both',
            'format': '%f',
            'description': 'Percentage of Connections Used',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'slave_delay',
            'call_back': get_slave_delay,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Seconds',
            'slope': 'both',
            'format': '%u',
            'description': 'Replica Set Slave Delay',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'asserts_total',
            'call_back': get_asserts_total_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Asserts/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Asserts',
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
