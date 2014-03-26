#!/usr/bin/python
#Name: netapp_api_cmode.py
#Desc: Uses Netapp Data Ontap API to get per volume latency & iops metrics.  Download the managemability SDK from now.netapp.com
#Author: Evan Fraser <evan.fraser@trademe.co.nz>
#Date: 13/08/2012
#Updated 26/03/2014: Now polls each filer as a separate thread and now only supports Clustered ONTAP 8.2+

import sys
import time
import pprint
import unicodedata
import threading
import os
import time

sys.path.append("/opt/netapp/sdk/lib/python/NetApp")
from NaServer import *

descriptors = list()
params = {}
filerdict = {}
FASMETRICS = {
    'time' : 0,
    'data' : {}
}
LAST_FASMETRICS = dict(FASMETRICS)
#metrics = {}
#This is the minimum interval between querying the RPA for metrics
FASMETRICS_CACHE_MAX = 10

class GetMetricsThread(threading.Thread):
    def __init__(self, MetricName, FilerName):
        self.filer_metrics = None
        self.MetricName = MetricName
        self.FilerName = FilerName
        super(GetMetricsThread, self).__init__()
    
    def run(self):
        self.filer_metrics = {}
        metric = self.MetricName
        filer = self.FilerName
        s = NaServer(filerdict[filer]['ipaddr'], 1, 3)
        out = s.set_transport_type('HTTPS')
        if (out and out.results_errno() != 0) :
            r = out.results_reason()
            print ("Connection to filer failed: " + r + "\n")
            sys.exit(2)
            
        out = s.set_style('LOGIN')
        if (out and out.results_errno() != 0) :
            r = out.results_reason()
            print ("Connection to filer failed: " + r + "\n")
            sys.exit(2)
        out = s.set_admin_user(filerdict[filer]['user'], filerdict[filer]['password'])

        #In C-mode, perf-object-get-instances-iter-start doesn't exist
        # Also need to get list of instance names to provide to the perf-object-get-instances now.
        #Get list of volume instances
        obj_name = "volume"
        instance_in = NaElement("perf-object-instance-list-info-iter")
        instance_in.child_add_string("objectname", obj_name)
        #Invoke API
        out = s.invoke_elem(instance_in)
        if(out.results_status() == "failed"):
            print("Invoke failed: " + out.results_reason() + "\n")
            sys.exit(2)
        
        #create an object for all the instances which we will pass to the perf-object-get-instances below
        instance_obj = NaElement("instances")
        instance_list = out.child_get("attributes-list")
        instances = instance_list.children_get()
        instance_names = []
        for i in instances:
            instance_obj.child_add_string("instance", i.child_get_string("name"))

        #Get perf objects for each instance
            perf_in = NaElement("perf-object-get-instances")
            perf_in.child_add_string("objectname", obj_name)
            perf_in.child_add(instance_obj)

        #Create object of type counters
        counters = NaElement("counters")
        #Add counter names to the object
        counter_name_list = ["total_ops","avg_latency","read_ops","read_latency","write_ops","write_latency"]
        for c in counter_name_list:
            counters.child_add_string("counter", c)
            perf_in.child_add(counters)

        #Invoke API
        out = s.invoke_elem(perf_in)

        if(out.results_status() == "failed"):
            print(out.results_reason() + "\n")
            sys.exit(2)
    
        filername = filerdict[filer]['name']
        instances_list = out.child_get("instances")            
        instances = instances_list.children_get()

        for inst in instances:
            inst_name = unicodedata.normalize('NFKD',inst.child_get_string("name")).encode('ascii','ignore')
            counters_list = inst.child_get("counters")
            counters = counters_list.children_get()

            for counter in counters:
                counter_name = unicodedata.normalize('NFKD',counter.child_get_string("name")).encode('ascii','ignore')         
                counter_value = counter.child_get_string("value")
                counter_unit = counter.child_get_string("unit")           
                self.filer_metrics[filername + '_vol_' + inst_name + '_' + counter_name] = float(counter_value)

        
