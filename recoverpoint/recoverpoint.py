#!/usr/bin/python
# Name: recoverpoint.py
# Desc: Ganglia Python module for gathering EMC recoverpoint statistics via SSH
# Author: Evan Fraser (evan.fraser@trademe.co.nz)
# Date: 01/08/2012


import yaml
import warnings
import pprint
import time
import re

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import paramiko

descriptors = list()
NIMETRICS = {
    'time' : 0,
    'data' : {}
}
#This is the minimum interval between querying the RPA for metrics.
#Each ssh query takes 1.6s so we limit the interval between getting metrics to this interval.
NIMETRICS_CACHE_MAX = 5

ipaddr = ''

#Example of data structure:
#{'RPA statistics': {'Site 1 RPA 1': {'Compression CPU usage': '0.00%',
#                                       'Latency (ms)': 12,
#                                       'Packet loss': '0.00%',
#                                       'Traffic': {'Application': {'SAN': '0 bps',
#                                                                   'WAN': '432 bps'},
#                                                   'Application (writes)': 0,
#                                                   'Compression': 0}},

def define_metrics(Desc_Skel, statsDict):
    for rpa in statsDict['RPA statistics']:
        #pprint.pprint(statsDict['RPA statistics'][rpa])
        for metric in statsDict['RPA statistics'][rpa].keys():
            if "Latency (ms)" in metric:
                descriptors.append(create_desc(Desc_Skel, {
                            "name"        : (rpa.lower()).replace(' ','_') + '_latency',
                            "units"       : "ms",
                            "description" : "latency in ms",
                            "groups"      : "Latency"
                            }))
            if "Traffic" in metric:
                #define the Application/[SAN|WAN] metrics
                for net in statsDict['RPA statistics'][rpa]['Traffic']['Application'].keys():
                    #print net
                    descriptors.append(create_desc(Desc_Skel, {
                                "name"        : (rpa.lower()).replace(' ','_') + '_' + net.lower(),
                                "units"       : "bits/sec",
                                "description" : net + ' traffic',
                                "groups"      : net + " Traffic",
                                }))
                    
    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d
    
def get_metrics(name):
    global NIMETRICS,ipaddr
    # if interval since last check > NIMETRICS_CACHE_MAX get metrics again
    metrics = {}
    if (time.time() - NIMETRICS['time']) > NIMETRICS_CACHE_MAX:

        sshcon = paramiko.SSHClient()
        sshcon.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        sshcon.connect(ipaddr, username='monitor',password='monitor',look_for_keys='False')
        stdin, stdout, sterr = sshcon.exec_command("get_system_statistics")
        rawmetrics = yaml.load(stdout)
        for rpa in rawmetrics['RPA statistics']:
            for metric in rawmetrics['RPA statistics'][rpa]:
                if "Latency (ms)" in metric:
                    metrics[(rpa.lower()).replace(' ','_') + '_latency'] = rawmetrics['RPA statistics'][rpa]['Latency (ms)']
                if "Traffic" in metric:
                    #store the Application/[SAN|WAN] metrics
                    for net in rawmetrics['RPA statistics'][rpa]['Traffic']['Application'].keys():
                        traffic,junk = rawmetrics['RPA statistics'][rpa]['Traffic']['Application'][net].split()
                        metrics[(rpa.lower()).replace(' ','_') + '_' + net.lower()] = int(traffic)

                        
        NIMETRICS = {
            'time': time.time(),
            'data': metrics
            }
    else:
        metrics = NIMETRICS['data']
    return metrics[name]
    
    

def metric_init(params):
    global descriptors, Desc_Skel, ipaddr
    print '[recoverpoint] Recieved the following parameters'
    print params
    ipaddr = params['mgmtip']
    print ipaddr
    spoof_string = ipaddr + ':recoverpoint'
    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_metrics,
        'time_max'    : 60,
        'value_type'  : 'double',
        'format'      : '%0f',
        'units'       : 'XXX',
        'slope'       : 'both',
        'description' : 'XXX',
        'groups'      : 'netiron',
        'spoof_host'  : spoof_string
        }  

    sshcon = paramiko.SSHClient()
    sshcon.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    sshcon.connect(ipaddr, username='monitor',password='monitor',look_for_keys='False')
    stdin, stdout, sterr = sshcon.exec_command("get_system_statistics")
    statsDict = yaml.load(stdout)
    sshcon.close()
    descriptors = define_metrics(Desc_Skel, statsDict)

    return descriptors

# For CLI Debuging:
if __name__ == '__main__':
    params = {
        'mgmtip' : '192.168.1.100',
              }
    descriptors = metric_init(params)
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print 'value for %s is %u' % (d['name'],  v)        
        print 'Sleeping 5 seconds'
        time.sleep(5)
#exit(0)
