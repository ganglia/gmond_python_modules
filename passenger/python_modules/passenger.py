#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import traceback
import os
import threading
import time
import datetime
import signal
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

def floatable(str):
    try:
        float(str)
        return True
    except:
        return False

class UpdateMetricThread(threading.Thread):

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running      = False
        self.shuttingdown = False
        self.refresh_rate = 30
        if "refresh_rate" in params:
            self.refresh_rate = int(params["refresh_rate"])
        self.metric       = {}
        self.timeout      = 10

        self.status       = "sudo /usr/bin/passenger-status"
        self.memory_stats = "sudo /usr/bin/passenger-memory-stats"
        if "status" in params:
            self.status = params["status"]
        if "memory_stats" in params:
            self.memory_stats = params["memory_stats"]
        self.mp      = params["metrix_prefix"]
        self.status_regex   = {
          'max_pool_size':        r"^max\s+= (\d+)",
          'open_processes':       r"^count\s+= (\d+)",
          'processes_active':     r"^active\s+= (\d+)",
          'processes_inactive':   r"^inactive\s+= (\d+)",
          'global_queue_depth':   r"^Waiting on global queue: (\d+)",
          'memory_usage':         r"^### Total private dirty RSS:\s+(\d+)"
        }

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
        status_output = timeout_command(self.status, self.timeout)
        status_output += timeout_command(self.memory_stats, self.timeout)[-1:] # to get last line of memory output
        dprint("%s", status_output)
        for line in status_output:
          for (name,regex) in self.status_regex.iteritems():
            result = re.search(regex,line)
            if result:
              dprint("%s = %d", name, int(result.group(1)))
              self.metric[self.mp+'_'+name] = int(result.group(1))

    def metric_of(self, name):
        val = 0
        mp = name.split("_")[0]
        if name in self.metric:
            _Lock.acquire()
            val = self.metric[name]
            _Lock.release()
        return val

def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread, Debug

    if "metrix_prefix" not in params:
      params["metrix_prefix"] = "passenger"

    print params

    # initialize skeleton of descriptors
    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : metric_of,
        'time_max'    : 60,
        'value_type'  : 'uint',
        'format'      : '%u',
        'units'       : 'XXX',
        'slope'       : 'XXX', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'passenger',
        }

    if "refresh_rate" not in params:
        params["refresh_rate"] = 15
    if "debug" in params:
        Debug = params["debug"]
    dprint("%s", "Debug mode on")

    _Worker_Thread = UpdateMetricThread(params)
    _Worker_Thread.start()

    # IP:HOSTNAME
    if "spoof_host" in params:
        Desc_Skel["spoof_host"] = params["spoof_host"]

    mp = params["metrix_prefix"]

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_max_pool_size",
                "units"      : "processes",
                "slope"      : "both",
                "description": "Max processes in Passenger pool",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_open_processes",
                "units"      : "processes",
                "slope"      : "both",
                "description": "Number of currently open passenger processes",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_processes_active",
                "units"      : "processes",
                "slope"      : "both",
                "description": "Active processes",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_processes_inactive",
                "units"      : "processes",
                "slope"      : "both",
                "description": "Inactive processes",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_global_queue_depth",
                "units"      : "requests",
                "slope"      : "both",
                "description": "Requests waiting on a free process",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_memory_usage",
                "units"      : "MB",
                "slope"      : "both",
                "description": "Passenger Memory usage",
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

def timeout_command(command, timeout):
    """call shell-command and either return its output or kill it
    if it doesn't normally exit within timeout seconds and return None"""
    cmd = command.split(" ")
    start = datetime.datetime.now()
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while process.poll() is None:
        time.sleep(0.2)
        now = datetime.datetime.now()
        if (now - start).seconds> timeout:
            os.system("sudo kill %s" % process.pid)
            os.waitpid(-1, os.WNOHANG)
            return []
    return process.stdout.readlines()

if __name__ == '__main__':
    try:
        params = {
            "debug" : True,
            }
        metric_init(params)

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
