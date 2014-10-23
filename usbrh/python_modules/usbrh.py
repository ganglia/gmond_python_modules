#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

descriptors = list()
Desc_Skel   = {}
Debug = False

def dprint(f, *v):
    if Debug:
        print >>sys.stderr, "DEBUG: "+f % v

def metric_of(name):
    dprint("%s", name)
    try:
        type, device_num = name.split("usbrh_")[1].split("_")
        f = open("/proc/usbrh/%(device_num)s/%(type)s" % locals(), 'r')

    except IOError:
        return 0

    for l in f:
        line = l.rstrip()
        if type == "temperature":
            line = float(line)

    return line

def metric_init(params):
    global descriptors, Desc_Skel, Debug

    print '[usbrh] initialize'
    print params

    # initialize skeleton of descriptors
    Desc_Skel = {
        'name'        : 'usbrh',
        'call_back'   : metric_of,
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%f',
        'units'       : 'Celsius',
        'slope'       : 'both',
        'description' : 'usbrh temperature',
        'groups'      : 'usbrh',
        }

    if "debug" in params:
        Debug = params["debug"]
    dprint("%s", "Debug mode on")

    # IP:HOSTNAME
    if "spoof_host" in params:
        Desc_Skel["spoof_host"] = params["spoof_host"]

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "usbrh_temperature_0",
                "value_type" : "float",
                "format"     : "%f",
                "units"      : "Celsius",
                "description": "usbrh temperature 0",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "usbrh_temperature_1",
                "value_type" : "float",
                "format"     : "%f",
                "units"      : "Celsius",
                "description": "usbrh temperature 1",
                }))

    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_cleanup():
    pass

if __name__ == '__main__':
    params = {
        "debug" : True,
        }
    metric_init(params)

  #       for d in descriptors:
  #           print '''  metric {
  #   name  = "%s"
  #   title = "%s"
  #   value_threshold = 0
  # }''' % (d["name"], d["description"])

    for d in descriptors:
        v = d['call_back'](d['name'])
        print ('value for %s is '+d['format']) % (d['name'],  v)
