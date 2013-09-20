#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import socket
import traceback
import json
import copy
import urllib2

descriptors = list()
Desc_Skel   = {}
Debug = False

METRICS = {
    'time' : 0,
    'data' : {}
}

LAST_METRICS = copy.deepcopy(METRICS)

METRICS_CACHE_MAX = 5

SERVER_STATUS_URL = ""

def get_metrics():
    """Return all metrics"""

    global METRICS, LAST_METRICS, SERVER_STATUS_URL

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

	try:
	    # Initialize service dictionary
	    req = urllib2.Request(SERVER_STATUS_URL)
	    res = urllib2.urlopen(req, None, 1)
	    stats = res.read()
	    metrics2 = json.loads(stats)
            metrics = metrics2[0]
            metrics['status'] = "up"

        except StandardError, e:
            print e
            metrics = dict()
            metrics['status'] = "down"

	# update last metrics
        LAST_METRICS = copy.deepcopy(METRICS)

        # update cache
        METRICS = {
            'time': time.time(),
            'data': metrics
        }

    return [METRICS, LAST_METRICS]


def get_delta(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    metric_name_list = name.split("_")[1:]
    metric_name = "_".join(metric_name_list)

    try:
      delta = (float(curr_metrics['data'][metric_name]) - float(last_metrics['data'][metric_name])) /(curr_metrics['time'] - last_metrics['time'])
      # If rate is 0 counter has started from beginning
      if delta < 0:
          if Debug:
              print name + " is less 0. Setting value to 0."
          delta = 0
    except KeyError:
          if Debug:
              print "Key " + name + " can't be found."
          delta = 0.0      

    return delta

def get_value(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    metric_name_list = name.split("_")[1:]
    metric_name = "_".join(metric_name_list)
    
    try:
      value = float(curr_metrics['data'][metric_name])
    except KeyError:
      if Debug:
         print "Key " + name + " can't be found."
      value = 0.0      

    return value

def get_string(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    metric_name_list = name.split("_")[1:]
    metric_name = "_".join(metric_name_list)
    
    try:
      value = curr_metrics['data'][metric_name]
    except KeyError:
      if Debug:
         print "Key " + name + " can't be found."
      value = "down"      

    return value



def metric_init(params):
    global descriptors, Desc_Skel, URL, Debug, SERVER_STATUS_URL

    if "metrics_prefix" not in params:
      params["metrics_prefix"] = "celery"

    # initialize skeleton of descriptors
    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_delta,
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%f',
        'units'       : 'XXX',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : 'No descr',
        'groups'      : 'celery',
        }

    # IP:HOSTNAME
    if "spoof_host" in params:
        Desc_Skel["spoof_host"] = params["spoof_host"]
        
    if "url" not in params:
        params["url"] = "http://localhost:8989/api/worker/"

    SERVER_STATUS_URL = params["url"]
       
    descriptors.append(create_desc(Desc_Skel, {
	"name"       : params["metrics_prefix"] + "_active",
	"units"      : "jobs",
	"description": "Number of active jobs",
	"call_back"  : get_value
    }))
    
    descriptors.append(create_desc(Desc_Skel, {
	"name"       : params["metrics_prefix"] + "_processed",
	"units"      : "jobs/s",
	"description": "Number of processed jobs",
	"call_back"  : get_delta
    }))

    descriptors.append(create_desc(Desc_Skel, {
	"name"       : params["metrics_prefix"] + "_status",
	"units"      : "",
	'value_type' : 'string',
	'format'     : '%s',
	'slope'      : 'zero',
	"description": "Celery Service up/down",
	"call_back"  : get_string
    }))

	
    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

if __name__ == '__main__':
    try:
        params = {
            "url" : "http://localhost:8989/api/worker/",
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
