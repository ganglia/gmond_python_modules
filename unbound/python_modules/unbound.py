#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# unbound gmond module for Ganglia
#
# Copyright (C) 2014 by Tobias Schmidt <ts@soundcloud.com>, SoundCloud Inc.
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

NAME_PREFIX = 'unbound_'
PARAMS = {
    'stats_command': 'sudo /usr/sbin/unbound-control stats'
}
METRICS = {
    'time': 0,
    'data': {}
}
METRICS_CACHE_MAX = 5


def create_desc(skel, prop):
    d = skel.copy()
    for k, v in prop.iteritems():
        d[k] = v
    return d


def get_metrics():
    """Return all metrics"""

    global METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:
        # get raw metric data
        io = os.popen(PARAMS['stats_command'])

        # convert to dict
        metrics = {}
        for line in io.readlines():
            key, value = line.split('=')[:2]
            metrics[key] = float(value)

        # update cache
        METRICS = {
            'time': time.time(),
            'data': metrics
        }

    return METRICS


def get_value(name):
    """Return a value for the requested metric"""

    metrics = get_metrics()
    name = 'total.' + name[len(NAME_PREFIX):].replace('_', '.')

    try:
        result = metrics['data'][name]
    except StandardError:
        result = 0.0

    return result


def metric_init(lparams):
    """Initialize metric descriptors"""

    global PARAMS, Desc_Skel

    # set parameters
    for key in lparams:
        PARAMS[key] = lparams[key]

    Desc_Skel = {
        'name':        'XXX',
        'call_back':   get_value,
        'time_max':    60,
        'value_type':  'float',
        'format':      '%f',
        'units':       'XXX',
        'slope':       'both',
        'description': 'XXX',
        'groups':      'unbound',
    }

    descriptors = []

    descriptors.append(create_desc(Desc_Skel, {
        'name':        NAME_PREFIX + 'num_queries',
        'units':       'Queries',
        'description': 'Unbound queries',
    }))

    descriptors.append(create_desc(Desc_Skel, {
        'name':        NAME_PREFIX + 'num_cachehits',
        'units':       'Queries',
        'description': 'Unbound cachehits',
    }))

    descriptors.append(create_desc(Desc_Skel, {
        'name':        NAME_PREFIX + 'num_cachemiss',
        'units':       'Queries',
        'description': 'Unbound cachemiss',
    }))

    descriptors.append(create_desc(Desc_Skel, {
        'name':        NAME_PREFIX + 'num_prefetch',
        'units':       'Prefetches',
        'description': 'Unbound cache prefetches',
    }))

    descriptors.append(create_desc(Desc_Skel, {
        'name':        NAME_PREFIX + 'num_recursivereplies',
        'units':       'Replies',
        'description': 'Replies to recursive queries',
    }))

    descriptors.append(create_desc(Desc_Skel, {
        'name':        NAME_PREFIX + 'requestlist_avg',
        'units':       'Requests',
        'description': 'Number of requests (avg.)',
    }))

    descriptors.append(create_desc(Desc_Skel, {
        'name':        NAME_PREFIX + 'requestlist_max',
        'units':       'Requests',
        'description': 'Number of requests (max.)',
    }))

    descriptors.append(create_desc(Desc_Skel, {
        'name':        NAME_PREFIX + 'requestlist_overwritten',
        'units':       'Requests',
        'description': 'Overwritten number of requests',
    }))

    descriptors.append(create_desc(Desc_Skel, {
        'name':        NAME_PREFIX + 'requestlist_exceeded',
        'units':       'Requests',
        'description': 'Dropped number of requests',
    }))

    descriptors.append(create_desc(Desc_Skel, {
        'name':        NAME_PREFIX + 'requestlist_current_all',
        'units':       'Requests',
        'description': 'Unbound requestlist size (all)',
    }))

    descriptors.append(create_desc(Desc_Skel, {
        'name':        NAME_PREFIX + 'requestlist_current_user',
        'units':       'Requests',
        'description': 'Unbound requestlist size (user)',
    }))

    descriptors.append(create_desc(Desc_Skel, {
        'name':        NAME_PREFIX + 'recursion_time_avg',
        'units':       'Seconds',
        'description': 'Unbound recursion latency (avg.)',
    }))

    descriptors.append(create_desc(Desc_Skel, {
        'name':        NAME_PREFIX + 'recursion_time_median',
        'units':       'Seconds',
        'description': 'Unbound recursion latency (50th)',
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
            fmt = (('%s = %s') % (d['name'], d['format']))
            print fmt % (d['call_back'](d['name']))
        print 'Sleeping 15 seconds'
        time.sleep(15)
