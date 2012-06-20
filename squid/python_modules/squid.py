"""
Copyright (c)2012 Daniel Rich <drich@employees.org>

This module will query an squid server via SNMP for metrics
"""

import sys
import os
import re

import time
#import logging
#logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/gmond.log', filemode='w')
#logging.debug('starting up')

last_update = 0
# We get counter values back, so we have to calculate deltas for some stats
squid_stats = {}
squid_stats_last = {}

MIN_UPDATE_INTERVAL = 30          # Minimum update interval in seconds

def collect_stats():
    #logging.debug('collect_stats()')
    global last_update
    global squid_stats, squid_stats_last

    now = time.time()

    if now - last_update < MIN_UPDATE_INTERVAL:
        #logging.debug(' wait ' + str(int(MIN_UPDATE_INTERVAL - (now - last_update))) + ' seconds')
        return True
    else:
        elapsed_time = now - last_update
        last_update = now

    squid_stats = {}

    # Run squidclient mgr:info to get stats
    try:
        stats = {}
        squidclient = os.popen("squidclient mgr:info")
    except IOError,e:
        #logging.error('error running squidclient')
        return False

    # Parse output, splitting everything into key/value pairs
    rawstats = {}
    for stat in squidclient.readlines():
        stat = stat.strip()
        if stat.find(':') >= 0:
            [key,value] = stat.split(':',1)
            if value:     # Toss things with no value
                value = value.lstrip()
                rawstats[key] = value
        else:
            match = re.search("(\d+)\s+(.*)$",stat) # reversed "value key" line
            if match:
                rawstats[match.group(2)] = match.group(1)

    # Use stats_descriptions to convert raw stats to real metrics
    for metric in stats_descriptions:
        if stats_descriptions[metric].has_key('key'):
            if rawstats.has_key(stats_descriptions[metric]['key']):
                rawstat = rawstats[stats_descriptions[metric]['key']]
                if stats_descriptions[metric].has_key('match'):
                    match = re.match(stats_descriptions[metric]['match'],rawstat)
                    if match:
                        rawstat = match.group(1)
                        squid_stats[metric] = rawstat
                else:
                    squid_stats[metric] = rawstat
        if squid_stats.has_key(metric): # Strip trailing non-num text
            if metric != 'cacheVersionId': # version is special case
                match = re.match('([0-9.]+)',squid_stats[metric]);
                squid_stats[metric] = float(match.group(1))
                if stats_descriptions[metric]['type'] == 'integer':
                    squid_stats[metric] = int(squid_stats[metric])

        # Calculate delta for counter stats
        if metric in squid_stats_last:
            if stats_descriptions[metric]['type'] == 'counter32':
                current = squid_stats[metric]
                squid_stats[metric] = (squid_stats[metric] - squid_stats_last[metric]) / float(elapsed_time)
                squid_stats_last[metric] = current
            else:
                squid_stats_last[metric] = squid_stats[metric]
        else:
            if metric in squid_stats:
                squid_stats_last[metric] = squid_stats[metric]

    #logging.debug('collect_stats done')
    #logging.debug('squid_stats: ' + str(squid_stats))

def get_stat(name):
    #logging.info("get_stat(%s)" % name)
    global squid_stats

    ret = collect_stats()

    if ret:
        if name.startswith('squid_'):
            label = name[6:]
        else:
            lable = name
            
            #logging.debug("fetching %s" % label)
        try:
            #logging.info("got %4.2f" % squid_stats[label])
            return squid_stats[label]
        except:
            #logging.error("failed to fetch %s" % name)
            return 0

    else:
        return 0


