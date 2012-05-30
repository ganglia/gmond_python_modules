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
GMETRIC="/usr/bin/gmetric"
RABBITMQCTL="/usr/sbin/rabbitmqctl"
stats = {}
last_update = {}
compiled_results = {"nodes" : None, "queues" : None, "connections" : None}
#Make initial stat test time dict
for stat_type in ('queues', 'connections','exchanges', 'nodes'):
    last_update[stat_type] = None

keyToPath = {}


def create_desc(prop):
    d = Desc_Skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

# QUEUE METRICS #
keyToPath['rmq_messages_ready'] = "%s.messages_ready"
keyToPath['rmq_messages_unacknowledged'] = "%s.messages_unacknowledged"
keyToPath['rmq_backing_queue_ack_egress_rate'] = "%s.backing_queue_status.avg_ack_egress_rate"
keyToPath['rmq_backing_queue_ack_ingress_rate'] = "%s.backing_queue_status.avg_ack_ingress_rate" 
keyToPath['rmq_backing_queue_egress_rate'] = "%s.backing_queue_status.avg_egress_rate"
keyToPath['rmq_backing_queue_ingress_rate'] = "%s.backing_queue_status.avg_ingress_rate"
keyToPath['rmq_backing_queue_mirror_senders'] = "%s.backing_queue_status.mirror_senders"
keyToPath['rmq_memory'] = "%s.memory"

QUEUE_METRICS = ['rmq_messages_ready',
		'rmq_messages_unacknowledged',
		'rmq_backing_queue_ack_egress_rate',
		'rmq_backing_queue_ack_ingress_rate',
		'rmq_backing_queue_egress_rate',
		'rmq_backing_queue_ingress_rate',
		'rmq_backing_queue_mirror_senders',
		'rmq_memory']

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
        if type(path) in (str,unicode):
            path = path.split('.')
        return reduce(lambda x,y:x[y],path,obj)
    except:
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
    #Split a name like "rmq_backing_queue_ack_egress_rate-access"
    stat_name, queue_name = name.split(".")

    result = refreshGroup('queues')
    
    value = dig_it_up(result, keyToPath[stat_name] % queue_name)

    #Convert Booleans
    if value is True:
        value = 1
    elif value is False:
        value = 0

    return value

def getNodeStat(name):
    #Split a name like "rmq_backing_queue_ack_egress_rate-access"
    print name
    stat_name, node_name = name.split(".")

    result = refreshGroup('nodes')
   
    print stat_name, node_name, keyToPath[stat_name]
    value = dig_it_up(result, keyToPath[stat_name] % node_name)

    #Convert Booleans
    if value is True:
        value = 1
    elif value is False:
        value = 0

    return value
    
def metric_init(params):
    ''' Create the metric definition object '''
    global descriptors, stats, vhost, username, password, urlstring, url_template, compiled_results, Desc_Skel
    print 'received the following params:'
    #Set this globally so we can refresh stats
    vhost = params['vhost']
    username, password = params['username'], params['password']

    url = 'http://%s:%s@localhost:55672/api/$stats' % (username, password)
    url_template = Template(url)
    print params

    refreshGroup("nodes")
    refreshGroup("queues")
    print compiled_results['nodes'].keys()


    Desc_Skel = {
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

    def buildTestNodeStat():
	d = create_desc({
	'name' : u'rmq_disk_free.rmqone'.encode('ascii','ignore'),
	'call_back' : getNodeStat,
	'units': 'N',
	'slope': 'both',
	'format': '%d',	
	'groups' : 'rabbitmq',
        'description' : 'test'})
       
	descriptors.append(d)

    def buildQueueDescriptors():
	for queue in list_queues():
	    for metric in QUEUE_METRICS:
		name = "%s.%s" % (metric, queue)
		print name
		d1 = create_desc({'name': name.encode('ascii','ignore'),
		    'call_back': getQueueStat,
		    'units': 'N',
		    'slope': 'both',
		    'format': '%d',
		    'description': 'Queue_Metric',
		    'groups' : 'rabbitmq,queue'})
		
		descriptors.append(d1)
    
    def buildNodeDescriptors():
	for node in list_nodes():
	    node = node.split('@')[0]
	    for stat in NODE_METRICS:
		name = '%s.%s' % (stat, node)
		print name
		d2 = create_desc({'name': name.encode('ascii','ignore'),
		    'call_back': getNodeStat,
		    'units': 'N',
		    'slope': 'both',
		    'format': '%d',
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
    parameters = {"vhost":"/", "username":"guest","password":"guest", "metric_group":"rabbitmq"}
    descriptors = metric_init(parameters)
    for d1 in descriptors:
	print d1['name']
	print d1['call_back'](d1['name'])
    

