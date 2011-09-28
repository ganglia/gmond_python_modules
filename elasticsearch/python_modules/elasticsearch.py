#! /usr/bin/python

import os, time, json, string, urllib, sys, socket, jsonpath

global url, ip, last_update, keyToPath

def get_ip_address():
  host = os.uname()[1]
  ipt = socket.gethostbyname_ex(host)
  ipt = ipt[2]
  ip = ipt[0]
  return(ip)

# Set IP address and JSON Url
ip=get_ip_address()
url="http://"+ ip + ":9200/_cluster/nodes/" + ip + "/stats"

# short name to full path for stats
keyToPath=dict()

# Initial time modification stamp - Used to determine
# when JSON is updated
last_update = time.time()

keyToPath['es_heap_committed'] = "nodes.*.jvm.mem.heap_committed_in_bytes"
keyToPath['es_heap_used'] = "nodes.*.jvm.mem.heap_used_in_bytes"
keyToPath['es_threads'] = "nodes.*.jvm.threads.count"
keyToPath['es_gc_time'] = "nodes.*.jvm.gc.collection_time_in_millis"
keyToPath['es_tcp_active_opens'] = "nodes.*.network.tcp.active_opens"
keyToPath['es_tcp_curr_estab'] = "nodes.*.network.tcp.curr_estab"
keyToPath['es_tcp_attempt_fails']= "nodes.*.network.tcp.active_opens"
keyToPath['es_tcp_in_errs'] = "nodes.*.network.tcp.in_errs"
keyToPath['es_tcp_out_rsts'] = "nodes.*.network.tcp.out_rsts"
keyToPath['es_transport_open'] = "nodes.*.transport.server_open"
keyToPath['es_http_open'] = "nodes.*.http.server_open"
keyToPath['es_indices_size'] = "nodes.*.indices.size_in_bytes"
keyToPath['es_gc_count'] = "nodes.*.jvm.gc.collection_count"
keyToPath['es_merges_current'] = "nodes.*.indices.merges.current"
keyToPath['es_merges_total'] = "nodes.*.indices.merges.total"
keyToPath['es_merges_time'] = "nodes.*.indices.merges.total_time_in_millis"
keyToPath['es_num_docs'] = "nodes.*.indices.docs.num_docs"

def getStat(name):
    global last_update, result, url

    # If time delta is > 20 seconds, then update the JSON results
    now = time.time()
    diff = now - last_update
    if diff > 20:
        print '[elasticsearch] ' + str(diff) + ' seconds passed - Fetching ' + url
        result = json.load(urllib.urlopen(url))
        last_update = now

    JsonPathName=keyToPath[name]
    tmp = jsonpath.jsonpath(result, JsonPathName )

    # Convert List to String
    val = " ".join(["%s" % el for el in tmp])

    # Check for integer only result
    if val.isdigit():
        val = int(val)
    print "********** " + name + ": " + str(val)
    return val

def create_desc(prop):
    d = Desc_Skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_init(params):
    global result, url, descriptors, Desc_Skel

    print '[elasticsearch] Received the following parameters'
    print params

    # First iteration - Grab statistics
    print '[elasticsearch] Fetching ' + url
    result = json.load(urllib.urlopen(url))

    descriptors = []

    if "metric_group" not in params:
        params["metric_group"] = "elasticsearch"

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : getStat,
        'time_max'    : 60,
        'value_type'  : 'uint',
        'units'       : 'proc',
        'slope'       : 'both',
        'format'      : '%d',
        'description' : 'XXX',
        'groups'      : params["metric_group"],
    }

    descriptors.append(create_desc({
         'name'       : 'es_heap_committed',
         'value_type' : 'float',
         'units'      : 'KBytes',
         'format'     : '%.0f',
         'description': 'Java Heap Committed (KBytes)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_heap_used',
         'value_type' : 'float',
         'units'      : 'KBytes',
         'format'     : '%.0f',
         'description': 'Java Heap Used (KBytes)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_threads',
         'value_type' : 'uint',
         'units'      : 'threads',
         'format'     : '%d',
         'description': 'Threads (open)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_gc_time',
         'value_type' : 'uint',
         'units'      : 'ms',
         'format'     : '%d',
         'description': 'Java GC Time (ms)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_tcp_active_opens',
         'value_type' : 'uint',
         'units'      : 'sockets',
         'format'     : '%d',
         'description': 'TCP (open)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_tcp_curr_estab',
         'value_type' : 'uint',
         'units'      : 'sockets',
         'format'     : '%d',
         'description': 'TCP (established)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_tcp_attempt_fails',
         'value_type' : 'uint',
         'units'      : 'units',
         'format'     : '%d',
         'description': 'TCP (attempt_fails)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_tcp_in_errs',
         'value_type' : 'uint',
         'units'      : 'units',
         'format'     : '%d',
         'description': 'TCP (in_errs)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_tcp_out_rsts',
         'value_type' : 'uint',
         'units'      : 'units',
         'format'     : '%d',
         'description': 'TCP (out_rsts)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_transport_open',
         'value_type' : 'uint',
         'units'      : 'sockets',
         'format'     : '%d',
         'description': 'Transport Open (sockets)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_http_open',
         'value_type' : 'uint',
         'units'      : 'sockets',
         'format'     : '%d',
         'description': 'HTTP Open (sockets)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_indices_size',
         'value_type' : 'float',
         'units'      : 'KBytes',
         'format'     : '%.0f',
         'description': 'Index Size (KBytes)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_gc_count',
         'value_type' : 'uint',
         'units'      : 'units',
         'format'     : '%d',
         'description': 'Java GC Count',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_merges_current',
         'value_type' : 'uint',
         'units'      : 'units',
         'format'     : '%d',
         'description': 'Merges (current)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_merges_total',
         'value_type' : 'uint',
         'units'      : 'units',
         'format'     : '%d',
         'description': 'Merges (total)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_merges_time',
         'value_type' : 'uint',
         'units'      : 'ms',
         'format'     : '%d',
         'description': 'Merges Time (ms)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_num_docs',
         'value_type' : 'float',
         'units'      : 'units',
         'format'     : '%.0f',
         'description': 'Number of Documents',
    }))

    return descriptors
 
def metric_cleanup():
  pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    metric_init({})
    for d in descriptors:
        v = d['call_back'](d['name'])
        print 'value for %s is %s' % (d['name'], str(v))
 