def metric_init(params):
    global descriptors
    global squid_stats
    global stats_descriptions   # needed for stats extraction in collect_stat()

    #logging.debug("init: " + str(params))

    stats_descriptions = dict(
        cacheVersionId = {
            'description': 'Cache Software Version',
            'units': 'N/A',
            'type': 'string',
            'key': 'Squid Object Cache',
            },
        cacheSysVMsize = {
            'description': 'Storage Mem size in KB',
            'units': 'KB',
            'type': 'integer',
            'key': 'Storage Mem size',
            },
        cacheMemUsage = {
            'description': 'Total memory accounted for KB',
            'units': 'KB',
            'type': 'integer',
            'key': 'Total accounted',
            },
        cacheSysPageFaults = {
            'description': 'Page faults with physical i/o',
            'units': 'faults/s',
            'type': 'counter32',
            'key': 'Page faults with physical i/o',
            },
        cacheCpuTime = {
            'description': 'Amount of cpu seconds consumed',
            'units': 'seconds',
            'type': 'integer',
            'key': 'CPU Time',
            },
        cacheCpuUsage = {
            'description': 'The percentage use of the CPU',
            'units': 'percent',
            'type': 'float',
            'key': 'CPU Usage',
            },
        cacheCpuUsage_5 = {
            'description': 'The percentage use of the CPU - 5 min',
            'units': 'percent',
            'type': 'float',
            'key': 'CPU Usage, 5 minute avg',
            },
        cacheCpuUsage_60 = {
            'description': 'The percentage use of the CPU - 60 min',
            'units': 'percent',
            'type': 'float',
            'key': 'CPU Usage, 60 minute avg',
            },
        cacheMaxResSize = {
            'description': 'Maximum Resident Size in KB',
            'units': 'KB',
            'type': 'integer',
            'key': 'Maximum Resident Size',
            },
        cacheNumObjCount = {
            'description': 'Number of objects stored by the cache',
            'units': 'objects',
            'type': 'integer',
            'key': 'StoreEntries',
            },
        cacheNumObjCountMemObj = {
            'description': 'Number of memobjects stored by the cache',
            'units': 'objects',
            'type': 'integer',
            'key': 'StoreEntries with MemObjects',
            },
        cacheNumObjCountHot = {
            'description': 'Number of hot objects stored by the cache',
            'units': 'objects',
            'type': 'integer',
            'key': 'Hot Object Cache Items',
            },
        cacheNumObjCountOnDisk = {
            'description': 'Number of objects stored by the cache on-disk',
            'units': 'objects',
            'type': 'integer',
            'key': 'on-disk objects',
            },
        cacheCurrentUnusedFDescrCnt = {
            'description': 'Available number of file descriptors',
            'units': 'file descriptors',
            'type': 'gauge32',
            'key': 'Maximum number of file descriptors',
            },
        cacheCurrentResFileDescrCnt = {
            'description': 'Reserved number of file descriptors',
            'units': 'file descriptors',
            'type': 'gauge32',
            'key': 'Reserved number of file descriptors',
            },
        cacheCurrentFileDescrCnt = {
            'description': 'Number of file descriptors in use',
            'units': 'file descriptors',
            'type': 'gauge32',
            'key': 'Number of file desc currently in use',
            },
        cacheCurrentFileDescrMax = {
            'description': 'Highest file descriptors in use',
            'units': 'file descriptors',
            'type': 'gauge32',
            'key': 'Largest file desc currently in use',
            },
        cacheProtoClientHttpRequests = {
            'description': 'Number of HTTP requests received',
            'units': 'requests/s',
            'type': 'counter32',
            'key': 'Number of HTTP requests received'
            },
        cacheIcpPktsSent = {
            'description': 'Number of ICP messages sent',
            'units': 'messages/s',
            'type': 'counter32',
            'key': 'Number of ICP messages sent',
            },
        cacheIcpPktsRecv = {
            'description': 'Number of ICP messages received',
            'units': 'messages/s',
            'type': 'counter32',
            'key': 'Number of ICP messages received',
            },
        cacheCurrentSwapSize = {
            'description': 'Storage Swap size',
            'units': 'KB',
            'type': 'gauge32',
            'key': 'Storage Swap size',
            },
        cacheClients = {
            'description': 'Number of clients accessing cache',
            'units': 'clients',
            'type': 'gauge32',
            'key': 'Number of clients accessing cache',
            },
        cacheHttpAllSvcTime_5 = {
            'description': 'HTTP all service time - 5 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'HTTP Requests (All)',
            'match': '([0-9.]+)',
            },
        cacheHttpAllSvcTime_60 = {
            'description': 'HTTP all service time - 60 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'HTTP Requests (All)',
            'match': '[0-9.]+\s+([0-9.]+)',
            },
        cacheHttpMissSvcTime_5 = {
            'description': 'HTTP miss service time - 5 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'Cache Misses',
            'match': '([0-9.]+)',
            },
        cacheHttpMissSvcTime_60 = {
            'description': 'HTTP miss service time - 60 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'Cache Misses',
            'match': '[0-9.]+\s+([0-9.]+)',
            },
        cacheHttpNmSvcTime_5 = {
            'description': 'HTTP hit not-modified service time - 5 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'Not-Modified Replies',
            'match': '([0-9.]+)',
            },
        cacheHttpNmSvcTime_60 = {
            'description': 'HTTP hit not-modified service time - 60 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'Not-Modified Replies',
            'match': '[0-9.]+\s+([0-9.]+)',
            },
        cacheHttpHitSvcTime_5 = {
            'description': 'HTTP hit service time - 5 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'Cache Hits',
            'match': '([0-9.]+)',
            },
        cacheHttpHitSvcTime_60 = {
            'description': 'HTTP hit service time - 60 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'Cache Hits',
            'match': '[0-9.]+\s+([0-9.]+)',
            },
        cacheIcpQuerySvcTime_5 = {
            'description': 'ICP query service time - 5 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'ICP Queries',
            'match': '([0-9.]+)',
            },
        cacheIcpQuerySvcTime_60 = {
            'description': 'ICP query service time - 60 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'ICP Queries',
            'match': '[0-9.]+\s+([0-9.]+)',
            },
        cacheDnsSvcTime_5 = {
            'description': 'DNS service time - 5 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'DNS Lookups',
            'match': '([0-9.]+)',
            },
        cacheDnsSvcTime_60 = {
            'description': 'DNS service time - 60 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'DNS Lookups',
            'match': '[0-9.]+\s+([0-9.]+)',
            },
        cacheRequestHitRatio_5 = {
            'description': 'Request Hit Ratios - 5 min',
            'units': 'percent',
            'type': 'float',
            'key': 'Request Hit Ratios',
            'match': '5min: ([0-9.]+)%',
            },
        cacheRequestHitRatio_60 = {
            'description': 'Request Hit Ratios - 60 min',
            'units': 'percent',
            'type': 'float',
            'key': 'Request Hit Ratios',
            'match': '5min: [0-9.]+%,\s+60min: ([0-9.]+)%',
            },
        cacheRequestByteRatio_5 = {
            'description': 'Byte Hit Ratios - 5 min',
            'units': 'percent',
            'type': 'float',
            'key': 'Byte Hit Ratios',
            'match': '5min: ([0-9.]+)%',
            },
        cacheRequestByteRatio_60 = {
            'description': 'Byte Hit Ratios - 60 min',
            'units': 'percent',
            'type': 'float',
            'key': 'Byte Hit Ratios',
            'match': '5min: [0-9.]+%,\s+60min: ([0-9.]+)%',
            },
        cacheRequestMemRatio_5 = {
            'description': 'Memory Hit Ratios - 5 min',
            'units': 'percent',
            'type': 'float',
            'key': 'Request Memory Hit Ratios',
            'match': '5min: ([0-9.]+)%',
            },
        cacheRequestMemRatio_60 = {
            'description': 'Memory Hit Ratios - 60 min',
            'units': 'percent',
            'type': 'float',
            'key': 'Request Memory Hit Ratios',
            'match': '5min: [0-9.]+%,\s+60min: ([0-9.]+)%',
            },
        cacheRequestDiskRatio_5 = {
            'description': 'Disk Hit Ratios - 5 min',
            'units': 'percent',
            'type': 'float',
            'key': 'Request Disk Hit Ratios',
            'match': '5min: ([0-9.]+)%',
            },
        cacheRequestDiskRatio_60 = {
            'description': 'Disk Hit Ratios - 60 min',
            'units': 'percent',
            'type': 'float',
            'key': 'Request Disk Hit Ratios',
            'match': '5min: [0-9.]+%,\s+60min: ([0-9.]+)%',
            },
        cacheHttpNhSvcTime_5 = {
            'description': 'HTTP refresh hit service time - 5 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'Near Hits',
            'match': '([0-9.]+)',
            },
        cacheHttpNhSvcTime_60 = {
            'description': 'HTTP refresh hit service time - 60 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'Near Hits',
            'match': '[0-9.]+\s+([0-9.]+)',
            },
    )

    descriptors = []
    collect_stats()

    time.sleep(MIN_UPDATE_INTERVAL)
    collect_stats()

    for label in stats_descriptions:
        if squid_stats.has_key(label):
            if stats_descriptions[label]['type'] == 'string':
                d= {
                    'name': 'squid_' + label,
                    'call_back': get_stat,
                    'time_max': 60,
                    'value_type': "string",
                    'units': '',
                    'slope': "none",
                    'format': '%s',
                    'description': label,
                    'groups': 'squid',
                }
            elif stats_descriptions[label]['type'] == 'counter32':
                d= {
                    'name': 'squid_' + label,
                    'call_back': get_stat,
                    'time_max': 60,
                    'value_type': "float",
                    'units': stats_descriptions[label]['units'],
                    'slope': "positive",
                    'format': '%f',
                    'description': label,
                    'groups': 'squid',
                }
            elif stats_descriptions[label]['type'] == 'integer':
                d= {
                    'name': 'squid_' + label,
                    'call_back': get_stat,
                    'time_max': 60,
                    'value_type': "uint",
                    'units': stats_descriptions[label]['units'],
                    'slope': "both",
                    'format': '%u',
                    'description': label,
                    'groups': 'squid',
                }
            else:
                d= {
                'name': 'squid_' + label,
                'call_back': get_stat,
                'time_max': 60,
                'value_type': "float",
                'units': stats_descriptions[label]['units'],
                'slope': "both",
                'format': '%f',
                'description': label,
                'groups': 'squid',
                }
            
            d.update(stats_descriptions[label])
            
            descriptors.append(d)
            
        #else:
            #logging.error("skipped " + label)
            
    return descriptors

def metric_cleanup():
    #logging.shutdown()
    pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    metric_init(None)
    for d in descriptors:
        v = d['call_back'](d['name'])
        if d['value_type'] == 'string':
            print 'value for %s is %s %s' % (d['name'],  v, d['units'])
        elif d['value_type'] == 'uint':
            print 'value for %s is %d %s' % (d['name'],  v, d['units'])
        else:
            print 'value for %s is %4.2f %s' % (d['name'],  v, d['units'])

