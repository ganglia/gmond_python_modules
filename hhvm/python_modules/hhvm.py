#
# hhvm.py
#
# This script reports hhvm metrics to ganglia.
#
# This module parses output from the HHVM AdminServer memory and health commands
# and creates "hhvm_*" metrics
#
# Changelog:
#   v1.0.0 - 2015-01-15
#       * Initial version
#   v1.0.1 - 2015-02-10
#       * Added debug mode
#
# Copyright (c) 2015 Juan J. Villalobos <jj@debianized.net>
# License to use, modify, and distribute under the GPL
# http://www.gnu.org/licenses/gpl-3.0.txt
#

import urllib2
import logging
import json
import xml.etree.ElementTree as ET


logging.basicConfig(level=logging.ERROR,
                    format="%(asctime)s - hhvm - %(levelname)s - %(message)s")
logging.debug('starting')

descriptors = list()

name_map = {}

name_map['hhvm_mem_procstats_vmsize'] = \
    '__Memory_Process Stats (bytes)_VmSize'
name_map['hhvm_mem_procstats_vmrss'] = \
    '__Memory_Process Stats (bytes)_VmRss'
name_map['hhvm_mem_procstats_shared'] = \
    '__Memory_Process Stats (bytes)_Shared'
name_map['hhvm_mem_procstats_code'] = \
    '__Memory_Process Stats (bytes)_Text(Code)'
name_map['hhvm_mem_procstats_data'] = \
    '__Memory_Process Stats (bytes)_Data'

name_map['hhvm_mem_breakdown_static_strings_bytes'] = \
    '__Memory_Breakdown_Static Strings_Bytes'
name_map['hhvm_mem_breakdown_static_strings_count'] = \
    '__Memory_Breakdown_Static Strings_Details_Count'
name_map['hhvm_mem_breakdown_code_bytes'] =\
    '__Memory_Breakdown_Code_Details_Bytes'
name_map['hhvm_mem_breakdown_tcjit_bytes'] = \
    '__Memory_Breakdown_TC/Jit_Bytes'
name_map['hhvm_mem_breakdown_tcjit_code_cold_capacity'] = \
    '__Memory_Breakdown_TC/Jit_Details_code.cold_Capacity'
name_map['hhvm_mem_breakdown_tcjit_code_cold_used'] = \
    '__Memory_Breakdown_TC/Jit_Details_code.cold_Used'
name_map['hhvm_mem_breakdown_tcjit_code_frozen_capacity'] = \
    '__Memory_Breakdown_TC/Jit_Details_code.frozen_Capacity'
name_map['hhvm_mem_breakdown_tcjit_code_frozen_used'] = \
    '__Memory_Breakdown_TC/Jit_Details_code.frozen_Used'
name_map['hhvm_mem_breakdown_tcjit_code_hot_capacity'] = \
    '__Memory_Breakdown_TC/Jit_Details_code.hot_Capacity'
name_map['hhvm_mem_breakdown_tcjit_code_hot_used'] = \
    '__Memory_Breakdown_TC/Jit_Details_code.hot_Used'
name_map['hhvm_mem_breakdown_tcjit_code_main_capacity'] = \
    '__Memory_Breakdown_TC/Jit_Details_code.main_Capacity'
name_map['hhvm_mem_breakdown_tcjit_code_main_used'] = \
    '__Memory_Breakdown_TC/Jit_Details_code.main_Used'
name_map['hhvm_mem_breakdown_tcjit_code_prof_capacity'] = \
    '__Memory_Breakdown_TC/Jit_Details_code.prof_Capacity'
name_map['hhvm_mem_breakdown_tcjit_code_prof_used'] = \
    '__Memory_Breakdown_TC/Jit_Details_code.prof_Used'
name_map['hhvm_mem_breakdown_tcjit_data_capacity'] = \
    '__Memory_Breakdown_TC/Jit_Details_data_Capacity'
name_map['hhvm_mem_breakdown_tcjit_data_used'] = \
    '__Memory_Breakdown_TC/Jit_Details_data_Used'
name_map['hhvm_mem_breakdown_tcjit_total_capacity'] = \
    '__Memory_Breakdown_TC/Jit_Details_Total Capacity'
