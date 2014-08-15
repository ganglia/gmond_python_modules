#!/usr/bin/python
# Name: vmax.py
# Desc: Ganglia module for polling the VMAX UniSphere REST interface for metrics
# Author: Evan Fraser evan.fraser@trademe.co.nz
# Date: July 2014
# Copyright: GPL


import json, os, pprint, re, requests, socket, sys, time

descriptors = list()

unispherePort = 8443

#This is the minimum interval between querying unisphere for metrics
METRICS_CACHE_MAX = 300

METRICS = {
    'time' : 0,
    'data' : {}
}
LAST_METRICS = dict(METRICS)

vmax_dict = {
    'vmax_site1' : { 
        'sid' : '000000000001',
        'site' : 'site1',
        'unisphereIP' : '192.168.1.11',
        'user' : 'user',
        'pass' : 'password'
        },
    'vmax_site2' : { 
        'sid' : '000000000002',
        'site' : 'site2',
        'unisphereIP' : '192.168.1.12',
        'user' : 'user',
        'pass' : 'password'
        }
}

ARRAY_METRICS_TO_POLL = [
    'IO_RATE',
    'HIT_PER_SEC', 
    'MB_READ_PER_SEC', 
    'MB_WRITE_PER_SEC', 
    'READS', 
    'RESPONSE_TIME_READ', 
    'RESPONSE_TIME_WRITE',
    'WRITES'
    ]

POOL_METRICS_TO_POLL = [
    'BE_READS',
    'BE_WRITES',
    'BE_RESPONSE_TIME_READ',
    'BE_RESPONSE_TIME_WRITE',
    'BE_MB_READ_RATE',
    'BE_MB_WRITE_RATE',
    ]

