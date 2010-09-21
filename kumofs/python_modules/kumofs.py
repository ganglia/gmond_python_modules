#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import traceback
import os
import threading
import time
import subprocess
import re

descriptors = list()
Desc_Skel   = {}
_Worker_Thread = None
_Lock = threading.Lock() # synchronization lock
Debug = False

def dprint(f, *v):
    if Debug:
        print >>sys.stderr, "DEBUG: "+f % v

class UpdateMetricThread(threading.Thread):

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running      = False
        self.shuttingdown = False
        self.refresh_rate = 20
        if "refresh_rate" in params:
            self.refresh_rate = int(params["refresh_rate"])
        self.metric       = {}
        self.timeout      = 2

        self.host         = "localhost"
        self.port         = 19800
        if "host" in params:
            self.host = params["host"]
        if "port" in params:
            self.port = params["port"]

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
        cmd = ["kumostat", "%s:%s" % (self.host, self.port), "stats"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pout, perr = proc.communicate()

        for m in re.split('(?:\r\n|\n)',pout):
            dprint("%s",m)
            d = m.split(" ")
            if len(d) == 3 and d[0] == "STAT":
                self.metric["kumofs_"+d[1]] = int(d[2]) if d[2].isdigit() else d[2]

    def metric_of(self, name):
        val = 0
        if name in self.metric:
            _Lock.acquire()
            val = self.metric[name]
            _Lock.release()
        return val

def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread, Debug

    print '[kumofs] kumofs protocol "stats"'
    print params

    # initialize skeleton of descriptors
    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : metric_of,
        'time_max'    : 60,
        'value_type'  : 'uint',
        'format'      : '%d',
        'units'       : 'XXX',
        'slope'       : 'XXX', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'kumofs',
        }

    if "refresh_rate" not in params:
        params["refresh_rate"] = 20
    if "debug" in params:
        Debug = params["debug"]
    dprint("%s", "Debug mode on")

    _Worker_Thread = UpdateMetricThread(params)
    _Worker_Thread.start()

    # IP:HOSTNAME
    if "spoof_host" in params:
        Desc_Skel["spoof_host"] = params["spoof_host"]

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "kumofs_curr_items",
                "units"      : "items",
                "slope"      : "both",
                "description": "Current number of items stored",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "kumofs_cmd_get",
                "units"      : "commands",
                "slope"      : "positive",
                "description": "Cumulative number of retrieval reqs",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "kumofs_cmd_set",
                "units"      : "commands",
                "slope"      : "positive",
                "description": "Cumulative number of storage reqs",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "kumofs_cmd_delete",
                "units"      : "commands",
                "slope"      : "positive",
                "description": "Cumulative number of storage reqs",
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
            "host"  : "s101",
            "port"  : 19800,
            "debug" : True,
            }
        metric_init(params)

  #       for d in descriptors:
  #           print '''  metric {
  #   name  = "%s"
  #   title = "%s"
  #   value_threshold = 0
  # }''' % (d["name"], d["description"])

        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is '+d['format']) % (d['name'],  v)
            time.sleep(5)
    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except:
        traceback.print_exc()
        os._exit(1)