name_map['hhvm_mem_breakdown_tcjit_total_used'] = \
    '__Memory_Breakdown_TC/Jit_Details_Total Used'
name_map['hhvm_mem_breakdown_unknown'] = \
    '__Memory_Breakdown_Unknown'

name_map['hhvm_health_units'] = \
    '__units'
name_map['hhvm_health_funcs'] = \
    '__funcs'
name_map['hhvm_health_hhbc_roarena_capac'] = \
    '__hhbc-roarena-capac'
name_map['hhvm_health_load'] = \
    '__load'
name_map['hhvm_health_queued'] = \
    '__queued'
name_map['hhvm_health_rds'] = \
    '__rds'
name_map['hhvm_health_target_cache'] = \
    '__targetcache'

name_map['hhvm_jemalloc_low_allocated'] = \
    'hhvm_jemalloc_low_allocated'
name_map['hhvm_jemalloc_allocated'] = \
    'hhvm_jemalloc_allocated'
name_map['hhvm_jemalloc_mapped'] = \
    'hhvm_jemalloc_mapped'
name_map['hhvm_jemalloc_active'] = \
    'hhvm_jemalloc_active'
name_map['hhvm_jemalloc_low_mapped'] = \
    'hhvm_jemalloc_low_mapped'
name_map['hhvm_jemalloc_low_active'] = \
    'hhvm_jemalloc_low_active'
name_map['hhvm_jemalloc_error'] = \
    'hhvm_jemalloc_error'

url = ''
username = ''
password = ''


class MemoryData(object):
    ''' Object to store /memory-json endpoint result '''
    global url, password

    def __init__(self):
        self.url = url + '/memory.json?auth=' + password
        self.data = {}
        logging.debug('MemoryData object initialized pointing to ' + self.url)

    def get(self, name):
        try:
            logging.debug('MemoryData get method called')
            temp_data = json.load(fetch_url(self.url))
            self.data = flatten(temp_data)
            return int(self.data[name_map[name]])
        except:
            logging.error('MemoryData get method failed, '
                          'could not parse output data, retval=0')
            return 0


class HealthData(object):
    ''' Object to store /check-health endpoint result '''
    global url, password

    def __init__(self):
        self.url = url + '/check-health?auth=' + password
        self.data = {}
        logging.debug('HealthData object initialized pointing to ' + self.url)

    def get(self, name):
        try:
            logging.debug('HealthData get method called')
            temp_data = json.load(fetch_url(self.url))
            self.data = flatten(temp_data)
            return int(self.data[name_map[name]])
        except:
            logging.error('HealthData get method failed, '
                          'could not parse output data, retval=0')
            return 0


class JemallocData(object):
    ''' Object to store /jemalloc-stats endpoint result '''
    global url, password

    def __init__(self):
        self.url = url + '/jemalloc-stats?auth=' + password
        self.data = {}
        logging.debug('JemallocData object initialized pointing to ' + self.url)

    def get(self, name):
        try:
            logging.debug('JemallocData get method called')
            root = ET.parse(fetch_url(self.url)).getroot()
            for child in root:
                self.data['hhvm_jemalloc_' + child.tag] = child.text
            return int(self.data[name_map[name]])
        except:
            logging.error('JemallocData get method failed, '
                          'could not parse output data, retval=0')
            return 0


def flatten(structure, key="", path="", flattened=None):
    if flattened is None:
        flattened = {}
    if type(structure) not in(dict, list):
        flattened[((path + "_") if path else "") + key] = structure
    elif isinstance(structure, list):
        for i, item in enumerate(structure):
            flatten(item, "%d" % i, path + "_" + key, flattened)
    else:
        for new_key, value in structure.items():
            flatten(value, new_key, path + "_" + key, flattened)
    return flattened


def fetch_url(url):
    '''Returns fetched url'''
    try:
        result = urllib2.urlopen(url)
    except urllib2.HTTPError as e:
        # Checking for 401 allows module to retry authentication without restart
        if e.code == 401:
            logging.error('HTTPError: ' + str(e.reason) + ' ' + str(e.code))
            auth_admin_url()
        else:
            logging.error('HTTPError: ' + str(e.reason) + ' ' + str(e.code))
    else:
        return result


