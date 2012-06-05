#!/usr/bin/python
# Name: netiron.py
# Desc: Ganglia module for polling netirons via snmnp (probably work with any snmp capable device)
# Author: Evan Fraser evan.fraser@trademe.co.nz
# Date: April 2012
# Copyright: GPL

import sys
import os
import re
import time
from pysnmp.entity.rfc3413.oneliner import cmdgen
NIPARAMS = {}

NIMETRICS = {
    'time' : 0,
    'data' : {}
}
LAST_NIMETRICS = dict(NIMETRICS)
NIMETRICS_CACHE_MAX = 5

descriptors = list()

oidDict = {
    'ifIndex'       : (1,3,6,1,2,1,2,2,1,1),
    'ifName'        : (1,3,6,1,2,1,31,1,1,1,1),
    'ifAlias'       : (1,3,6,1,2,1,31,1,1,1,18),
    'ifHCInOctets'  : (1,3,6,1,2,1,31,1,1,1,6),
    'ifHCOutOctets' : (1,3,6,1,2,1,31,1,1,1,10),
    'ifInUcastPkts' : (1,3,6,1,2,1,2,2,1,11),
    'ifOutUcastPkts' : (1,3,6,1,2,1,2,2,1,17),
    }

def get_metrics():
    """Return all metrics"""

    global NIMETRICS, LAST_NIMETRICS

    # if interval since last check > NIMETRICS_CACHE_MAX get metrics again
    if (time.time() - NIMETRICS['time']) > NIMETRICS_CACHE_MAX:
        metrics = {}
        for para in NIPARAMS.keys():
            if para.startswith('netiron_'):
                ipaddr,name = NIPARAMS[para].split(':')
                snmpTable = runSnmp(oidDict,ipaddr)
                newmetrics = buildDict(oidDict,snmpTable,name)
                metrics = dict(newmetrics, **metrics)

        # update cache
        LAST_NIMETRICS = dict(NIMETRICS)
        NIMETRICS = {
            'time': time.time(),
            'data': metrics
        }

    return [NIMETRICS, LAST_NIMETRICS]

def get_delta(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()
    try:
        delta = float(curr_metrics['data'][name] - last_metrics['data'][name])/(curr_metrics['time'] - last_metrics['time'])
        #print delta
        if delta < 0:
            print "Less than 0"
            delta = 0
    except StandardError:
        delta = 0

    return delta

# Separate routine to perform SNMP queries and returns table (dict)
def runSnmp(oidDict,ip):
    
    # cmdgen only takes tuples, oid strings don't work
#    ifIndex       = (1,3,6,1,2,1,2,2,1,1)
#    ifName        = (1,3,6,1,2,1,31,1,1,1,1)
#    ifAlias       = (1,3,6,1,2,1,31,1,1,1,18)
#    ifHCInOctets  = (1,3,6,1,2,1,31,1,1,1,6)
#    ifHCOutOctets = (1,3,6,1,2,1,31,1,1,1,10)

    #Runs the SNMP query, The order that oid's are passed determines the order in the results
    errorIndication, errorStatus, errorIndex, varBindTable = cmdgen.CommandGenerator().nextCmd(
        # SNMP v2
        cmdgen.CommunityData('test-agent', 'public'),
        cmdgen.UdpTransportTarget((ip, 161)),
        oidDict['ifAlias'],
        oidDict['ifIndex'],
        oidDict['ifName'],
        oidDict['ifHCInOctets'],
        oidDict['ifHCOutOctets'],
        oidDict['ifInUcastPkts'],
        oidDict['ifOutUcastPkts'],
        )
    # Check for SNMP errors
    if errorIndication:
        print errorIndication
    else:
        if errorStatus:
            print '%s at %s\n' % (
                errorStatus.prettyPrint(), errorIndex and varBindTable[-1][int(errorIndex)-1] or '?'
                )
        else:
            return(varBindTable)

def buildDict(oidDict,t,netiron): # passed a list of tuples, build's a dict based on the alias name
    builtdict = {}
    
    for line in t:
        #        if t[t.index(line)][2][1] != '':
        string = str(t[t.index(line)][2][1])
        match = re.search(r'ethernet', string)
        if match and t[t.index(line)][0][1] != '':
            alias = str(t[t.index(line)][0][1])
            index = str(t[t.index(line)][1][1])
            name = str(t[t.index(line)][2][1])
            hcinoct = str(t[t.index(line)][3][1])
            builtdict[netiron+'_'+alias+'_bitsin'] = int(hcinoct) * 8
            hcoutoct = str(t[t.index(line)][4][1])
            builtdict[netiron+'_'+alias+'_bitsout'] = int(hcoutoct) * 8
            hcinpkt = str(t[t.index(line)][5][1])
            builtdict[netiron+'_'+alias+'_pktsin'] = int(hcinpkt)
            hcoutpkt = str(t[t.index(line)][6][1])
            builtdict[netiron+'_'+alias+'_pktsout'] = int(hcoutpkt)
            
    return builtdict

# define_metrics will run an snmp query on an ipaddr, find interfaces, build descriptors and set spoof_host
# define_metrics is called from metric_init
def define_metrics(Desc_Skel, ipaddr, netiron):
    snmpTable = runSnmp(oidDict,ipaddr)
    aliasdict = buildDict(oidDict,snmpTable,netiron)
    spoof_string = ipaddr + ':' + netiron
    #print newdict

    for key in aliasdict.keys():
        if "bitsin" in key:
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : key,
                        "units"       : "bits/sec",
                        "description" : "received bits per sec",
                        "groups"      : "Throughput",
                        "spoof_host"  : spoof_string,
                        }))
        elif "bitsout" in key:
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : key,
                        "units"       : "bits/sec",
                        "description" : "transmitted bits per sec",
                        "groups"      : "Throughput",
                        "spoof_host"  : spoof_string,
                        }))
        elif "pktsin" in key:
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : key,
                        "units"       : "pkts/sec",
                        "description" : "received packets per sec",
                        "groups"      : "Packets",
                        "spoof_host"  : spoof_string,
                        }))
        elif "pktsout" in key:
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : key,
                        "units"       : "pkts/sec",
                        "description" : "transmitted packets per sec",
                        "groups"      : "Packets",
                        "spoof_host"  : spoof_string,
                        }))


    return descriptors

def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread, Debug, newdict

    print '[netiron] Received the following parameters'
    print params

    #Import the params into the global NIPARAMS
    for key in params:
        NIPARAMS[key] = params[key]

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_delta,
        'time_max'    : 60,
        'value_type'  : 'double',
        'format'      : '%0f',
        'units'       : 'XXX',
        'slope'       : 'both',
        'description' : 'XXX',
        'groups'      : 'netiron',
        }  

    # Find all the netiron's passed in params    
    for para in params.keys():
         if para.startswith('netiron_'):
             #Get ipaddr + name of netirons from params
             ipaddr,name = params[para].split(':')
             # pass skel, ip and name to define_metrics to create descriptors
             descriptors = define_metrics(Desc_Skel, ipaddr, name)
    #Return the descriptors back to gmond
    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d


def metric_cleanup():
    '''Clean up the metric module.'''
    pass

# For CLI Debuging:
if __name__ == '__main__':
    params = {
        'netiron_1' : '192.168.1.1:switch1',
        'netiron_2' : '192.168.1.2:switch2',
              }
    descriptors = metric_init(params)
    print len(descriptors)
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print 'value for %s is %u' % (d['name'],  v)        
        print 'Sleeping 5 seconds'
        time.sleep(5)
#exit(0)
