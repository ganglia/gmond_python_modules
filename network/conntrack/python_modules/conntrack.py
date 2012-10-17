#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Conntrack gmond module for Ganglia
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

import os
import time
import copy

NAME_PREFIX = 'conntrack_'
PARAMS = {
    'stats_command' : '/usr/sbin/conntrack -S'
}
METRICS = {
    'time' : 0,
    'data' : {}
}
LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_MAX = 5

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d


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
            try:
                metrics[values[0]] = int(values[1])
            except ValueError:
                metrics[values[0]] = 0

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


def get_delta(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    # get delta
    name = name[len(NAME_PREFIX):] # remove prefix from name
    try:
        delta = float(curr_metrics['data'][name] - last_metrics['data'][name])/(curr_metrics['time'] - last_metrics['time'])
        if delta < 0:
            print "Less than 0"
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

    global PARAMS, Desc_Skel

    # set parameters
    for key in lparams:
        PARAMS[key] = lparams[key]

    # define descriptors
    time_max = 60

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : 'XXX',
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%f',
        'units'       : 'XXX',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'conntrack',
        }

    descriptors = []
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'entries',
                "call_back"  : get_value,
                "units"      : "entries",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'searched',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'found',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'new',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'invalid',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'ignore',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'delete',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'delete_list',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'insert',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'insert_failed',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'drop',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'early_drop',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'icmp_error',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'expect_new',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'expect_create',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'expect_delete',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'search_restart',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                })) 

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
        print 'Sleeping 15 seconds'
        time.sleep(15)
