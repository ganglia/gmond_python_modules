import sys
import traceback
import os
import re
import time
import copy
import urllib2

METRICS = {
    'time' : 0,
    'data' : {}
}

LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_MAX = 5

NAME_PREFIX="filechecks_"

###############################################################################
# Misc file checks
###############################################################################
def get_is_file_present(name):
    """Find whether file exists"""

    global NAME_PREFIX

    name = name.replace(NAME_PREFIX,"") # remove prefix from name
    
    filename = "/" + name.replace("_present","").replace("_","/")
    
    if os.path.isfile(filename):
	return 1
    else:
	return 0


def get_file_size(name):

    global NAME_PREFIX

    name = name.replace(NAME_PREFIX,"") # remove prefix from name

    filename = "/" + name.replace("_size","").replace("_","/")

    try:
        return os.stat(filename).st_size
    except OSError:
        return 0

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_init(params):
    global descriptors, metric_map, Desc_Skel, NAME_PREFIX

    descriptors = []

    Desc_Skel = {
        'name'        : 'XXX',
        'orig_name'   : 'XXX',
        'call_back'   : get_is_file_present,
        'time_max'    : 60,
        'value_type'  : 'uint',
        'format'      : '%d',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : '',
	'units'	      : 'boolean',
        'groups'      : 'file_checks',
        }


    descriptors.append(create_desc(Desc_Skel, {
	"name"       : NAME_PREFIX + "etc_chef_disabled_present",
	"call_back"   : get_is_file_present,
	"description" : "/etc/chef/disabled present"
    }))

    descriptors.append(create_desc(Desc_Skel, {
	  "name"       : NAME_PREFIX + "var_log_syslog_size",
	  "call_back"   : get_file_size,
	  "units"       : "bytes",
	  "value_type"  : "float",
	  "description" : "Size of /var/log/syslog"
      }))


    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    metric_init({})
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print '%s = %s' % (d['name'],  v)
        print 'Sleeping 5 seconds'
        time.sleep(5)
