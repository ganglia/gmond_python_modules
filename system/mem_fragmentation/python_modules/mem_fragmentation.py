import sys
import re
import time
import copy

PARAMS = {}

METRICS = {
    'time' : 0,
    'data' : {}
}

NAME_PREFIX = "buddy"

#Normal: 1046*4kB 529*8kB 129*16kB 36*32kB 17*64kB 5*128kB 26*256kB 40*512kB 13*1024kB 16*2048kB 94*4096kB = 471600kB

buddyinfo_file = "/proc/buddyinfo"

LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_MAX = 5

stats_pos = {} 

stats_pos = {
  '0004k' : 4,
  '0008k' : 5,
  '0016k' : 6,
  '0032k' : 7,
  '0064k' : 8,
  '0128k' : 9,
  '0256k' : 10,
  '0512k' : 11,
  '1024k' : 12,
  '2048k' : 13,
  '4096k' : 14
}

zones = []

def get_node_zones():
    """Return all zones metrics"""

    try:
	file = open(buddyinfo_file, 'r')

    except IOError:
	return 0

    # convert to dict
    metrics = {}
    for line in file:
	metrics = re.split("\s+", line)
	node_id = metrics[1].replace(',','')
	zone = metrics[3].lower()
	zones.append("node" + node_id + "_" + zone)


def get_metrics():
    """Return all metrics"""

    global METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

	try:
	    file = open(buddyinfo_file, 'r')
    
	except IOError:
	    return 0

        # convert to dict
        metrics = {}
	values = {}
        for line in file:
            metrics = re.split("\s+", line)
	    node_id = metrics[1].replace(',','')
	    zone = metrics[3].lower()
	    for item in stats_pos:
		pos = stats_pos[item]
		metric_name = "node" + node_id + "_" + zone + "_" + item
		values[metric_name] = metrics[pos]
		

	file.close
        # update cache
        LAST_METRICS = copy.deepcopy(METRICS)
        METRICS = {
            'time': time.time(),
            'data': values
        }
	
    return [METRICS]


def get_value(name):
    """Return a value for the requested metric"""

    metrics = get_metrics()[0]

    prefix_length = len(NAME_PREFIX) + 1
    name = name[prefix_length:] # remove prefix from name
    try:
        result = metrics['data'][name]
    except StandardError:
        result = 0

    return result


def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_init(params):
    global descriptors, metric_map, Desc_Skel

    descriptors = []

    get_node_zones()

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_value,
        'time_max'    : 60,
        'value_type'  : 'uint',
        'format'      : '%d',
        'units'       : 'segments',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'mem_fragmentation',
        }

    for zone in zones:
	for item in stats_pos:
	    descriptors.append(create_desc(Desc_Skel, {
		    "name"       : NAME_PREFIX + "_" + zone + "_" + item,
		    "description": item,
		    }))

    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    descriptors = metric_init(PARAMS)
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print '%s = %s' % (d['name'],  v)
        print 'Sleeping 15 seconds'
        time.sleep(15)