def get_metric(name):
    global METRICS, LAST_METRICS, METRICS_CACHE_MAX, ARRAY_METRICS_TO_POLL, params
    metrics = {}
    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:
        
        #Get all metrics at once, Don't re-poll for 5 minutes because they're no more granular than that anyway.    
        for key in vmax_dict:
            ### Get the Array based metrics first
            baseurl = 'https://' + vmax_dict[key]['unisphereIP'] + ':' + str(unispherePort) + '/univmax/restapi/performance/Array/metrics'
            requestObj = {'arrayParam': 
                          {'endDate': str(int(time.time()*1000)), #End time to specify is now.
                           'startDate': str(int(time.time()*1000)-(300*1000)), #start time is 5 minutes before that
                           'metrics': ARRAY_METRICS_TO_POLL,
                           'symmetrixId': vmax_dict[key]['sid'] #symmetrix ID (full 12 digits)
                           }
                          }

            requestJSON = json.dumps(requestObj, sort_keys=True, indent=4) #turn this into a JSON string
            headers = {'content-type': 'application/json','accept':'application/json'} #set the headers for how we want the response

                #make the actual request, specifying the URL, the JSON from above, standard basic auth, the headers and not to verify the SSL cert
            r = requests.post(baseurl, requestJSON, auth=(vmax_dict[key]['user'], vmax_dict[key]['pass']), headers=headers, verify=False)
            
                #take the raw response text and deserialize it into a python object.
            try:
                responseObj = json.loads(r.text)
            except:
                print "Exception"
                print r.text

            if len(responseObj["iterator"]["resultList"]["result"]) > 0:

                metrics[key + '_cache_hits'] = float(responseObj["iterator"]["resultList"]["result"][0]['HIT_PER_SEC'])
                metrics[key + '_fe_reads'] = float(responseObj["iterator"]["resultList"]["result"][0]['READS'])
                metrics[key + '_fe_writes'] = float(responseObj["iterator"]["resultList"]["result"][0]['WRITES'])
                metrics[key + '_vol_iorate'] = float(responseObj["iterator"]["resultList"]["result"][0]['IO_RATE'])
                metrics[key + '_megabytes_read'] = float(responseObj["iterator"]["resultList"]["result"][0]['MB_READ_PER_SEC'])
                metrics[key + '_megabytes_written'] = float(responseObj["iterator"]["resultList"]["result"][0]['MB_WRITE_PER_SEC'])
                metrics[key + '_response_time_read'] = float(responseObj["iterator"]["resultList"]["result"][0]['RESPONSE_TIME_READ'])
                metrics[key + '_response_time_write'] = float(responseObj["iterator"]["resultList"]["result"][0]['RESPONSE_TIME_WRITE'])

            else:
                print "Short response"
                pprint.pprint(responseObj) 

            ### Now get the pool based metrics for each vmax.
            #Start by getting the list of pools
            baseurl = 'https://' + vmax_dict[key]['unisphereIP'] + ':' + str(unispherePort) + '/univmax/restapi/performance/ThinPool/keys'

            requestObj = {'thinPoolKeyParam': 
                          {
                    'symmetrixId': vmax_dict[key]['sid'] #symmetrix ID (full 12 digits)
                    }
                          }

            requestJSON = json.dumps(requestObj, sort_keys=True, indent=4) #turn this into a JSON string

            headers = {'content-type': 'application/json','accept':'application/json'} #set the headers for how we want the response

            #make the actual request, specifying the URL, the JSON from above, standard basic auth, the headers and not to verify the SSL cert.

            r = requests.post(baseurl, requestJSON, auth=(vmax_dict[key]['user'], vmax_dict[key]['pass']), headers=headers, verify=False)


            #take the raw response text and deserialize it into a python object.
            try:
                responseObj = json.loads(r.text)
            except:
                print "Exception"
                print r.text
                print json.dumps(responseObj, sort_keys=False, indent=4)

            for pool in responseObj["poolKeyResult"]["poolInfo"]:
                baseurl = 'https://' + vmax_dict[key]['unisphereIP'] + ':' + str(unispherePort) + '/univmax/restapi/performance/ThinPool/metrics'

                requestObj = {'thinPoolParam': 
                              {'endDate': str(int(time.time()*1000)), #End time to specify is now.
                               'startDate': str(int(time.time()*1000)-(300*1000)), #start time is 5 minutes before that
                               'metrics': POOL_METRICS_TO_POLL,
                               'poolId': pool["poolId"],
                               'symmetrixId': vmax_dict[key]['sid'] #symmetrix ID (full 12 digits)
                               }
                              }
                requestJSON = json.dumps(requestObj, sort_keys=True, indent=4) #turn this into a JSON string

                headers = {'content-type': 'application/json','accept':'application/json'} #set the headers for how we want the response

                #make the actual request, specifying the URL, the JSON from above, standard basic auth, the headers and not to verify the SSL cert.
                r = requests.post(baseurl, requestJSON, auth=(vmax_dict[key]['user'], vmax_dict[key]['pass']), headers=headers, verify=False)

                #take the raw response text and deserialize it into a python object.
                try:
                    responseObj = json.loads(r.text)
                except:
                    print "Exception"
                    print r.text
                    print json.dumps(responseObj, sort_keys=False, indent=4)

                if len(responseObj["iterator"]["resultList"]["result"]) > 0:

                    metrics[key + '_' + pool["poolId"] + '_reads'] = float(responseObj["iterator"]["resultList"]["result"][0]['BE_READS'])
                    metrics[key + '_' + pool["poolId"] + '_writes'] = float(responseObj["iterator"]["resultList"]["result"][0]['BE_WRITES'])
                    metrics[key + '_' + pool["poolId"] + '_response_time_reads'] = float(responseObj["iterator"]["resultList"]["result"][0]['BE_RESPONSE_TIME_READ'])
                    metrics[key + '_' + pool["poolId"] + '_response_time_writes'] = float(responseObj["iterator"]["resultList"]["result"][0]['BE_RESPONSE_TIME_WRITE'])
                    metrics[key + '_' + pool["poolId"] + '_megabytes_read'] = float(responseObj["iterator"]["resultList"]["result"][0]['BE_MB_READ_RATE'])
                    metrics[key + '_' + pool["poolId"] + '_megabytes_written'] = float(responseObj["iterator"]["resultList"]["result"][0]['BE_MB_WRITE_RATE'])

                else:
                    print "Short response"
                    pprint.pprint(responseObj) 

            
        LAST_METRICS = dict(METRICS)
        METRICS = {
            'time': time.time(),
            'data': metrics
        }


    return METRICS['data'][name]


