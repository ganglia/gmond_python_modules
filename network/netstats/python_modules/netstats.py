#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import traceback
import os
import threading
import time

MODULE_NAME = "netstat"
STATS_FILE = "/proc/net/netstat"
SNMP_FILE = "/proc/net/snmp"

descriptors = list()
Desc_Skel = {}
_Worker_Thread = None
_Lock = threading.Lock()  # synchronization lock
Debug = False


def dprint(f, *v):
    if Debug:
        print >>sys.stderr, MODULE_NAME + ": " + f % v


def floatable(str):
    try:
        float(str)
        return True
    except:
        return False


class UpdateMetricThread(threading.Thread):
    def __init__(self, params):
        threading.Thread.__init__(self)

        self.running = False
        self.shuttingdown = False
        self.refresh_rate = params["refresh_rate"]
        self.mp = params["metrix_prefix"]
        self.metric = {}
        self.last_metric = {}

    def shutdown(self):
        self.shuttingdown = True

        if not self.running:
            return

        self.join()

    def run(self):
        self.running = True

        while not self.shuttingdown:
            _Lock.acquire()
            updated = self.update_metric()
            _Lock.release()

            if not updated:
                time.sleep(0.2)
            else:
                if "time" in self.last_metric:
                    dprint("metric delta period %.3f" % (
                            self.metric['time'] -
                            self.last_metric['time']))

        self.running = False

    def update_metric(self):
        if "time" in self.metric:
            if (time.time() - self.metric['time']) < self.refresh_rate:
                return False

        dprint("updating metrics")

        self.last_metric = self.metric.copy()

        update_dict = {
            'time': time.time(),
        }

        try:
            for stat_type, key, value in netstats_iterator():
                update_dict['%s_%s_%s' % (self.mp, stat_type, key)] = int(value)

        except IOError as err:
            dprint("unable to open stats file. %s" % err)
            return False

        self.metric.update(update_dict)

        return True

    def metric_delta(self, name):
        val = 0

        if name in self.metric and name in self.last_metric:
            _Lock.acquire()
            if self.metric['time'] - self.last_metric['time'] != 0:
                val = (self.metric[name] - self.last_metric[name]) / (
                        self.metric['time'] - self.last_metric['time'])
            _Lock.release()

        return float(val)


def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread, Debug

    # initialize skeleton of descriptors
    Desc_Skel = {
        'name': 'XXX',
        'call_back': metric_delta,
        'time_max': 60,
        'value_type': 'float',
        'format': '%.2f',
        'units': 'XXX',
        'slope': 'XXX',  # zero|positive|negative|both
        'description': 'XXX',
        'groups': 'network'
    }
    
    params["refresh_rate"] = params.get("refresh_rate", 15)
    params["metrix_prefix"] = params.get("metrix_prefix", MODULE_NAME)
    Debug = params.get("debug", False)

    dprint("debugging has been turned on")

    _Worker_Thread = UpdateMetricThread(params)
    _Worker_Thread.start()

    mp = params["metrix_prefix"]

    try:
        for stat_type, key, value in netstats_iterator():
            descriptors.append(create_desc(Desc_Skel, {
                "name": '%s_%s_%s' % (mp, stat_type, key),
                "units": "number",
                "slope": "both",
                "description": "Netstat %s metric %s" % (stat_type, key)
            }))
    except IOError:
        return

    return descriptors


def file_iterator(file_name):
    f = open(file_name, 'r')

    line_number = -1
    labels = []
    labels_type = None

    with f:
        for line in f:
            line_number += 1

            if not re.search(':', line):
                continue

            are_labels = (line_number % 2 == 0)

            tokens = re.split('[:\s]+', line.strip())

            if are_labels:
                labels_type = tokens[0].strip(':')
                labels = tokens[1:]
                continue

            values_type = tokens[0].strip(':')

            if values_type != labels_type:
                dprint("Expected values of type `%s` but they were `%s`" % (
                        labels_type, values_type))
                continue

            for ind, value in enumerate(tokens[1:]):
                yield values_type, labels[ind], value


def netstats_iterator():
    for vt, key, val in file_iterator(STATS_FILE):
        yield vt, key, val

    for vt, key, val in file_iterator(SNMP_FILE):
        yield vt, key, val


def create_desc(skel, prop):
    d = skel.copy()
    for k, v in prop.iteritems():
        d[k] = v
    return d


def metric_delta(name):
    return _Worker_Thread.metric_delta(name)


def metric_cleanup():
    _Worker_Thread.shutdown()

if __name__ == '__main__':
    params = {
        "debug": True,
        "refresh_rate": 15
    }

    try:
        metric_init(params)

        while True:
            time.sleep(params['refresh_rate'])
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is ' + d['format']) % (d['name'],  v)
    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except:
        traceback.print_exc()
        os._exit(1)
