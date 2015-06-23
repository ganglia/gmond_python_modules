#
# net_latency - A simple Ganglia module that
# measures network latency.
#
# Created by Giorgos Kappes <contact@giorgoskappes.com>
#
import subprocess
import os

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def measure_latency(name):
        try:
		target = "$(ip route show | grep default | awk '{ print $3 }')"
		command = "ping -c 5 "+target+" | tail -1| awk -F '/' '{print $5}'"
                f = os.popen(command)
                res = f.read()
		if is_number(res) == False:
			return 0
        except IOError:
                return 0

	return int(float(res) * 1000)

def metric_init(params):
	global descriptors
	
	d1 = {'name': 'net_latency',
		'call_back': measure_latency,
		'value_type': 'uint',
		'units': 'microseconds',
		'slope': 'both',
		'format': '%u',
		'description': 'Network Latency',
		'groups': 'network' }
	
	descriptors = [d1]
	return descriptors

def metric_cleanup():
	'''Clean up the metric module.'''
	pass
    