def auth_admin_url():
    '''Returns fetched url'''
    global url, username, password
    logging.debug('HTTP basic authentication with '
                  'username=' + username + ', password=' + password)
    if (username and password):
        try:
            password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            password_mgr.add_password(None, url, username, password)
            handler = urllib2.HTTPBasicAuthHandler(password_mgr)
            opener = urllib2.build_opener(handler)
            opener.open(url)
            urllib2.install_opener(opener)
        except urllib2.HTTPError as e1:
            logging.error('HTTPError: ' + str(e1.reason) + ' ' + str(e1.code))
        except urllib2.URLError as e2:
            logging.error('URLError: ' + str(e2.reason))
        except Exception as e3:
            logging.error('Error: ' + str(e3.message))


def create_desc(skel, prop):
    d = skel.copy()
    for k, v in prop.iteritems():
        d[k] = v
    return d


def metric_init(params):
    '''Initialize hhvm module'''
    global descriptors, metric_map
    global url, username, password
    global Desc_Skel_Memory, Desc_Skel_Health

    url = params.get('url', 'http://localhost:9001/')
    username = params.get('user', '')
    password = params.get('pass', '')

    logging.debug('metric_init received params: ' +
                  'user=' + username + ' pass=' + password + ' url=' + url)

    logging.debug('metric_init calls auth_admin_url() for '
                  'initial HTTP basic authentication')
    auth_admin_url()

    memory_data = MemoryData()
    health_data = HealthData()
    jemalloc_data = JemallocData()

    descriptors = []

    Desc_Skel_Memory = {
        'name': 'XXX',
        'call_back': memory_data.get,
        'time_max': 20,
        'value_type': 'uint',
        'format': '%u',
        'units': 'XXX',
        'slope': 'both',  # zero|positive|negative|both
        'description': 'XXX',
        'groups': 'hhvm',
        }

    Desc_Skel_Health = {
        'name': 'XXX',
        'call_back': health_data.get,
        'time_max': 20,
        'value_type': 'uint',
        'format': '%u',
        'units': 'XXX',
        'slope': 'both',  # zero|positive|negative|both
        'description': 'XXX',
        'groups': 'hhvm',
    }

    Desc_Skel_Jemalloc = {
        'name': 'XXX',
        'call_back': jemalloc_data.get,
        'time_max': 20,
        'value_type': 'uint',
        'format': '%u',
        'units': 'XXX',
        'slope': 'both',  # zero|positive|negative|both
        'description': 'XXX',
        'groups': 'hhvm',
    }

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_procstats_vmsize",
        "units": "Bytes",
        "description": "process vm Size",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_procstats_vmrss",
        "units": "Bytes",
        "description": "process rss size",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_procstats_shared",
        "units": "Bytes",
        "description": "process shared size",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_procstats_code",
        "units": "Bytes",
        "description": "process code size",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_procstats_data",
        "units": "Bytes",
        "description": "process data size",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_static_strings_bytes",
        "units": "Bytes",
        "description": "breakdown static strings",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_static_strings_count",
        "units": "",
        "description": "breakdown static strings",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_code_bytes",
        "units": "Bytes",
        "description": "breakdown code",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_tcjit_bytes",
        "units": "Bytes",
        "description": "breakdown tc/jit",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_tcjit_code_cold_capacity",
        "units": "Bytes",
        "description": "breakdown tc/Jjit code cold capacity",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_tcjit_code_cold_used",
        "units": "Bytes",
        "description": "breakdown tc/jit code cold used",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_tcjit_code_hot_capacity",
        "units": "Bytes",
        "description": "breakdown tc/jit code hot capacity",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_tcjit_code_hot_used",
        "units": "Bytes",
        "description": "breakdown tc/jit code hot used",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_tcjit_code_frozen_capacity",
        "units": "Bytes",
        "description": "breakdown tc/jit code frozen capacity",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_tcjit_code_frozen_used",
        "units": "Bytes",
        "description": "breakdown tc/jit code frozen used",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_tcjit_code_main_capacity",
        "units": "Bytes",
        "description": "breakdown tc/jit code main capacity",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_tcjit_code_main_used",
        "units": "Bytes",
        "description": "breakdown tc/jit code main used",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_tcjit_code_prof_capacity",
        "units": "Bytes",
        "description": "breakdown tc/jit code prof capacity",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_tcjit_code_prof_used",
        "units": "Bytes",
        "description": "breakdown tc/jit code prof used",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_tcjit_data_capacity",
        "units": "Bytes",
        "description": "breakdown tc/jit data capacity",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_tcjit_data_used",
        "units": "Bytes",
        "description": "breakdown tc/jit data used",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_tcjit_total_capacity",
        "units": "Bytes",
        "description": "breakdown tc/jit total capacity",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_tcjit_total_used",
        "units": "Bytes",
        "description": "breakdown tc/jit total used",
        }))

    descriptors.append(create_desc(Desc_Skel_Memory, {
        "name": "hhvm_mem_breakdown_unknown",
        "units": "Bytes",
        "description": "breakdown unknown",
        }))

    descriptors.append(create_desc(Desc_Skel_Health, {
        "name": "hhvm_health_funcs",
        "units": "",
        "description": "funcs",
        }))

    descriptors.append(create_desc(Desc_Skel_Health, {
        "name": "hhvm_health_units",
        "units": "",
        "description": "units",
        }))

    descriptors.append(create_desc(Desc_Skel_Health, {
        "name": "hhvm_health_hhbc_roarena_capac",
        "units": "Bytes",
        "description": "hhbc roarena capacity",
        }))

    descriptors.append(create_desc(Desc_Skel_Health, {
        "name": "hhvm_health_load",
        "units": "",
        "description": "load",
        }))

    descriptors.append(create_desc(Desc_Skel_Health, {
        "name": "hhvm_health_queued",
        "units": "",
        "description": "queued",
        }))

    descriptors.append(create_desc(Desc_Skel_Health, {
        "name": "hhvm_health_rds",
        "units": "",
        "description": "rds",
        }))

    descriptors.append(create_desc(Desc_Skel_Health, {
        "name": "hhvm_health_target_cache",
        "units": "Bytes",
        "description": "target cache",
        }))

    descriptors.append(create_desc(Desc_Skel_Jemalloc, {
        "name": "hhvm_jemalloc_low_allocated",
        "units": "Bytes",
        "description": "hhvm jemalloc low allocated",
        }))

    descriptors.append(create_desc(Desc_Skel_Jemalloc, {
        "name": "hhvm_jemalloc_allocated",
        "units": "Bytes",
        "description": "hhvm jemalloc allocated",
        }))

    descriptors.append(create_desc(Desc_Skel_Jemalloc, {
        "name": "hhvm_jemalloc_mapped",
        "units": "Bytes",
        "description": "hhvm jemalloc mapped",
        }))

    descriptors.append(create_desc(Desc_Skel_Jemalloc, {
        "name": "hhvm_jemalloc_active",
        "units": "Bytes",
        "description": "hhvm jemalloc active",
        }))

    descriptors.append(create_desc(Desc_Skel_Jemalloc, {
        "name": "hhvm_jemalloc_low_mapped",
        "units": "Bytes",
        "description": "hhvm jemalloc low mapped",
        }))

    descriptors.append(create_desc(Desc_Skel_Jemalloc, {
        "name": "hhvm_jemalloc_low_active",
        "units": "Bytes",
        "description": "hhvm jemalloc low active",
        }))

    descriptors.append(create_desc(Desc_Skel_Jemalloc, {
        "name": "hhvm_jemalloc_error",
        "units": "Bytes",
        "description": "hhvm jemalloc error",
        }))

    return descriptors


def metric_cleanup():
    '''Clean up the metric module.'''
    logging.debug('metric_cleanup')
    pass


# This code is for debugging and unit testing
if __name__ == '__main__':
    params = {
        'url': 'http://localhost/memory.json',
        'user': '',
        'pass': ''
    }

    metric_init(params)
    for d in descriptors:
        v = d['call_back'](d['name'])
        print 'value for %s is %u' % (d['name'],  int(v))
