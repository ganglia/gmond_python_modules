#!/usr/bin/python2.4
import sys
import os
import json
import urllib2
import time
from string import Template
import itertools
import threading

global url, descriptors, last_update, vhost, username, password, url_template, result, result_dict, keyToPath


JSON_PATH_SEPARATOR = "?"
METRIC_TOKEN_SEPARATOR = "___"
 
INTERVAL = 10
descriptors = list()
username, password = "guest", "guest"
stats = {}
keyToPath = {}
last_update = None
#last_update = {}
compiled_results = {"nodes" : None, "queues" : None, "connections" : None}
#Make initial stat test time dict
#for stat_type in ('queues', 'connections','exchanges', 'nodes'):
#    last_update[stat_type] = None

### CONFIGURATION SECTION ###
STATS = ['nodes', 'queues']

# QUEUE METRICS #
keyToPath['rmq_messages_ready'] = "%s{0}messages_ready".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_messages_unacknowledged'] = "%s{0}messages_unacknowledged".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_backing_queue_ack_egress_rate'] = "%s{0}backing_queue_status{0}avg_ack_egress_rate".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_backing_queue_ack_ingress_rate'] = "%s{0}backing_queue_status{0}avg_ack_ingress_rate".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_backing_queue_egress_rate'] = "%s{0}backing_queue_status{0}avg_egress_rate".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_backing_queue_ingress_rate'] = "%s{0}backing_queue_status{0}avg_ingress_rate".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_backing_queue_mirror_senders'] = "%s{0}backing_queue_status{0}mirror_senders".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_memory'] = "%s{0}memory".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_consumers'] = "%s{0}consumers".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_messages'] = "%s{0}messages".format(JSON_PATH_SEPARATOR)

RATE_METRICS = [
    'rmq_backing_queue_ack_egress_rate',
    'rmq_backing_queue_ack_ingress_rate',
    'rmq_backing_queue_egress_rate',
    'rmq_backing_queue_ingress_rate'
]

QUEUE_METRICS = ['rmq_messages_ready',
		'rmq_messages_unacknowledged',
		'rmq_backing_queue_ack_egress_rate',
		'rmq_backing_queue_ack_ingress_rate',
		'rmq_backing_queue_egress_rate',
		'rmq_backing_queue_ingress_rate',
		'rmq_backing_queue_mirror_senders',
		'rmq_memory',
                'rmq_consumers',
		'rmq_messages']

# NODE METRICS #
keyToPath['rmq_disk_free'] = "%s{0}disk_free".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_disk_free_alarm'] = "%s{0}disk_free_alarm".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_fd_used'] = "%s{0}fd_used".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_fd_used'] = "%s{0}fd_used".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_mem_used'] = "%s{0}mem_used".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_proc_used'] = "%s{0}proc_used".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_sockets_used'] = "%s{0}sockets_used".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_mem_alarm'] = "%s{0}mem_alarm".format(JSON_PATH_SEPARATOR) #Boolean
keyToPath['rmq_mem_binary'] = "%s{0}mem_binary".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_mem_code'] = "%s{0}mem_code".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_mem_proc_used'] = "%s{0}mem_proc_used".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_running'] = "%s{0}running".format(JSON_PATH_SEPARATOR) #Boolean

NODE_METRICS = ['rmq_disk_free', 'rmq_mem_used', 'rmq_disk_free_alarm', 'rmq_running', 'rmq_proc_used', 'rmq_mem_proc_used', 'rmq_fd_used', 'rmq_mem_alarm', 'rmq_mem_code', 'rmq_mem_binary', 'rmq_sockets_used']
	



def metric_cleanup():
    pass

def dig_it_up(obj,path):
    try:
	path = path.split(JSON_PATH_SEPARATOR)
        return reduce(lambda x,y:x[y],path,obj)
    except:
        print "Exception"
        return False

def refreshStats(stats = ('nodes', 'queues'), vhosts = ['/']):

    global url_template
    global last_update, url, compiled_results

    now = time.time()

    if not last_update:
        diff = INTERVAL
    else:
        diff = now - last_update

    if diff >= INTERVAL or not last_update:
	print "Fetching Results after %d seconds" % INTERVAL
	last_update = now
        for stat in stats:
            for vhost in vhosts:
                if stat in ('nodes'):
                    vhost = '/'
		result_dict = {}
                urlstring = url_template.safe_substitute(stats = stat, vhost = vhost)
                print urlstring
                result = json.load(urllib2.urlopen(urlstring))
		# Rearrange results so entry is held in a dict keyed by name - queue name, host name, etc.
		if stat in ("queues", "nodes", "exchanges"):
		    for entry in result:
		        name = entry['name']
			result_dict[name] = entry
		    compiled_results[(stat, vhost)] = result_dict

    return compiled_results


def validatedResult(value):
    if not isInstance(value, bool):
        return float(value)
    else:
        return None

def list_queues(vhost):
    global compiled_results
    queues = compiled_results[('queues', vhost)].keys()
    return queues

def list_nodes():
    global compiled_results
    nodes = compiled_results[('nodes', '/')].keys()
    return nodes

def getQueueStat(name):
    refreshStats(stats = STATS, vhosts = vhosts)
    #Split a name like "rmq_backing_queue_ack_egress_rate.access"
    
    #handle queue names with . in them
    print name
    stat_name, queue_name, vhost = name.split(METRIC_TOKEN_SEPARATOR)
    
    vhost = vhost.replace('-', '/') #decoding vhost from metric name
    # Run refreshStats to get the result object
    result = compiled_results[('queues', vhost)]
    
    value = dig_it_up(result, keyToPath[stat_name] % queue_name)
    
    if zero_rates_when_idle and stat_name in RATE_METRICS  and 'idle_since' in result[queue_name].keys():
        value = 0

    #Convert Booleans
    if value is True:
        value = 1
    elif value is False:
        value = 0

    return float(value)

