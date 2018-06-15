import os
import sys
import re
import time
import copy
import string
import subprocess

METRICS = {
    'time' : 0,
    'data' : {},
    'units': {},
    'descr': {}
}

METRICS_CACHE_MAX = 5

stats_pos = {} 

# Try to make different vendors' sensor names at least somewhat consistent...
# This list is admittedly a bit Dell centric, as I have HP and Dell
# hardware and Dell's sensor names (mostly) make more sense to me than
# HP's...  --troy
unified_metric_names = {
    # Cisco
    "FP_TEMP_SENSOR": "Inlet Temp",
    # HP sensor names
    "01-Inlet Ambient": "Inlet Temp",
    "43-Sys Exhaust": "Exhaust Temp",
    "02-CPU 1": "CPU 1 Temp",
    "03-CPU 2": "CPU 2 Temp",
    "04-P1 DIMM 1-4": "CPU 1 MemBank 1 Temp",
    "05-P1 DIMM 5-8": "CPU 1 MemBank 2 Temp",
    "06-P2 DIMM 1-4": "CPU 2 MemBank 1 Temp",
    "07-P2 DIMM 5-8": "CPU 2 MemBank 2 Temp",
    "34-Coprocessor 1": "Coprocessor 1 Temp",
    "35-Coprocessor 2": "Coprocessor 2 Temp",
    "36-Coprocessor 3": "Coprocessor 3 Temp",
    "42-P/S Board": "Pwr Supply 1 Temp",
    "Power Meter": "Pwr Consumption",
    "Temp 1": "Inlet Temp",
    "Temp 2 (CPU 1)": "CPU 1 Temp",
    "Temp 3 (CPU 2)": "CPU 2 Temp",
    "Temp 4 (MemD1)": "CPU 1 MemBank 1 Temp",
    "Temp 5 (MemD2)": "CPU 2 MemBank 1 Temp",
    "Temp 16 (GPU2)": "Coprocessor 2 Temp",
    "Temp 17 (GPU3)": "Coprocessor 3 Temp",
    "Temp 18 (GPU1)": "Coprocessor 1 Temp",
    # Dell sensor names
    "Ambient Temp": "Inlet Temp",
    "Fan1": "Fan 1",
    "Fan2": "Fan 2",
    "Fan3": "Fan 3",
    "Fan4": "Fan 4",
    "Fan5": "Fan 5",
    "Fan6": "Fan 6",
    "Fan7": "Fan 7",
    "Fan8": "Fan 8",
    "Fan1A": "Fan 1A",
    "Fan1B": "Fan 1B",
    "Fan2A": "Fan 2A",
    "Fan2B": "Fan 2B",
    "Fan3A": "Fan 3A",
    "Fan3B": "Fan 3B",
    "Fan4A": "Fan 4A",
    "Fan4B": "Fan 4B",
    "Fan5A": "Fan 5A",
    "Fan5B": "Fan 5B",
    "Fan6A": "Fan 6A",
    "Fan6B": "Fan 6B",
    "Fan7A": "Fan 7A",
    "Fan7B": "Fan 7B",
    "Fan8A": "Fan 8A",
    "Fan8B": "Fan 8B",
    # Intel(?) sensor names
    "Front Panel Temp": "Inlet Temp",
    "Exit Air Temp": "Exhaust Temp",
    "System Fan 1": "Fan 1",
    "System Fan 2": "Fan 2",
    "Processor 1 Fan": "Fan 3",
    "Processor 2 Fan": "Fan 4",
    "PS1 Temperature": "Pwr Supply 1 Temp",
    "PS2 Temperature": "Pwr Supply 2 Temp",
    # Sun
    "VRD 0 Temp": "Inlet Temp",
    "MB/T_VRD0": "Inlet Temp",
    "MB/T_AMB0": "Inlet Temp",
    "/MB/T_AMB": "Inlet Temp",
    # Supermicro
    "Air Temp": "Inlet Temp",
    "System Temp" : "Inlet Temp"
}
def mangle_metric_name(metric_name,prefix):
    name = metric_name
    if ( metric_name.strip() in unified_metric_names.keys() ):
        name = unified_metric_names[metric_name.strip()]
    return prefix+"_"+name.strip().lower().replace("+","").replace(" ","_").replace("-","_")
