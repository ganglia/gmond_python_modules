#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import threading
import time
import re

descriptors = list()
Desc_Skel   = {}
_Worker_Thread = None
_Lock = threading.Lock() # synchronization lock
Debug = False

Diskstats_Pos = {
    'ds_ios_read'  : 3,
    'ds_KB_read' : 5,
    'ds_ios_write' : 7,
    'ds_KB_write': 9,
    'ds_in_flight' :11,
    }

def dprint(f, *v):
    if Debug:
        print >>sys.stderr, "DEBUG: "+f % v

class UpdateMetricThread(threading.Thread):

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running      = False
        self.shuttingdown = False
        self.refresh_rate = 10
        if "refresh_rate" in params:
            self.refresh_rate = int(params["refresh_rate"])
        self.metric       = {}
        self.re_disk      = r"^sd[a-z]$"
        self.re_procs     = r"^procs_"

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        self.running = True

        while not self.shuttingdown:
            _Lock.acquire()
            self.update_metric()
            _Lock.release()
            time.sleep(self.refresh_rate)

        self.running = False

    def update_metric(self):
        elm = []

        f = open("/proc/diskstats", "r")
        for l in f:
            elm = l.split(None)
            if not re.search(self.re_disk, elm[2]):
                continue
            for (k,v) in Diskstats_Pos.iteritems():
                if (k == "ds_KB_read" or k == "ds_KB_write"):
                    dprint("  %s (%d)", k, int(elm[v]))
                    self.metric[k] = int(elm[v])/2 # *512/1024
                else:
                    self.metric[k] = int(elm[v])
                dprint("%s %d", k, self.metric[k])
        f.close

        f = open("/proc/stat", "r")
        for l in f:
            elm = l.split(None)
            if not re.search(self.re_procs, elm[0]):
                continue
            k = "ds_"+elm[0]
            self.metric[k] = int(elm[1])
            dprint("%s %d", k, self.metric[k])
        f.close


    def metric_of(self, name):
        val = 0
        if name in self.metric:
            _Lock.acquire()
            val = self.metric[name]
            _Lock.release()
        return val

def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread, Debug

    print '[diskstats] disk I/O stats'
    print params

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : metric_of,
        'time_max'    : 60,
        'value_type'  : 'uint',
        'format'      : '%d',
        'units'       : 'XXX',
        'slope'       : 'positive',
        'description' : 'XXX',
        'groups'      : 'disk',
        }

    if "refresh_rate" not in params:
        params["refresh_rate"] = 10
    if "debug" in params:
        Debug = params["debug"]
    dprint("%s", "Debug mode on")

    _Worker_Thread = UpdateMetricThread(params)
    _Worker_Thread.start()

    # IP:HOSTNAME
    if "spoof_host" in params:
        Desc_Skel["spoof_host"] = params["spoof_host"]

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "ds_ios_read",
                "units"      : "IO",
                "description": "number of reads completed",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "ds_ios_write",
                "units"      : "IO",
                "description": "number of writes completed",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "ds_KB_read",
                "units"      : "KiB",
                "description": "KiB of read",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "ds_KB_write",
                "units"      : "KiB",
                "description": "KiB of write",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "ds_in_flight",
                "units"      : "req",
                "description": "number of I/Os currently in progress",
                "slope"      : "both",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "ds_procs_running",
                "units"      : "procs",
                "description": "number of processes running",
                "slope"      : "both",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "ds_procs_blocked",
                "units"      : "procs",
                "description": "number of processes I/O blocked",
                "slope"      : "both",
                }))

    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_of(name):
    return _Worker_Thread.metric_of(name)

def metric_cleanup():
    _Worker_Thread.shutdown()

if __name__ == '__main__':
    try:
        params = {
            "debug" : True,
            }
        metric_init(params)
        time.sleep(0.3)
        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is '+d['format']) % (d['name'],  v)
            #time.sleep(5)
            os._exit(1)
    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except StandardError:
        os._exit(1)