# define_metrics will run an snmp query on an ipaddr, find interfaces, build descriptors and set spoof_host
# define_metrics is called from metric_init
def define_metrics(Desc_Skel, unisphereIP, sid, site):
    global vmax_dict
    spoof_string = unisphereIP + ':vmax_' + site
    vmax_name = 'vmax_' + site

    #FE Cache Hits/s
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : vmax_name + '_cache_hits',
                "units"       : "iops",
                "description" : "Cache Hits/s",
                "groups"      : "iops",
                "spoof_host"  : spoof_string,
                }))
    #FE Read IOPs
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : vmax_name + '_fe_reads',
                "units"       : "iops",
                "description" : "FE Read IOPs",
                "groups"      : "iops",
                "spoof_host"  : spoof_string,
                }))
    #FE Write IOPs
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : vmax_name + '_fe_writes',
                "units"       : "iops",
                "description" : "FE Write IOPs",
                "groups"      : "iops",
                "spoof_host"  : spoof_string,
                }))
    #Array MB_READ_PER_SEC
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : vmax_name + '_megabytes_read',
                "units"       : "MB/s",
                "description" : "Array MB/s Reads",
                "groups"      : "Throughput",
                "spoof_host"  : spoof_string,
                }))
    #Array MB_WRITE_PER_SEC
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : vmax_name + '_megabytes_written',
                "units"       : "MB/s",
                "description" : "Array MB/s Writes",
                "groups"      : "Throughput",
                "spoof_host"  : spoof_string,
                }))
    #Array RESPONSE_TIME_READ
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : vmax_name + '_response_time_read',
                "units"       : "ms",
                "description" : "Array Read Response Time",
                "groups"      : "Latency",
                "spoof_host"  : spoof_string,
                }))
    #Array RESPONSE_TIME_WRITE
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : vmax_name + '_response_time_write',
                "units"       : "ms",
                "description" : "Array Write Response Time",
                "groups"      : "Latency",
                "spoof_host"  : spoof_string,
                }))
    #Total Volume IO_RATE
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : vmax_name + '_vol_iorate',
                "units"       : "iops",
                "description" : "Array IOPs",
                "groups"      : "iops",
                "spoof_host"  : spoof_string,
                }))

    ###Perform API query to get list of Thinpools

    baseurl = 'https://' + unisphereIP + ':8443/univmax/restapi/performance/ThinPool/keys'

    requestObj = {'thinPoolKeyParam': 
                  {
            'symmetrixId': sid
            }
                  }
          
    requestJSON = json.dumps(requestObj, sort_keys=True, indent=4) #turn this into a JSON string

    headers = {'content-type': 'application/json','accept':'application/json'} #set the headers for how we want the response

    #make the actual request, specifying the URL, the JSON from above, standard basic auth, the headers and not to verify the SSL cert.
    r = requests.post(baseurl, requestJSON, auth=(vmax_dict[vmax_name]['user'], vmax_dict[vmax_name]['pass']), headers=headers, verify=False)


    #take the raw response text and deserialize it into a python object.
    try:
        responseObj = json.loads(r.text)
    except:
        print "Exception"
        print r.text
        print json.dumps(responseObj, sort_keys=False, indent=4)

    for pool in responseObj["poolKeyResult"]["poolInfo"]:

        #BE_READS
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(vmax_name + '_' + pool["poolId"] + '_reads'),
                    "units"       : "iops",
                    "description" : "Pool BE Read IOPs",
                    "groups"      : "iops",
                    "spoof_host"  : spoof_string,
                    }))

        #BE_WRITES
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(vmax_name + '_' + pool["poolId"] + '_writes'),
                    "units"       : "iops",
                    "description" : "Pool BE Writes IOPs",
                    "groups"      : "iops",
                    "spoof_host"  : spoof_string,
                    }))

        #BE_RESPONSE_TIME_READ
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(vmax_name + '_' + pool["poolId"] + '_response_time_reads'),
                    "units"       : "ms",
                    "description" : "Pool BE Read Latency",
                    "groups"      : "Latency",
                    "spoof_host"  : spoof_string,
                    }))

        #BE_RESPONSE_TIME_WRITE
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(vmax_name + '_' + pool["poolId"] + '_response_time_writes'),
                    "units"       : "ms",
                    "description" : "Pool BE Write Latency",
                    "groups"      : "Latency",
                    "spoof_host"  : spoof_string,
                    }))
        #BE_MB_READ_RATE
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(vmax_name + '_' + pool["poolId"] + '_megabytes_read'),
                    "units"       : "MB/s",
                    "description" : "Pool BE MB/s read",
                    "groups"      : "Throughput",
                    "spoof_host"  : spoof_string,
                    }))
        #BE_MB_WRITE_RATE
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(vmax_name + '_' + pool["poolId"] + '_megabytes_written'),
                    "units"       : "MB/s",
                    "description" : "Pool BE MB/s writes",
                    "groups"      : "Throughput",
                    "spoof_host"  : spoof_string,
                    }))


    return descriptors

def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread, Debug, newdict, vmax_dict

    print '[switch] Received the following parameters'
    print params

    #Import the params into the global NIPARAMS

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_metric,
        'time_max'    : 600,
        'value_type'  : 'double',
        'format'      : '%0f',
        'units'       : 'XXX',
        'slope'       : 'both',
        'description' : 'XXX',
        'groups'      : 'switch',
        }  

    # Find all the vmax's passed in params    
    for vmax in vmax_dict:
             # pass skel, ip and name to define_metrics to create descriptors
        descriptors = define_metrics(Desc_Skel, vmax_dict[vmax]['unisphereIP'], vmax_dict[vmax]['sid'], vmax_dict[vmax]['site'])
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

 
