#!/usr/bin/env python3
"""Ganglia GMOND Module to get metrics from EMC Recoverpoint v4.x"""
__author__ = 'Evan Fraser'
__email__ = 'evan.fraser@trademe.co.nz'
__license__ = 'GPL'

import json, sys, os, time, requests, urllib3
from pprint import pprint

cg_dict = {}
cluster_dict = {}
cluster_ip = '<clustermgmtip>'
username = '<username>'
password = '<password>'
base_url = 'https://' + cluster_ip
descriptors = list()

METRICS_CACHE_MAX = 60

METRICS = {
    'time': 0,
    'data': {}
}
LAST_METRICS = dict(METRICS)


def get_metric(metric_name):
    """Callback function, input is name of metric, returns the metrics value,
    Gathers metrics all together once per polling interval"""
    global username, password, base_url, cg_dict, METRICS, LAST_METRICS, METRICS_CACHE_MAX
    print(metric_name)
    query_headers = {'content-type': 'application/json', 'accept': 'application/json'}

    metrics = {}
    #Code to get statistics...
    #Consistency Group Metrics here
    pprint(cg_dict)
    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:
        for cg in cg_dict:
            #get uid
            cg_uid = cg_dict[cg]['uid']
            #build req_url
            req_url = '/fapi/rest/4_0/statistics/groups/' + str(cg_uid)
            #perform query for CG
            try:
                r = requests.get(base_url + req_url, auth=(username,password), headers=query_headers, verify=False)

                #take the raw response text and deserialize it into a python object.
                responseObj = json.loads(r.text)

            except Exception as e:
                print(str(e))
                print(r.status_code)
                exit(1)


            for cluster in responseObj['consistencyGroupCopyStatistics']:
                #print(item)
                cluster_id = cluster['copyUID']['globalCopyUID']['clusterUID']
                if cluster['journalStatistics'] is None:
                    print('Production site is: ' + str(cluster_id))
                    inc_cluster_throughput = cluster['incomingThroughput']
                    inc_cluster_writes = cluster['incomingWrites']
                    print(str(cluster_id) + ' ' + str(inc_cluster_throughput) + ' ' + str(inc_cluster_writes))
                    metrics[cg + '_incomingThroughput'] = float(cluster['incomingThroughput'])
                    metrics[cg + '_incomingWrites'] = float(cluster['incomingWrites'])

                else:
                    #This is the replica site
                    print('Replica site is: ' + str(cluster_id))
                    metrics[cg + '_journalLagInBytes'] = float(cluster['journalStatistics']['journalLagInBytes'])
                    metrics[cg + '_actualJournalSizeInBytes'] = float(cluster['journalStatistics']['actualJournalSizeInBytes'])
                    metrics[cg + '_actualJournalUsageInBytes'] = float(cluster['journalStatistics']['actualJournalUsageInBytes'])

            for group in responseObj['consistencyGroupLinkStatistics']:
                metrics[cg + '_linkCompressionRatio'] = float(group['pipeStatistics']['compressionRatio'])
                metrics[cg + '_linkDeduplicationRatio'] = float(group['pipeStatistics']['deduplicationRatio'])
                metrics[cg + '_linkOutgoingThroughput'] = float(group['pipeStatistics']['outgoingThroughput'])
                metrics[cg + '_linkTimeLag'] = float(group['pipeStatistics']['lag']['timeCounter'])
                metrics[cg + '_linkDataLag'] = float(group['pipeStatistics']['lag']['dataCounter'])
                metrics[cg + '_linkInitIncomingThroughput'] = float(group['initStatistics']['initIncomingThroughput'])
                metrics[cg + '_linkInitOutgoingThroughput'] = float(group['initStatistics']['initOutgoingThroughput'])
                metrics[cg + '_linkInitCompletionPortion'] = float((group['initStatistics']['initCompletionPortion']) * 100)

            print(len(responseObj['consistencyGroupLinkStatistics']))

        LAST_METRICS = dict(METRICS)
        METRICS = {
            'time': time.time(),
            'data': metrics
        }

    return METRICS['data'][metric_name]


def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.items():
        d[k] = v
    return d

