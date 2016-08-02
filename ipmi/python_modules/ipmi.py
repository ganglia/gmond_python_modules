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

# Try to make different vendors' sensor names at least somewhat consistent...
# This list is admittedly a bit Dell centric, as I have HP and Dell
# hardware and Dell's sensor names (mostly) make more sense to me than
# HP's...  --troy
unified_metric_names = {
    # HP sensor names
    "01-Inlet Ambient": "Inlet Temp",
    "43-Sys Exhaust": "Exhaust Temp",
    "02-CPU 1": "CPU 1 Temp",
    "03-CPU 2": "CPU 2 Temp",
    "04-P1 DIMM 1-4":  "CPU 1 MemBank 1 Temp",
    "05-P1 DIMM 5-8":  "CPU 1 MemBank 2 Temp",
    "06-P2 DIMM 1-4":  "CPU 2 MemBank 1 Temp",
    "07-P2 DIMM 5-8":  "CPU 2 MemBank 2 Temp",
    "34-Coprocessor 1": "Coprocessor 1 Temp",
    "35-Coprocessor 2": "Coprocessor 2 Temp",
    "36-Coprocessor 3": "Coprocessor 3 Temp",
    "42-P/S Board": "Pwr Supply Temp",
    "Power Meter": "Pwr Consumption",
    # Dell sensor names
    "Fan1": "Fan 1",
    "Fan2": "Fan 2",
    "Fan3": "Fan 3",
    "Fan4": "Fan 4",
    "Fan5": "Fan 5",
    "Fan6": "Fan 6"
}
def mangle_metric_name(metric_name):
    name = metric_name
    if ( metric_name.strip() in unified_metric_names.keys() ):
        name = unified_metric_names[metric_name.strip()]
    return name.strip().lower().replace("+","").replace(" ","_").replace("-","_")

def get_metrics(params):
    """Return all metrics"""

    global METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

	new_metrics = {}
	units = {}

	command = [ params['timeout_bin'],
	"3", params['ipmitool_bin']]
        if ( 'use_sudo' in params.keys() and params['use_sudo'] ):
            command.insert(0,'sudo')
        if ( 'ipmi_ip' in params.keys() ):
            command.append("-H")
            command.append(params['ipmi_ip'])
        if ( 'username' in params.keys() ):
            command.append("-U")
            command.append(params['username'])
        if ( 'password' in params.keys() ):
            command.append('-P')
            command.append(params['password'])
	if ('level' in params.keys() ):
            command.append('-L')
            command.append(params['level'])
	command.append('sensor')

        p = subprocess.Popen(command,
                             stdout=subprocess.PIPE).communicate()[0][:-1]

        dell_temp_count = 1
        for i, v in enumerate(p.split("\n")):
            data = v.split("|")
            try:
                if ( data[0].strip()=="Temp" ):
                    # Dell names all CPU temperature sensors "Temp";
                    # thus, the following stupidity:
                    tempname = "CPU "+str(dell_temp_count)+" Temp"
                    metric_name = mangle_metric_name(tempname)
                    dell_temp_count = dell_temp_count+1
                else:
                    metric_name = mangle_metric_name(data[0])
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

	name = name.lstrip('ipmi_')

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

    metrics = get_metrics(params)[0]
    
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
        "use_sudo" : False,
	"metric_prefix" : "ipmi",
	#"ipmi_ip" : "10.1.2.3",
	#"username"  : "ADMIN",
	#"password"  : "secret",
	#"level" : "USER",
	"ipmitool_bin" : "/usr/bin/ipmitool",
	"timeout_bin" : "/usr/bin/timeout"
	}
    descriptors = metric_init(params)

    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print '%s = %s' % (d['name'],  v)
        print 'Sleeping 15 seconds'
        time.sleep(15)
