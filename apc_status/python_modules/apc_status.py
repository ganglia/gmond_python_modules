#
#
# Module: apc_status
# Graphs the status of APC: Another PHP Cache
#
# Useage: To use this, you need to copy the apc-json.php file to your document root of the local webserver.
#         The path to the apc-json.php should be set in conf.d/apc_status.pyconf
#
# Author: Jacob V. Rasmussen (jacobvrasmussen@gmail.com)
# Site: http://blackthorne.dk
#

import urllib2
import json
import traceback

NAME_PREFIX = "apc_"

APC_STATUS_URL = ""

descriptors = list()
Desc_Skel   = {}
metric_list = {
	NAME_PREFIX + 'num_slots'	: { 'type': 'uint',  'format' : '%d', 'unit': 'Slots', 		'desc': 'Number of slots' },
	NAME_PREFIX + 'num_hits'	: { 'type': 'uint',  'format' : '%d', 'unit': 'Hits', 		'desc': 'Number of cache hits' },
	NAME_PREFIX + 'num_misses'	: { 'type': 'uint',  'format' : '%d', 'unit': 'Misses', 	'desc': 'Number of cache misses' },
	NAME_PREFIX + 'num_inserts'	: { 'type': 'uint',  'format' : '%d', 'unit': 'Inserts', 	'desc': 'Number of cache inserts' },
	NAME_PREFIX + 'expunges'	: { 'type': 'uint',  'format' : '%d', 'unit': 'Deletes', 	'desc': 'Number of cache deletes' },
	NAME_PREFIX + 'mem_size'	: { 'type': 'uint',  'format' : '%d', 'unit': 'Bytes', 		'desc': 'Memory size' },
	NAME_PREFIX + 'num_entries'	: { 'type': 'uint',  'format' : '%d', 'unit': 'Entries', 	'desc': 'Cached Files' },
	NAME_PREFIX + 'uptime'		: { 'type': 'uint',  'format' : '%d', 'unit': 'seconds',	'desc': 'Uptime' },
	NAME_PREFIX + 'request_rate'	: { 'type': 'float', 'format' : '%f', 'unit': 'requests/sec', 	'desc': 'Request Rate (hits, misses)' },
	NAME_PREFIX + 'hit_rate'	: { 'type': 'float', 'format' : '%f', 'unit': 'requests/sec', 	'desc': 'Hit Rate' },
	NAME_PREFIX + 'miss_rate'	: { 'type': 'float', 'format' : '%f', 'unit': 'requests/sec', 	'desc': 'Miss Rate' },
	NAME_PREFIX + 'insert_rate'	: { 'type': 'float', 'format' : '%f', 'unit': 'requests/sec', 	'desc': 'Insert Rate' },
	NAME_PREFIX + 'num_seg'		: { 'type': 'uint',  'format' : '%d', 'unit': 'fragments', 	'desc': 'Segments' },
	NAME_PREFIX + 'mem_avail'	: { 'type': 'uint',  'format' : '%d', 'unit': 'bytes', 		'desc': 'Free Memory' },
	NAME_PREFIX + 'mem_used'	: { 'type': 'uint',  'format' : '%d', 'unit': 'bytes', 		'desc': 'Used Memory' },
	}

def get_value(name):
	try:
		req = urllib2.Request(APC_STATUS_URL, None, {'user-agent':'ganglia-apc-python'})
		opener = urllib2.build_opener()
		f = opener.open(req)
		apc_stats = json.load(f)

	except urllib2.URLError:
		traceback.print_exc()

	return apc_stats[name[len(NAME_PREFIX):]]

def create_desc(prop):
	d = Desc_Skel.copy()
	for k,v in prop.iteritems():
		d[k] = v
	return d

def metric_init(params):
	global descriptors, Desc_Skel, APC_STATUS_URL

	if "metric_group" not in params:
		params["metric_group"] = "apc_cache"

	Desc_Skel = {
		'name'		: 'XXX',
		'call_back'	: get_value,
		'time_max'	: 60,
		'value_type'	: 'uint',
		'units'		: 'proc',
		'slope'		: 'both',
		'format'	: '%d',
		'description'	: 'XXX',
		'groups'	: params["metric_group"],
		}

	if "refresh_rate" not in params:
		params["refresh_rate"] = 15

	if "url" not in params:
		params["url"] = "http://localhost/apc-json.php"
	
	
	APC_STATUS_URL = params["url"]

	if "spoof_host" in params:
		Desc_Skel["spoof_host"] = params["spoof_host"]

	for k,v in metric_list.iteritems():
		descriptors.append(create_desc({
			"name"		: k,
			"call_back"	: get_value,
			"value_type"	: v["type"],
			"units"		: v["unit"],
			"format"	: v["format"],
			"description"	: v["desc"],
			}))

	return descriptors

def metric_cleanup():
	pass

if __name__ == '__main__':
	metric_init({})
	for d in descriptors:
		v = d['call_back'](d['name'])
		print 'value for %s is %s' % (d['name'], v)