def getNodeStat(name):
    refreshStats(stats = STATS, vhosts = vhosts)
    #Split a name like "rmq_backing_queue_ack_egress_rate.access"
    stat_name, node_name, vhost = name.split(METRIC_TOKEN_SEPARATOR)
    vhost = vhost.replace('-', '/') #decoding vhost from metric name

    result = compiled_results[('nodes', '/')]
    value = dig_it_up(result, keyToPath[stat_name] % node_name)

    print name,value
    #Convert Booleans
    if value is True:
        value = 1
    elif value is False:
        value = 0

    return float(value)

def product(*args, **kwds):
    # replacement for itertools.product
    # product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
    pools = map(tuple, args) * kwds.get('repeat', 1)
    result = [[]]
    for pool in pools:
        result = [x+[y] for x in result for y in pool]
    for prod in result:
        yield tuple(prod)

def str2bool(string):
    if string.lower() in ("yes", "true"):
        return True
    if string.lower() in ("no", "false"):
        return False
    raise Exception("Invalid value of the 'zero_rates_when_idle' param, use one of the ('true', 'yes', 'false', 'no')")
    
def metric_init(params):
    ''' Create the metric definition object '''
    global descriptors, stats, vhost, username, password, urlstring, url_template, compiled_results, STATS, vhosts, zero_rates_when_idle
    print 'received the following params:'
    #Set this globally so we can refresh stats
    if 'host' not in params:
        params['host'], params['vhost'],params['username'],params['password'],params['port'] = "localhost", "/", "guest", "guest", "15672"
    if 'zero_rates_when_idle' not in params:
        params['zero_rates_when_idle'] = "false"

    # Set the vhosts as a list split from params
    vhosts = params['vhost'].split(',')
    username, password = params['username'], params['password']
    host = params['host']
    port = params['port']

    zero_rates_when_idle = str2bool(params['zero_rates_when_idle'])
    
    url = 'http://%s:%s/api/$stats/$vhost' % (host,port)
    base_url = 'http://%s:%s/api' % (host,port)
    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, base_url, username, password)
    handler = urllib2.HTTPBasicAuthHandler(password_mgr)
    opener = urllib2.build_opener(handler)
    opener.open(base_url)
    urllib2.install_opener(opener)
    url_template = Template(url)
    print params

    refreshStats(stats = STATS, vhosts = vhosts)

    def metric_handler(name):
        if 15 < time.time() - metric_handler.timestamp:
            metric_handler.timestamp = time.time()
            return refreshStats(stats = STATS, vhosts = vhosts)

            

    def create_desc(prop):
	d = {
	    'name'        : 'XXX',
	    'call_back'   : getQueueStat,
	    'time_max'    : 60,
	    'value_type'  : 'uint',
	    'units'       : 'units',
	    'slope'       : 'both',
	    'format'      : '%d',
	    'description' : 'XXX',
	    'groups'      : params["metric_group"],
	}

	for k,v in prop.iteritems():
	    d[k] = v
	return d


    def buildQueueDescriptors():
        for vhost, metric in product(vhosts, QUEUE_METRICS):
            queues = list_queues(vhost)
            for queue in queues:
                name = "{1}{0}{2}{0}{3}".format(METRIC_TOKEN_SEPARATOR, metric, queue, vhost.replace('/', '-'))
		print name
		d1 = create_desc({'name': name.encode('ascii','ignore'),
		    'call_back': getQueueStat,
                    'value_type': 'float',
		    'units': 'N',
		    'slope': 'both',
		    'format': '%f',
		    'description': 'Queue_Metric',
		    'groups' : 'rabbitmq,queue'})
		print d1
		descriptors.append(d1)
    
    def buildNodeDescriptors():
        for metric in NODE_METRICS:
            for node in list_nodes():
                name = "{1}{0}{2}{0}-".format(METRIC_TOKEN_SEPARATOR, metric, node)
                print name
                d2 = create_desc({'name': name.encode('ascii','ignore'),
		    'call_back': getNodeStat,
                    'value_type': 'float',
		    'units': 'N',
		    'slope': 'both',
		    'format': '%f',
		    'description': 'Node_Metric',
		    'groups' : 'rabbitmq,node'}) 
                print d2
                descriptors.append(d2)

    buildQueueDescriptors()
    buildNodeDescriptors()
    # buildTestNodeStat()
	
    return descriptors

def metric_cleanup():
    pass
  

if __name__ == "__main__":
    url = 'http://%s:%s@localhost:15672/api/$stats' % (username, password)
    url_template = Template(url)
    print "url_template is ", url_template
### in config files we use '/' in vhosts names but we should convert '/' to '-' when calculating a metric
    parameters = {"vhost":"/", "username":"guest","password":"guest", "metric_group":"rabbitmq", "zero_rates_when_idle": "yes"}
    metric_init(parameters)
    result = refreshStats(stats = ('queues', 'nodes'), vhosts = ('/'))
    print '***'*20
    getQueueStat('rmq_backing_queue_ack_egress_rate___nfl_client___-')
    getNodeStat('rmq_disk_free___rmqone@inrmq01d1___-')
    getNodeStat('rmq_mem_used___rmqone@inrmq01d1___-')
