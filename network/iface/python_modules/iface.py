#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import traceback
import os
import threading
import time
import socket
import select

descriptors     = list()
Desc_Skel       = {}
_Worker_Thread  = None
_Lock           = threading.Lock() # synchronization lock
Debug           = False

def dprint(f, *v):
    if Debug:
        print >>sys.stderr, "iface: " + f % v

def floatable(str):
    try:
        float(str)
        return True
    except:
        return False

class UpdateMetricThread(threading.Thread):
    def __init__(self, params):
        threading.Thread.__init__(self)

        self.running        = False
        self.shuttingdown   = False
        self.refresh_rate   = params["refresh_rate"]
        self.mp             = params["metrix_prefix"]
        self.metric         = {}
        self.last_metric    = {}

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
                    dprint("metric delta period %.3f" % (self.metric['time'] - self.last_metric['time']))


        self.running = False

    def update_metric(self):
        if "time" in self.metric:
            if (time.time() - self.metric['time']) < self.refresh_rate:
                return False

        dprint("updating metrics")

        self.last_metric = self.metric.copy()

        try:
            f = open('/proc/net/dev', 'r')
        except IOError:
            dprint("unable to open /proc/net/dev")
            return False

        for line in f:
            if re.search(':', line):
                tokens  = re.split('[:\s]+', line.strip())
                iface   = tokens[0].strip(':')

                self.metric.update({
                    'time'                                          : time.time(),
                    '%s_%s_%s' % (self.mp, iface, 'rx_bytes')       : int(tokens[1]),
                    '%s_%s_%s' % (self.mp, iface, 'rx_packets')     : int(tokens[2]),
                    '%s_%s_%s' % (self.mp, iface, 'rx_errs')        : int(tokens[3]),
                    '%s_%s_%s' % (self.mp, iface, 'rx_drop')        : int(tokens[4]),
                    '%s_%s_%s' % (self.mp, iface, 'rx_fifo')        : int(tokens[5]),
                    '%s_%s_%s' % (self.mp, iface, 'rx_frame')       : int(tokens[6]),
                    '%s_%s_%s' % (self.mp, iface, 'rx_compressed')  : int(tokens[7]),
                    '%s_%s_%s' % (self.mp, iface, 'rx_multicast')   : int(tokens[8]),
                    '%s_%s_%s' % (self.mp, iface, 'tx_bytes')       : int(tokens[9]),
                    '%s_%s_%s' % (self.mp, iface, 'tx_packets')     : int(tokens[10]),
                    '%s_%s_%s' % (self.mp, iface, 'tx_errs')        : int(tokens[11]),
                    '%s_%s_%s' % (self.mp, iface, 'tx_drop')        : int(tokens[12]),
                    '%s_%s_%s' % (self.mp, iface, 'tx_fifo')        : int(tokens[13]),
                    '%s_%s_%s' % (self.mp, iface, 'tx_frame')       : int(tokens[14]),
                    '%s_%s_%s' % (self.mp, iface, 'tx_compressed')  : int(tokens[15]),
                    '%s_%s_%s' % (self.mp, iface, 'tx_multicast')   : int(tokens[16]),
                })

        return True

    def metric_delta(self, name):
        val = 0

        if name in self.metric and name in self.last_metric:
            _Lock.acquire()
            if self.metric['time'] - self.last_metric['time'] != 0:
                val = (self.metric[name] - self.last_metric[name]) / (self.metric['time'] - self.last_metric['time'])
            _Lock.release()

        return float(val)

def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread, Debug

    # initialize skeleton of descriptors
    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : metric_delta,
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%.0f',
        'units'       : 'XXX',
        'slope'       : 'XXX', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'network'
    }

    
    params["refresh_rate"]  = params["refresh_rate"] if "refresh_rate" in params else 15
    params["metrix_prefix"] = params["metrix_prefix"] if "metrix_prefix" in params else "iface"
    Debug                   = params["debug"] if "debug" in params else False

    dprint("debugging has been turned on")

    _Worker_Thread = UpdateMetricThread(params)
    _Worker_Thread.start()

    mp = params["metrix_prefix"]

    try:
        f = open("/proc/net/dev", 'r')
    except IOError:
        return

    for line in f:
        if re.search(':', line):
            tokens  = re.split('[:\s]+', line.strip())
            iface   = tokens[0].strip(':')

            for way in ('tx', 'rx'):
                descriptors.append(create_desc(Desc_Skel, {
                    "name"       : '%s_%s_%s_%s' % (mp, iface, way, 'bytes'),
                    "units"      : "bytes/s",
                    "slope"      : "both",
                    "description": 'Interface %s %s bytes per seconds' % (iface, way.upper())
                }))

                descriptors.append(create_desc(Desc_Skel, {
                    "name"       : '%s_%s_%s_%s' % (mp, iface, way, 'packets'),
                    "units"      : "packets/s",
                    "slope"      : "both",
                    "description": 'Interface %s %s packets per seconds' % (iface, way.upper())
                }))

                descriptors.append(create_desc(Desc_Skel, {
                    "name"       : '%s_%s_%s_%s' % (mp, iface, way, 'errs'),
                    "units"      : "errs/s",
                    "slope"      : "both",
                    "description": 'Interface %s %s errors per seconds' % (iface, way.upper())
                }))

                descriptors.append(create_desc(Desc_Skel, {
                    "name"       : '%s_%s_%s_%s' % (mp, iface, way, 'drop'),
                    "units"      : "drop/s",
                    "slope"      : "both",
                    "description": 'Interface %s %s drop per seconds' % (iface, way.upper())
                }))

                descriptors.append(create_desc(Desc_Skel, {
                    "name"       : '%s_%s_%s_%s' % (mp, iface, way, 'fifo'),
                    "units"      : "fifo/s",
                    "slope"      : "both",
                    "description": 'Interface %s %s fifo per seconds' % (iface, way.upper())
                }))

                descriptors.append(create_desc(Desc_Skel, {
                    "name"       : '%s_%s_%s_%s' % (mp, iface, way, 'frame'),
                    "units"      : "frame/s",
                    "slope"      : "both",
                    "description": 'Interface %s %s frame per seconds' % (iface, way.upper())
                }))

                descriptors.append(create_desc(Desc_Skel, {
                    "name"       : '%s_%s_%s_%s' % (mp, iface, way, 'compressed'),
                    "units"      : "compressed/s",
                    "slope"      : "both",
                    "description": 'Interface %s %s compressed per seconds' % (iface, way.upper())
                }))

                descriptors.append(create_desc(Desc_Skel, {
                    "name"       : '%s_%s_%s_%s' % (mp, iface, way, 'multicast'),
                    "units"      : "multicast/s",
                    "slope"      : "both",
                    "description": 'Interface %s %s multicast per seconds' % (iface, way.upper())
                }))

    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_delta(name):
    return _Worker_Thread.metric_delta(name)

def metric_cleanup():
    _Worker_Thread.shutdown()

if __name__ == '__main__':
    params = {
        "debug"         : True,
        "refresh_rate"  : 15
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
