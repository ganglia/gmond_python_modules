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
NIMETRICS_CACHE_MAX = 10

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
                #define the Appliance/[SAN|WAN] metrics
                for net in statsDict['RPA statistics'][rpa]['Traffic']['Application'].keys():
                    #print net
                    descriptors.append(create_desc(Desc_Skel, {
                                "name"        : (rpa.lower()).replace(' ','_') + '_' + net.lower(),
                                "units"       : "bits/sec",
                                "description" : net + ' traffic',
                                "groups"      : net + " Traffic",
                                }))

    #Define Consistency Group metrics this is paintfully nested in the dict.
    for group in statsDict['Group']:
        #CG SAN and Journal lag are under the policies
        for policyname in statsDict['Group'][group]['Copy stats']:
            if 'SAN traffic' in statsDict['Group'][group]['Copy stats'][policyname]:
                descriptors.append(create_desc(Desc_Skel, {
                            "name"        : group + '_SAN_Traffic',
                            "units"       : 'Bits/s',
                            "description" : group + ' SAN Traffic',
                            "groups"      : 'SAN Traffic',
                            }))
            elif 'Journal' in statsDict['Group'][group]['Copy stats'][policyname]:
                descriptors.append(create_desc(Desc_Skel, {
                            "name"        : group + '_Journal_Lag',
                            "units"       : 'Bytes',
                            "description" : group + ' Journal Lag',
                            "groups"      : 'Lag',
                            }))
                #Protection window
                descriptors.append(create_desc(Desc_Skel, {
                            "name"        : group + '_Protection_Window',
                            "units"       : 'mins',
                            "description" : group + ' Protection Window',
                            "groups"      : 'Protection',
                            }))

        #CG Lag and WAN stats are in the Link stats section
        for repname in statsDict['Group'][group]['Link stats']:
            #Define CG WAN traffic metrics
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : group + '_WAN_Traffic',
                        "units"       : 'Bits/s',
                        "description" : group + ' WAN Traffic',
                        "groups"      : 'WAN Traffic',
                        }))
            
            #Define CG Lag metrics
            for lagfields in statsDict['Group'][group]['Link stats'][repname]['Replication']['Lag']:
                lagunit = ''
                if 'Writes' in lagfields:
                    lagunit = 'Writes'
                elif 'Data' in lagfields:
                    lagunit = 'Bytes'
                elif 'Time' in lagfields:
                    lagunit = 'Seconds'
                descriptors.append(create_desc(Desc_Skel, {
                            "name"        : group + '_Lag_' + lagfields,
                            "units"       : lagunit,
                            "description" : group + ' Lag ' + lagunit,
                            "groups"      : 'Lag',
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
        stdin, stdout, sterr = sshcon.exec_command("get_system_statistics;get_group_statistics")
        rawdata = stdout.read()
        #Group stats don't leave a space after the colon in some places
        rawmetrics = yaml.safe_load(rawdata.replace(':N',': N'))
        #Get RPA metrics
        for rpa in rawmetrics['RPA statistics']:
            for metric in rawmetrics['RPA statistics'][rpa]:
                if "Latency (ms)" in metric:
                    metrics[(rpa.lower()).replace(' ','_') + '_latency'] = rawmetrics['RPA statistics'][rpa]['Latency (ms)']
                if "Traffic" in metric:
                    #store the Application/[SAN|WAN] metrics
                    for net in rawmetrics['RPA statistics'][rpa]['Traffic']['Application'].keys():
                        traffic,junk = rawmetrics['RPA statistics'][rpa]['Traffic']['Application'][net].split()
                        metrics[(rpa.lower()).replace(' ','_') + '_' + net.lower()] = float(traffic)

        for group in rawmetrics['Group']:
            #CG SAN and Journal lag are under the policies
            for policyname in rawmetrics['Group'][group]['Copy stats']:
                #Get CG SAN metrics (remove 'Mbps' from end + convert to float and then bits)
                if 'SAN traffic' in rawmetrics['Group'][group]['Copy stats'][policyname]:
                    metrics[group + '_SAN_Traffic'] = float(rawmetrics['Group'][group]['Copy stats'][policyname]['SAN traffic']['Current throughput'][:-4]) * 1024 * 1024
                elif 'Journal' in rawmetrics['Group'][group]['Copy stats'][policyname]:
                    datastr = rawmetrics['Group'][group]['Copy stats'][policyname]['Journal']['Journal lag']
                    amount = float(datastr[:-2])
                    unitstr = datastr[-2:]
                    if 'MB' in unitstr:
                        amount = amount * 1024 * 1024
                    elif 'KB' in unitstr:
                        amount = amount * 1024
                    elif 'GB' in unitstr:
                        amount = amount * 1024 * 1024 * 1024
                    metrics[group + '_Journal_Lag'] = amount
                    #Protection Window is in Journal section
                    prowindowstr = rawmetrics['Group'][group]['Copy stats'][policyname]['Journal']['Protection window']['Current']['Value']
                    protectmins = 0
                    protimelist = prowindowstr.split(' ')
                    if 'hr' in protimelist:
                        hrindex = protimelist.index('hr')
                        protectmins = protectmins + (int(protimelist[int(hrindex) - 1]) * 60)
                    if 'min' in protimelist:
                        minindex = protimelist.index('min')
                        protectmins = protectmins + int(protimelist[int(minindex) -1])
                    metrics[group + '_Protection_Window'] = float(protectmins)
                                                     
            #CG Lag and WAN stats are in the Link stats section
            for repname in rawmetrics['Group'][group]['Link stats']:
                #Get CG WAN metrics (remove 'Mbps' from end + convert to float and then bits)
                metrics[group + '_WAN_Traffic'] = float(rawmetrics['Group'][group]['Link stats'][repname]['Replication']['WAN traffic'][:-4]) * 1024 * 1024
                
                #Get CG Lag metrics
                for lagfields in rawmetrics['Group'][group]['Link stats'][repname]['Replication']['Lag']:
                    if 'Data' in lagfields:
                        #Convert 12.34(GB|MB|KB) to bytes
                        datastr = rawmetrics['Group'][group]['Link stats'][repname]['Replication']['Lag'][lagfields]
                        #print datastr
                        amount = float(datastr[:-2])
                        unitstr = datastr[-2:]
                        if 'MB' in unitstr:
                            amount = amount * 1024 * 1024
                        elif 'KB' in unitstr:
                            amount = amount * 1024
                        elif 'GB' in unitstr:
                            amount = amount * 1024 * 1024 * 1024
                        metrics[group + '_Lag_' + lagfields] = amount
                        
                    elif 'Time' in lagfields:
                        #Strip 'sec' from value, convert to float.
                        lagtime = float(rawmetrics['Group'][group]['Link stats'][repname]['Replication']['Lag'][lagfields][:-3])
                        metrics[group + '_Lag_' + lagfields] = lagtime
                    else:
                        #Writes Lag
                        metrics[group + '_Lag_' + lagfields] = float(rawmetrics['Group'][group]['Link stats'][repname]['Replication']['Lag'][lagfields])
                        
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
    stdin, stdout, sterr = sshcon.exec_command("get_system_statistics;get_group_statistics")
    rawdata = stdout.read()
    #Group stats don't leave a space after the colon in some places
    statsDict = yaml.safe_load(rawdata.replace(':N',': N'))
    sshcon.close()
    descriptors = define_metrics(Desc_Skel, statsDict)

    return descriptors

# For CLI Debuging:
if __name__ == '__main__':
    params = {
        'mgmtip' : '192.168.1.100',
        
              }
    descriptors = metric_init(params)
    pprint.pprint(descriptors)
    print len(descriptors)
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print 'value for %s is %u' % (d['name'],  v)        
        print 'Sleeping 5 seconds'
        time.sleep(5)
#exit(0)