def get_metrics(name):
    global FASMETRICS, LAST_FASMETRICS, FASMETRICS_CACHE_MAX, params
    max_records = 10
    threads = []
    metrics = {}
    if (time.time() - FASMETRICS['time']) > FASMETRICS_CACHE_MAX:
        #start = time.time()
        for filer in filerdict.keys():
            # Execute threads to gather metrics from each filer
            thread = GetMetricsThread(name,filer)
            thread.start()
            threads.append(thread)

        #Wait for the threads to return here
        for t in threads:
            t.join()
            metrics.update(t.filer_metrics)
        #end = time.time()
        #print "elapsed time was: ",(end - start)

        # update cache
        LAST_FASMETRICS = dict(FASMETRICS)
        FASMETRICS = {
            'time': time.time(),
            'data': metrics
            }
    else: 
        metrics = FASMETRICS['data']

    #calculate change in values and return
    if 'total_ops' in name:
        try:
            delta = float(FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name])/(FASMETRICS['time'] - LAST_FASMETRICS['time'])
            if delta < 0:
                print "Less than 0"
                delta = 0
        except StandardError:
            delta = 0
        #This is the Operations per second
        return delta

    elif 'avg_latency' in name:
        try: 
            #T1 and T2
            #(T2_lat - T1_lat) / (T2_ops - T1_ops)
            #Find the metric name of the base counter
            total_ops_name = name.replace('avg_latency', 'total_ops')
            #Calculate latency in time (div 100 to change to ms)
            return float((FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name]) / (FASMETRICS['data'][total_ops_name] -LAST_FASMETRICS['data'][total_ops_name])) / 100
        except StandardError:
            return 0
    elif 'read_ops' in name:

        try:
            delta = float(FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name])/(FASMETRICS['time'] - LAST_FASMETRICS['time'])
            if delta < 0:
                print "Less than 0"
                delta = 0
        except StandardError:
            delta = 0
        return delta

    elif 'read_latency' in name:
        try: 
            read_ops_name = name.replace('read_latency', 'read_ops')
            return float((FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name]) / (FASMETRICS['data'][read_ops_name] -LAST_FASMETRICS['data'][read_ops_name])) / 100
        except StandardError:
            return 0
    elif 'write_ops' in name:
        try:
            delta = float(FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name])/(FASMETRICS['time'] - LAST_FASMETRICS['time'])
            if delta < 0:
                print "Less than 0"
                delta = 0
        except StandardError:
            delta = 0
        return delta

    elif 'write_latency' in name:
        try: 
            write_ops_name = name.replace('write_latency', 'write_ops')
            return float((FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name]) / (FASMETRICS['data'][write_ops_name] -LAST_FASMETRICS['data'][write_ops_name])) / 100
        except StandardError:
            return 0
            

    return 0    
        


def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d
    

