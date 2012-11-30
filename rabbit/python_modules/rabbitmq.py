#!/usr/bin/python2.4
import sys
import os
import simplejson as json
import urllib2
import time
from string import Template
import itertools
import threading

global url, descriptors, last_update, vhost, username, password, url_template, result, result_dict, keyToPath 
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
keyToPath['rmq_messages_ready'] = "%s.messages_ready"
keyToPath['rmq_messages_unacknowledged'] = "%s.messages_unacknowledged"
keyToPath['rmq_backing_queue_ack_egress_rate'] = "%s.backing_queue_status.avg_ack_egress_rate"
keyToPath['rmq_backing_queue_ack_ingress_rate'] = "%s.backing_queue_status.avg_ack_ingress_rate" 
keyToPath['rmq_backing_queue_egress_rate'] = "%s.backing_queue_status.avg_egress_rate"
keyToPath['rmq_backing_queue_ingress_rate'] = "%s.backing_queue_status.avg_ingress_rate"
keyToPath['rmq_backing_queue_mirror_senders'] = "%s.backing_queue_status.mirror_senders"
keyToPath['rmq_memory'] = "%s.memory"
keyToPath['rmq_consumers'] = "%s.consumers"
keyToPath['rmq_messages'] = "%s.messages"

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
keyToPath['rmq_disk_free'] = "%s.disk_free"
keyToPath['rmq_disk_free_alarm'] = "%s.disk_free_alarm"
keyToPath['rmq_fd_used'] = "%s.fd_used"
keyToPath['rmq_fd_used'] = "%s.fd_used"
keyToPath['rmq_mem_used'] = "%s.mem_used"
keyToPath['rmq_proc_used'] = "%s.proc_used"
keyToPath['rmq_sockets_used'] = "%s.sockets_used"
keyToPath['rmq_mem_alarm'] = "%s.mem_alarm" #Boolean
keyToPath['rmq_mem_binary'] = "%s.mem_binary"
keyToPath['rmq_mem_code'] = "%s.mem_code"
keyToPath['rmq_mem_proc_used'] = "%s.mem_proc_used"
keyToPath['rmq_running'] = "%s.running" #Boolean

NODE_METRICS = ['rmq_disk_free', 'rmq_mem_used', 'rmq_disk_free_alarm', 'rmq_running', 'rmq_proc_used', 'rmq_mem_proc_used', 'rmq_fd_used', 'rmq_mem_alarm', 'rmq_mem_code', 'rmq_mem_binary', 'rmq_sockets_used']
	



def metric_cleanup():
    pass

def dig_it_up(obj,path):
    try:
	path = path.split('.')
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
    split_name, vhost = name.split("#")
    split_name = split_name.split(".")
    stat_name = split_name[0]
    queue_name = ".".join(split_name[1:])
    
    # Run refreshStats to get the result object
    result = compiled_results[('queues', vhost)]
    
    value = dig_it_up(result, keyToPath[stat_name] % queue_name)
    print name, value

    #Convert Booleans
    if value is True:
        value = 1
    elif value is False:
        value = 0

    return float(value)

def getNodeStat(name):
    refreshStats(stats = STATS, vhosts = vhosts)
    #Split a name like "rmq_backing_queue_ack_egress_rate.access"
    stat_name = name.split(".")[0]
    node_name, vhost = name.split(".")[1].split("#")
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
    
def metric_init(params):
    ''' Create the metric definition object '''
    global descriptors, stats, vhost, username, password, urlstring, url_template, compiled_results, STATS, vhosts
    print 'received the following params:'
    #Set this globally so we can refresh stats
    if 'host' not in params:
        params['host'], params['vhost'],params['username'],params['password'],params['port'] = "localhost", "/", "guest", "guest", "15672"

    # Set the vhosts as a list split from params
    vhosts = params['vhost'].split(',')
    username, password = params['username'], params['password']
    host = params['host']
    port = params['port']
    
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
                name = "%s.%s#%s" % (metric, queue, vhost)   
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
		name = '%s.%s#%s' % (metric, node, '/')
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
    parameters = {"vhost":"/", "username":"guest","password":"guest", "metric_group":"rabbitmq"}
    metric_init(parameters)
    result = refreshStats(stats = ('queues', 'nodes'), vhosts = ('/'))
    print '***'*10
    getQueueStat('rmq_backing_queue_ack_egress_rate.nfl_client#/')
    getNodeStat('rmq_disk_free.rmqone@inrmq01d1#/') 
    getNodeStat('rmq_mem_used.rmqone@inrmq01d1#/')
