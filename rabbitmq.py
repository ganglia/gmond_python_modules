#!/usr/bin/python
from subprocess import Popen, PIPE
import simplejson as json
import urllib
import time
from String import Template

global url, descriptors, last_update, vhost, username, password, url_template, result, result_dict, keyToPath
INTERVAL = 20
descriptors = list()
username, password = "guest", "guest"
GMETRIC="/usr/bin/gmetric"
RABBITMQCTL="/usr/sbin/rabbitmqctl"
stats = {}
last_update = {}
compiled_results = {}
#Make initial stat test time dict
for stat_type in ('queues', 'connections','exchanges', 'nodes'):
    last_update[stat_type] = time.time()

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

def dig_it_up(obj,path):
    try:
        if type(path) in (str,unicode):
            path = path.split('.')
        return reduce(lambda x,y:x[y],path,obj)
    except:
        return False

def refreshGroup(group):


    urlstring = url_template.safe_substitute(stat = group)

    global last_update, url, compiled_results

    now = time.time()
    diff = now - last_update[group]
    
    if diff > INTERVAL:
        print "Fetching stats after %d seconds" % INTERVAL
        result = json.load(urllib.urlopen(urlstring))
	compiled_results[group] = result
        last_update[group] = now
	#Refresh dict by names. We'll probably move this elsewhere.
        if group in (queues, nodes):
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
    queues = [queue["name"] for queue in results]
    return queues

def list_nodes():
    results = refreshGroup('nodes')
    nodes = [node['name'] for node in results]
    return nodes

def getQueueStat(name):
    #Split a name like "rmq_backing_queue_ack_egress_rate-access"
    stat_name, queue_name = name.split("-")

    result = refreshGroup('queues')
    
    value = dig_it_up(result, keyToPath[stat_name] % queue_name)
    print value

    #Convert Booleans
    if value is True:
        value = 1
    elif value is False:
        value = 0

    return value
    
def metric_init(params):
    ''' Create the metric definition object '''
    global descriptors, params, stats, vhost, username, password, urlstring
    print 'received the following params:'

    #Set this globally so we can refresh stats
    vhost = params['vhost']
    stats = get_vhost_stats(params['vhost'])
    username, password = params['username'], params['password']

    url = 'http://%s:%s@localhost:55672/api/$stats' % (username, password)
    url_template = Template(url)

    for queue in list_queues():
        for metric in QUEUE_METRICS:
	    d1 = {'name': "%s-%s" % (metric, queue),
		'call_back': getQueueStat,
		'units': 'N',
		'slope': 'both',
		'format': '%d',
		'description': 'Queue_Metric'}
	    
	    descriptors.append(d1)

    for node in list_nodes():
        for stat in NODE_METRICS:
	    d1 = {'name': '%s-%s' % (stat, node),
		'call_back': get_messages_ready,
		'units': 'N',
		'slope': 'both',
		'format': '%d',
		'description': 'Get Messages Ready in Queue'}
		
	    descriptors.append(d1)

    for d in descriptors:
        print d

    return descriptors
	


def get_vhost_stats(vhost, qtypes):
    data = {}
    VALID_TYPES = ['messages_ready', 'messages_unacknowledged']
    qtypes = [t for t in qtypes if t in VALID_TYPES]
    cmd = [RABBITMQCTL,
           'list_queues',
           '-p', vhost, 'name']
    cmd.extend(qtypes)
    stdout, stderr = Popen(cmd, stdout=PIPE, stderr=PIPE).communicate()
    for l in stdout.split("\n")[1:-2]:
        l = l.split()
        name = l.pop(0)
        data[name] = {}
        for i, t in enumerate(qtypes):
            data[name][t] = int(l[i])
    print data
    return data

if __name__ == "__main__":
    params = {"vhost":"/", "username":"guest","password":"guest"}
    metric_init(params)

