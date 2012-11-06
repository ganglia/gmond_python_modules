#!/usr/bin/python
# Name: multi_nginx_status.py
# Desc: Ganglia python module for getting nginx stats from multiple nginx servers.
# Author: Evan Fraser (evan.fraser@trademe.co.nz) (inherited some code from existing nginx_status module)
# Date: 05/11/2012

import pprint
import time
import socket
import urllib2
import re

descriptors = list()

NIPARAMS = {}

NIMETRICS = {
    'time' : 0,
    'data' : {}
}

LAST_NIMETRICS = {}
NIMETRICS_CACHE_MAX = 10

# status_request() makes the http request to the nginx status pages
def status_request(srvname, port):
    url = 'http://' + srvname + ':' + port + '/nginx_status'
    c = urllib2.urlopen(url)
    data = c.read()
    c.close()

    matchActive = re.search(r'Active connections:\s+(\d+)', data)
    matchHistory = re.search(r'\s*(\d+)\s+(\d+)\s+(\d+)', data)
    matchCurrent = re.search(r'Reading:\s*(\d+)\s*Writing:\s*(\d+)\s*'
            'Waiting:\s*(\d+)', data)
    if not matchActive or not matchHistory or not matchCurrent:
        raise Exception('Unable to parse {0}' . format(url))
    result = {}
    result[srvname + '_activeConn'] = float(matchActive.group(1))

    #These ones are accumulative and will need to have their delta calculated
    result[srvname + '_accepts'] = float(matchHistory.group(1))
    result[srvname + '_handled'] = float(matchHistory.group(2))
    result[srvname + '_requests'] = float(matchHistory.group(3))

    result[srvname + '_reading'] = float(matchCurrent.group(1))
    result[srvname + '_writing'] = float(matchCurrent.group(2))
    result[srvname + '_waiting'] = float(matchCurrent.group(3))

    return result

# get_metrics() is the callback metric handler, is called repeatedly by gmond
def get_metrics(name):
    global NIMETRICS,LAST_NIMETRICS
    # if interval since last check > NIMETRICS_CACHE_MAX get metrics again
    if (time.time() - NIMETRICS['time']) > NIMETRICS_CACHE_MAX:
        metrics = {}
        for para in NIPARAMS.keys():
            srvname,port = NIPARAMS[para].split(':')
            newmetrics = status_request(srvname,port)
            metrics = dict(newmetrics, **metrics)
                        
        LAST_NIMETRICS = dict(NIMETRICS)
        NIMETRICS = {
            'time': time.time(),
            'data': metrics
            }
    #For counter type metrics, return the delta instead:
    accumulative = ['_accepts', '_handled', '_requests']
    for m in accumulative:
        if m in name:
            try:
                delta = float(NIMETRICS['data'][name] - LAST_NIMETRICS['data'][name])/(NIMETRICS['time'] - LAST_NIMETRICS['time'])
                if delta < 0:
                    delta = 0
            except StandardError:
                delta = 0
            return delta

    return NIMETRICS['data'][name]
        
# create_desc() builds the descriptors from passed skeleton and additional properties
def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

# called by metric_init() to setup the metrics
def define_metrics(Desc_Skel, srvname, port):
    ip = socket.gethostbyname(srvname)
    spoof_str = ip + ':' + srvname
    print spoof_str
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : srvname + '_activeConn',
                "units"       : "connections",
                "description" : "Total number of active connections",
                "spoof_host"  : spoof_str,
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : srvname + '_accepts',
                "units"       : "connections/s",
                "description" : "Accepted connections per second",
                "spoof_host"  : spoof_str,
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : srvname + '_handled',
                "units"       : "connections/s",
                "description" : "Handled connections per second",
                "spoof_host"  : spoof_str,
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : srvname + '_requests',
                "units"       : "requests/s",
                "description" : "Requests per second",
                "spoof_host"  : spoof_str,
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : srvname + '_reading',
                "units"       : "connections",
                "description" : "Current connections in reading state",
                "spoof_host"  : spoof_str,
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : srvname + '_writing',
                "units"       : "connections",
                "description" : "Current connections in writing state",
                "spoof_host"  : spoof_str,
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : srvname + '_waiting',
                "units"       : "connections",
                "description" : "Current connections in waiting state",
                "spoof_host"  : spoof_str,
                }))

    return descriptors
# Called once by gmond to setup the metrics.
def metric_init(params):
    global descriptors, Desc_Skel
    print '[multinginx] Recieved the following parameters'
    print params

    for key in params:
        NIPARAMS[key] = params[key]

    Desc_Skel = {
        'name'        : 'XXX',
        #'call_back'   : 'XXX',
        'call_back'   : get_metrics,
        'time_max'    : 60,
        'value_type'  : 'double',
        'format'      : '%0f',
        'units'       : 'XXX',
        'slope'       : 'both',
        'description' : 'XXX',
        'groups'      : 'nginx',
        #'spoof_host'  : spoof_string
        }  

    for para in params.keys():
        if para.startswith('server_'):
            srvname,port = params[para].split(':')
            descriptors = define_metrics(Desc_Skel, srvname, port)

    return descriptors

# Below section is for debugging from the CLI.
if __name__ == '__main__':
    params = {
        #Example hostname:portnumber"
        'server_1' : 'imgsrv1:8080',
        'server_2' : 'imgsrv2:8080',
        'server_3' : 'imgsrv3:8081',
        }
    descriptors = metric_init(params)
    print len(descriptors)
    pprint.pprint(descriptors)
    while True:
         for d in descriptors:
             v = d['call_back'](d['name'])
             #print v
             print 'value for %s is %u' % (d['name'], v)
         print 'Sleeping 5 seconds'
         time.sleep(5)
