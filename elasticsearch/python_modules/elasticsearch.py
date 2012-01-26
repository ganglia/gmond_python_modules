#! /usr/bin/python

import json
import os
import socket
import time
import urllib

global url, ip, last_update, keyToPath

def get_ip_address():
  host = os.uname()[1]
  ipt = socket.gethostbyname_ex(host)
  ipt = ipt[2]
  ip = ipt[0]
  return(ip)

def dig_it_up(obj,path):
    try:
        if type(path) in (str,unicode):
            path = path.split('.')
        return reduce(lambda x,y:x[y],path,obj)
    except:
        return False

# Set IP address and JSON Url
ip=get_ip_address()
url="http://"+ ip + ":9200/_cluster/nodes/" + ip + "/stats"

# short name to full path for stats
keyToPath=dict()

# Initial time modification stamp - Used to determine
# when JSON is updated
last_update = time.time()

keyToPath['es_heap_committed'] = "nodes.%s.jvm.mem.heap_committed_in_bytes"
keyToPath['es_heap_used'] = "nodes.%s.jvm.mem.heap_used_in_bytes"
keyToPath['es_threads'] = "nodes.%s.jvm.threads.count"
keyToPath['es_gc_time'] = "nodes.%s.jvm.gc.collection_time_in_millis"
keyToPath['es_transport_open'] = "nodes.%s.transport.server_open"
keyToPath['es_http_current_open'] = "nodes.%s.http.current_open"
keyToPath['es_http_total_open'] = "nodes.%s.http.total_opened"
keyToPath['es_indices_size'] = "nodes.%s.indices.store.size_in_bytes"
keyToPath['es_gc_count'] = "nodes.%s.jvm.gc.collection_count"
keyToPath['es_merges_current'] = "nodes.%s.indices.merges.current"
keyToPath['es_merges_current_size'] = "nodes.%s.indices.merges.current_size_in_bytes"
keyToPath['es_merges_total'] = "nodes.%s.indices.merges.total"
keyToPath['es_merges_total_size'] = "nodes.%s.indices.merges.total_size_in_bytes"
keyToPath['es_merges_time'] = "nodes.%s.indices.merges.total_time_in_millis"
keyToPath['es_docs_count'] = "nodes.%s.indices.docs.count"
keyToPath['es_open_file_descriptors'] = "nodes.%s.process.open_file_descriptors"
keyToPath['es_cache_field_eviction'] = "nodes.%s.indices.cache.field_evictions"
keyToPath['es_cache_field_size'] = "nodes.%s.indices.cache.field_size_in_bytes"
keyToPath['es_cache_filter_count'] = "nodes.%s.indices.cache.filter_count"
keyToPath['es_cache_filter_evictions'] = "nodes.%s.indices.cache.filter_evictions"
keyToPath['es_cache_filter_size'] = "nodes.%s.indices.cache.filter_size_in_bytes"
keyToPath['es_queries_current'] = "nodes.%s.indices.search.query_current"
keyToPath['es_query_time'] = "nodes.%s.indices.search.query_time_in_millis"
keyToPath['es_queries_total'] = "nodes.%s.indices.search.query_total"


def getStat(name):
    global last_update, result, url

    # If time delta is > 20 seconds, then update the JSON results
    now = time.time()
    diff = now - last_update
    if diff > 20:
        print '[elasticsearch] ' + str(diff) + ' seconds passed - Fetching ' + url
        result = json.load(urllib.urlopen(url))
        last_update = now

    node = result['nodes'].keys()[0]
    val = dig_it_up(result, keyToPath[name] % node )

    # Check to make sure we have a valid result
    # JsonPath returns False if no match found
    if not isinstance(val,bool):
        return int(val)
    else:
        return None

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
        'units'       : 'units',
        'slope'       : 'both',
        'format'      : '%d',
        'description' : 'XXX',
        'groups'      : params["metric_group"],
    }

    descriptors.append(create_desc({
         'name'       : 'es_heap_committed',
         'units'      : 'Bytes',
         'format'     : '%d',
         'description': 'Java Heap Committed (Bytes)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_heap_used',
         'units'      : 'Bytes',
         'format'     : '%d',
         'description': 'Java Heap Used (Bytes)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_threads',
         'units'      : 'threads',
         'format'     : '%d',
         'description': 'Threads (open)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_gc_time',
         'units'      : 'ms',
         'format'     : '%d',
         'slope'      : 'positive',
         'description': 'Java GC Time (ms)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_transport_open',
         'units'      : 'sockets',
         'format'     : '%d',
         'description': 'Transport Open (sockets)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_http_current_open',
         'units'      : 'sockets',
         'format'     : '%d',
         'description': 'HTTP Open (sockets)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_http_total_open',
         'units'      : 'sockets',
         'format'     : '%d',
         'description': 'HTTP Open (sockets)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_indices_size',
         'units'      : 'Bytes',
         'format'     : '%d',
         'description': 'Index Size (Bytes)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_gc_count',
         'format'     : '%d',
         'slope'      : 'positive',
         'description': 'Java GC Count',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_merges_current',
         'format'     : '%d',
         'description': 'Merges (current)',
    }))
    
    descriptors.append(create_desc({
         'name'       : 'es_merges_total',
         'format'     : '%d',
         'slope'      : 'positive',
         'description': 'Merges (total)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_merges_current_size',
         'units'      : 'Bytes',
         'format'     : '%d',
         'description': 'Merges size (current)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_merges_total_size',
         'units'      : 'Bytes',
         'format'     : '%d',
         'slope'      : 'positive',
         'description': 'Merges size (total)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_merges_time',
         'units'      : 'ms',
         'format'     : '%d',
         'slope'      : 'positive',
         'description': 'Merges Time (ms)',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_docs_count',
         'units'      : 'docs',
         'format'     : '%d',
         'description': 'Number of Documents',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_open_file_descriptors',
         'units'      : 'files',
         'format'     : '%d',
         'description': 'Open File Descriptors',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_cache_field_eviction',
         'units'      : 'units',
         'format'     : '%d',
         'slope'      : 'positive',
         'description': 'Field Cache Evictions',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_cache_field_size',
         'units'      : 'Bytes',
         'format'     : '%d',
         'description': 'Field Cache Size',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_cache_filter_count',
         'format'     : '%d',
         'description': 'Filter Cache Count',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_cache_filter_evictions',
         'format'     : '%d',
         'slope'      : 'positive',
         'description': 'Filter Cache Evictions',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_cache_filter_size',
         'units'      : 'Bytes',
         'format'     : '%d',
         'description': 'Filter Cache Size',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_queries_current',
         'units'      : 'Queries',
         'format'     : '%d',
         'description': 'Current Queries',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_query_time',
         'units'      : 'ms',
         'format'     : '%d',
         'slope'      : 'positive',
         'description': 'Total Query Time',
    }))

    descriptors.append(create_desc({
         'name'       : 'es_queries_total',
         'units'      : 'Queries',
         'format'     : '%d',
         'slope'      : 'positive',
         'description': 'Total Queries',
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
 