def define_metrics_thread(Desc_Skel,filer,params):
    global descriptors
    s = NaServer(params[filer]['ipaddr'], 1, 3)
    out = s.set_transport_type('HTTPS')
    if (out and out.results_errno() != 0) :
        r = out.results_reason()
        print ("Connection to filer failed: " + r + "\n")
        sys.exit(2)
            
    out = s.set_style('LOGIN')
    if (out and out.results_errno() != 0) :
        r = out.results_reason()
        print ("Connection to filer failed: " + r + "\n")
        sys.exit(2)
    out = s.set_admin_user(params[filer]['user'], params[filer]['password'])

    #In C-mode, perf-object-get-instances-iter-start doesn't exist
    # Also need to get list of instance names to provide to the perf-object-get-instances now.
    #Get list of volume instances
    obj_name = "volume"
    instance_in = NaElement("perf-object-instance-list-info-iter")
    instance_in.child_add_string("objectname", obj_name)

    #Invoke API
    out = s.invoke_elem(instance_in)
    if(out.results_status() == "failed"):
        print("Invoke failed: " + out.results_reason() + "\n")
        sys.exit(2)
        
    #create an object for all the instances which we will pass to the perf-object-get-instances below
    instance_obj = NaElement("instances")
    instance_list = out.child_get("attributes-list")
    instances = instance_list.children_get()
    instance_names = []
    for i in instances:
        instance_obj.child_add_string("instance", i.child_get_string("name"))

            
    #Get perf objects for each instance
    perf_in = NaElement("perf-object-get-instances")
    perf_in.child_add_string("objectname", obj_name)
    perf_in.child_add(instance_obj)
    #perf_in.

    #Hard coded volume, only volume stats gathered at present
    #Create object of type counters
    counters = NaElement("counters")
    #Add counter names to the object
    counter_name_list = ["total_ops","avg_latency","read_ops","read_latency","write_ops","write_latency"]
    for c in counter_name_list:
        counters.child_add_string("counter", c)
        perf_in.child_add(counters)
        

    #Invoke API
    out = s.invoke_elem(perf_in)
    if(out.results_status() == "failed"):
        print("Invoke failed: " + out.results_reason() + "\n")
        sys.exit(2)


    #iter_tag = out.child_get_string("tag")
    #num_records = 1
    filername = params[filer]['name']

    instances_list = out.child_get("instances")            
    instances = instances_list.children_get()

    for inst in instances:
        inst_name = unicodedata.normalize('NFKD',inst.child_get_string("name")).encode('ascii','ignore')
        counters_list = inst.child_get("counters")
        counters = counters_list.children_get()

        for counter in counters:
            counter_name = unicodedata.normalize('NFKD',counter.child_get_string("name")).encode('ascii','ignore')
            counter_value = counter.child_get_string("value")
            counter_unit = counter.child_get_string("unit")
            if 'total_ops' in counter_name:
                descriptors.append(create_desc(Desc_Skel, {
                            "name"        : filername + '_vol_' + inst_name + '_' + counter_name,
                            "units"       : 'iops',
                            "description" : "volume iops",
                            "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                            "groups"      : "iops"
                            }))
            elif 'avg_latency' in counter_name:
                descriptors.append(create_desc(Desc_Skel, {
                            "name"        : filername + '_vol_' + inst_name + '_' + counter_name,
                            "units"       : 'ms',
                            "description" : "volume avg latency",
                            "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                            "groups"      : "latency"
                            }))
            elif 'read_ops' in counter_name:
                descriptors.append(create_desc(Desc_Skel, {
                            "name"        : filername + '_vol_' + inst_name + '_' + counter_name,
                            "units"       : 'iops',
                            "description" : "volume read iops",
                            "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                            "groups"      : "iops"
                            }))
            elif 'read_latency' in counter_name:
                descriptors.append(create_desc(Desc_Skel, {
                            "name"        : filername + '_vol_' + inst_name + '_' + counter_name,
                            "units"       : 'ms',
                            "description" : "volume read latency",
                            "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                            "groups"      : "latency"
                            }))
            elif 'write_ops' in counter_name:
                descriptors.append(create_desc(Desc_Skel, {
                            "name"        : filername + '_vol_' + inst_name + '_' + counter_name,
                            "units"       : 'iops',
                            "description" : "volume write iops",
                            "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                            "groups"      : "iops"
                            }))
            elif 'write_latency' in counter_name:
                descriptors.append(create_desc(Desc_Skel, {
                            "name"        : filername + '_vol_' + inst_name + '_' + counter_name,
                            "units"       : 'ms',
                            "description" : "volume write latency",
                            "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                            "groups"      : "latency"
                            }))
    #return descriptors
    

def define_metrics(Desc_Skel,params):
    global descriptors
    max_records = 10
    threads = []
    for filer in params.keys():
        #call define_metrics_thread as separate threads for each filer
        thread = threading.Thread(target=define_metrics_thread, args=(Desc_Skel,filer,params))
        thread.start()
        threads.append(thread)

    for t in threads:
        t.join()
    
    return descriptors

def metric_init(params):
    global descriptors,filerdict
    print 'netapp_stats] Received the following parameters'
    params = {
        'filer1' : {
            'name' : 'cluster1mgmt.local',
            'ipaddr' : '192.168.1.100',
            'user' : 'monitoruser',
            'password' : 'password',
              },
        'filer2' : {
            'name' : 'cluster2mgmt.local',
            'ipaddr' : '192.168.1.200',
            'user' : 'monitoruser',
            'password' : 'password',
              },
        }

    filerdict = dict(params)
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
        'spoof_host'  : 'XXX',
        }  


    descriptors = define_metrics(Desc_Skel,params)

    return descriptors

# For CLI Debugging:
if __name__ == '__main__':
    #global params
    params = {}
    descriptors = metric_init(params)
    pprint.pprint(descriptors)
    #print len(descriptors)
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            #print v
            print 'value for %s is %.2f' % (d['name'],  v)        
        print 'Sleeping 5 seconds'
        time.sleep(5)