def metric_description(metric_name):
    if ( metric_name.strip() in unified_metric_names.keys() ):
        return unified_metric_names[metric_name.strip()]
    else:
        return metric_name.strip()

def c_to_f(temp):
  return (temp * 9.0/5.0) + 32.0

def get_metrics():
    """Return all metrics"""

    global METRICS

    params = global_params

    # bail out if no ipmi ip address is set and there are no
    # ipmi device files available (i.e. ipmitool is guaranteed
    # to fail
    if ( 'ipmi_ip' not in params.keys() and
         not os.path.exists('/dev/ipmi0') and
         not os.path.exists('/dev/ipmi/0') and
         not os.path.exists('/dev/ipmidev/0') ):
            pass
    # otherwise, run ipmitool if we're outside the cache timeout
    elif (time.time() - METRICS['time']) > METRICS_CACHE_MAX:
        new_metrics = {}
        units = {}
        descr = {}

        command = [ params['timeout_bin'], str(params['timeout']) ]
        if ( 'use_sudo' in params.keys() and params['use_sudo'] ):
            command.append('sudo')
        command.append(params['ipmitool_bin'])
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
                    description = "CPU "+str(dell_temp_count)+" Temp"
                    metric_name = mangle_metric_name(description,params['metric_prefix'])
                    dell_temp_count = dell_temp_count+1
                else:
                    description = metric_description(data[0])
                    metric_name = mangle_metric_name(data[0],params['metric_prefix'])
                value = data[1].strip()

                # Skip missing sensors
                if re.search("(0x)", value ) or value == 'na':
                    continue

                # Extract out a float value
                vmatch = re.search("([0-9.]+)", value)
                if not vmatch:
                    continue
                metric_value = float(vmatch.group(1))
                if data[2].strip() == "degrees C":
                  if 'use_fahrenheit' in params.keys() and params['use_fahrenheit']:
                    metric_value = c_to_f(metric_value)
                    units[metric_name] = "F"
                  else:
                    units[metric_name] = "C"
                else:
                  units[metric_name] = data[2].strip()

                new_metrics[metric_name] = metric_value
                descr[metric_name] = description
                
            except ValueError:
                continue
            except IndexError:
                continue
                
        METRICS = {
            'time': time.time(),
            'data': new_metrics,
            'units': units,
            'descr': descr
        }

    return [METRICS]


def get_value(name):
    """Return a value for the requested metric"""

    try:
        
        metrics = get_metrics()[0]

        if ( name in metrics['data'].keys() ):
            result = metrics['data'][name]
        else:
            result = 0

    except Exception as e:
        result = 0

    return result

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_init(params):
    global descriptors, metric_map, Desc_Skel, global_params

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

    global_params = params

    metrics = get_metrics()[0]
    
    for item in metrics['data']:
        descriptors.append(create_desc(Desc_Skel, {
                'name'          : item,
                'description'   : metrics['descr'][item],
                'groups'        : params['metric_prefix'],
                'units'         : metrics['units'][item]
                }))


    return descriptors


def metric_cleanup():
    '''Clean up the metric module.'''
    pass


#This code is for debugging and unit testing
if __name__ == '__main__':
    
    params = {
        "use_sudo" : False,
        "use_fahrenheit" : False,
        "metric_prefix" : "ipmi",
        #"ipmi_ip" : "10.1.2.3",
        #"username"  : "ADMIN",
        #"password"  : "secret",
        #"level" : "USER",
        "timeout" : 15,
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
