import sys
import re
import time
import copy
import string
import subprocess

METRICS = {
    'time' : 0,
    'data' : {}
}

METRICS_CACHE_MAX = 5

stats_pos = {} 

def get_metrics():
    """Return all metrics"""

    global METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

	new_metrics = {}
	units = {}

	command = [ params['timeout_bin'] , "3", params['ipmitool_bin'] , "-H", params['ipmi_ip'] , "-U" , params['username'] , '-P', params['password'] , 'sensor']	

        p = subprocess.Popen(command,
                             stdout=subprocess.PIPE).communicate()[0][:-1]

        for i, v in enumerate(p.split("\n")):
            data = v.split("|")
            try:
                metric_name = data[0].strip().lower().replace("+", "").replace(" ", "_")
                value = data[1].strip()

                # Skip missing sensors
                if re.search("(0x)", value ) or value == 'na':
                    continue

                # Extract out a float value
                vmatch = re.search("([0-9.]+)", value)
                if not vmatch:
                    continue
                metric_value = float(vmatch.group(1))

                new_metrics[metric_name] = metric_value
                units[metric_name] = data[2].strip().replace("degrees C", "C")
		
            except ValueError:
                continue
            except IndexError:
                continue
		
	METRICS = {
            'time': time.time(),
            'data': new_metrics,
            'units': units
        }

    return [METRICS]


def get_value(name):
    """Return a value for the requested metric"""

    try:

	metrics = get_metrics()[0]

	prefix_length = len(params['metric_prefix']) + 1
	name = name[prefix_length:] # remove prefix from name

	result = metrics['data'][name]

    except Exception:
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

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_value,
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%.5f',
        'units'       : 'count/s',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'XXX',
        }

    metrics = get_metrics()[0]
    
    for item in metrics['data']:
	descriptors.append(create_desc(Desc_Skel, {
		"name"       	: params['metric_prefix'] + "_" + item,
		'groups'	: params['metric_prefix'],
		'units'		: metrics['units'][item]
		}))


    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    
    params = {
        "metric_prefix" : "ipmi",
	"ipmi_ip" : "10.1.2.3",
	"username"  : "ADMIN",
	"password"  : "secret"
	}
    descriptors = metric_init(params)

    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print '%s = %s' % (d['name'],  v)
        print 'Sleeping 15 seconds'
        time.sleep(15)
