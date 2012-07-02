#!/usr/bin/python2.4
import sys
import os
import simplejson as json
import urllib
import time
from string import Template

global url, descriptors, last_update, vhost, username, password, url_template, result, result_dict, keyToPath
INTERVAL = 20
descriptors = list()
username, password = "guest", "guest"
stats = {}
last_update = {}
compiled_results = {"nodes" : None, "queues" : None, "connections" : None}
#Make initial stat test time dict
for stat_type in ('queues', 'connections','exchanges', 'nodes'):
    last_update[stat_type] = None

keyToPath = {}


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

def refreshGroup(group):
  

    global url_template
    urlstring = url_template.safe_substitute(stats = group)

    global last_update, url, compiled_results

    now = time.time()
    if not last_update[group]:
        diff = INTERVAL
    else:
    	diff = now - last_update[group]
    
    if diff >= INTERVAL or not last_update[group]:
        result_dict = {}
        print "Fetching stats after %d seconds" % INTERVAL
        result = json.load(urllib.urlopen(urlstring))
	compiled_results[group] = result
        last_update[group] = now
	#Refresh dict by names. We'll probably move this elsewhere.
        if group in ('queues', 'nodes'):
	    for entry in result:
		name_attribute = entry['name']
		result_dict[name_attribute] = entry
	    compiled_results[group] = result_dict
	
    return compiled_results[group]

def getConnectionTotal(name):
    result = refreshGroup('connections')
    return result.length()

def getConnectionStats(name):
    pass

def validatedResult(value):
    if not isInstance(value, bool):
        return float(value)
    else:
        return None

def list_queues():
    # Make a list of queues
    results = refreshGroup('queues')
    return results.keys()

def list_nodes():
    results = refreshGroup('nodes')
    return results.keys()

def getQueueStat(name):
    #Split a name like "rmq_backing_queue_ack_egress_rate.access"
    
    #handle queue names with . in them
    split_name = name.split(".")
    stat_name = split_name[0]
    queue_name = ".".join(split_name[1:])
    
    result = refreshGroup('queues')
    
    value = dig_it_up(result, keyToPath[stat_name] % queue_name)
    print name, value

    #Convert Booleans
    if value is True:
        value = 1
    elif value is False:
        value = 0

    return float(value)

def getNodeStat(name):
    #Split a name like "rmq_backing_queue_ack_egress_rate.access"
    stat_name, node_name = name.split(".") 
    result = refreshGroup('nodes')
    value = dig_it_up(result, keyToPath[stat_name] % node_name)
    print name,value
    #Convert Booleans
    if value is True:
        value = 1
    elif value is False:
        value = 0

    return float(value)
    
def metric_init(params):
    ''' Create the metric definition object '''
    global descriptors, stats, vhost, username, password, urlstring, url_template, compiled_results
    print 'received the following params:'
    #Set this globally so we can refresh stats
    if 'host' not in params:
        params['host'], params['vhost'],params['username'],params['password'] = "localhost", "/", "guest", "guest"
    vhost = params['vhost']
    username, password = params['username'], params['password']
    host = params['host']

    url = 'http://%s:%s@%s:55672/api/$stats' % (username, password, host)
    url_template = Template(url)
    print params

    refreshGroup("nodes")
    refreshGroup("queues")

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
	for queue in list_queues():
	    for metric in QUEUE_METRICS:
		name = "%s.%s" % (metric, queue)
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
	for node in list_nodes():
	    #node = node.split('@')[0]
	    for stat in NODE_METRICS:
		name = '%s.%s' % (stat, node)
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
    url = 'http://%s:%s@localhost:55672/api/$stats' % (username, password)
    url_template = Template(url)
    parameters = {"vhost":"/", "username":"guest","password":"guest", "metric_group":"rabbitmq"}
    metric_init(parameters)
    result = refreshGroup('queues')
    node_result = refreshGroup('nodes')
    print '***'*10
    getQueueStat('rmq_backing_queue_ack_egress_rate.gelf_client_three')
    getNodeStat('rmq_disk_free.rmqtwo@inrmq02d1') 
    getNodeStat('rmq_mem_used.rmqtwo@inrmq02d1')