def metric_init(params):
    """metric_init(params) this is called by gmond to initialise the metrics"""

    global base_url, cg_dict, password, username

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_metric,
        'time_max'    : 600,
        'value_type'  : 'double',
        'format'      : '%0f',
        'units'       : 'XXX',
        'slope'       : 'both',
        'description' : 'XXX',
        'groups'      : 'switch',
    }


    #set the headers for how we want the response
    query_headers = {'content-type': 'application/json','accept':'application/json'}

    #get list of all cg_group uids
    req_url = '/fapi/rest/4_0/settings/groups/all_uids'

    try:
        r = requests.get(base_url + req_url, auth=(username,password), headers=query_headers, verify=False,)
        uid_dict = json.loads(r.text)

    except Exception as e:
        print('failed to get list of uids: ', str(e))
        exit(1)

    #get names for all cg_group uids
    for uid in uid_dict:
        req_url = '/fapi/rest/4_0/settings/groups/' + str(uid['id']) + '/name'
        try:
            r = requests.get(base_url + req_url, auth=(username,password), headers=query_headers, verify=False,)
            #print('name of ' + str(uid['id']) + ' ' + r.text)
        except Exception as e:
            print('Failed to get names for uids', str(e))
            exit(1)
        #put the UID's and names in a dict
        cg_dict[r.text] = {'uid': uid['id']}

    #get list of cluster uids
    req_url = '/fapi/rest/4_0/settings/system/full'

    try:
        r = requests.get(base_url + req_url, auth=(username,password), headers=query_headers, verify=False,)
        settings_dict = json.loads(r.text)
    except Exception as e:
        print('Failed to get all settings', str(e))
        exit(1)

    #put uid + cluster names in a dict.
    for cluster in settings_dict['clustersSettings']:

        cluster_dict[cluster['clusterName']] = {'uid' : cluster['clusterUID']['id']}


    #define the metrics we want
    spoof_string = cluster_ip + ':recoverpoint'
    #per Consistency Group Copy
    for cg_name in cg_dict.keys():
        # incomingWrites
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(cg_name) + '_incomingWrites',
                    "units"       : "iops",
                    "description" : "CG Incoming Writes",
                    "groups"      : "iops",
                    "spoof_host"  : spoof_string,
                    }))
        # incomingThroughput
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(cg_name) + '_incomingThroughput',
                    "units"       : "Bytes",
                    "description" : "CG Incoming Throughput",
                    "groups"      : "throughput",
                    "spoof_host"  : spoof_string,
                    }))

        # journalLagInBytes
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(cg_name) + '_journalLagInBytes',
                    "units"       : "Bytes",
                    "description" : "CG Incoming Writes",
                    "groups"      : "journal",
                    "spoof_host"  : spoof_string,
                    }))
        # actualJournalSizeInBytes
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(cg_name) + '_actualJournalSizeInBytes',
                    "units"       : "Bytes",
                    "description" : "CG Journal Size",
                    "groups"      : "journal",
                    "spoof_host"  : spoof_string,
                    }))
        # actualJournalUsageInBytes
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(cg_name) + '_actualJournalUsageInBytes',
                    "units"       : "Bytes",
                    "description" : "CG Journal Usage",
                    "groups"      : "journal",
                    "spoof_host"  : spoof_string,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(cg_name) + '_linkCompressionRatio',
                    "units"       : "Ratio",
                    "description" : "CG Link Compression Ratio",
                    "groups"      : "link",
                    "spoof_host"  : spoof_string,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(cg_name) + '_linkDeduplicationRatio',
                    "units"       : "Ratio",
                    "description" : "CG Link Deduplication Ratio",
                    "groups"      : "link",
                    "spoof_host"  : spoof_string,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(cg_name) + '_linkTimeLag',
                    "units"       : "microseconds",
                    "description" : "CG Link Time Lag",
                    "groups"      : "link",
                    "spoof_host"  : spoof_string,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(cg_name) + '_linkDataLag',
                    "units"       : "Bytes",
                    "description" : "CG Link Data Lag",
                    "groups"      : "link",
                    "spoof_host"  : spoof_string,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(cg_name) + '_linkOutgoingThroughput',
                    "units"       : "Bytes",
                    "description" : "CG Link Outgoing Throughput",
                    "groups"      : "link",
                    "spoof_host"  : spoof_string,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(cg_name) + '_linkInitIncomingThroughput',
                    "units"       : "Bytes",
                    "description" : "CG Link Init Incoming Throughput",
                    "groups"      : "init",
                    "spoof_host"  : spoof_string,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(cg_name) + '_linkInitOutgoingThroughput',
                    "units"       : "Bytes",
                    "description" : "CG Link Init Outgoing Throughput",
                    "groups"      : "init",
                    "spoof_host"  : spoof_string,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : str(cg_name) + '_linkInitCompletionPortion',
                    "units"       : "Percent",
                    "description" : "CG Link Inititalisation Completion",
                    "groups"      : "init",
                    "spoof_host"  : spoof_string,
                    }))


    return descriptors

if __name__ == '__main__':
    """Main function, for when executed from CLI"""
    params = {

    }
    descriptors = metric_init(params)
    pprint(descriptors)
    print(len(descriptors))
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print('value for %s is %u' % (d['name'],  v))
        print('Sleeping 5 seconds')
        time.sleep(5)


