#!/usr/bin/env python
#
# Storm Topology gmond module for Ganglia
#
# Copyright (C) 2015 by Nipun Talukdar <nipunmlist [at] gmail [dot] com>.
# All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
import logging
import md5
import pickle
import re
import sys
from time import time
from thrift.transport import TTransport, TSocket
from thrift.protocol import TBinaryProtocol

clusterinfo = None
topology_found = True
descriptors = list()
topologies = []
serialfile_dir = '/tmp'
topology_summary_cols_map = {'status': 'Status', 'num_workers': 'Worker Count',
                             'num_executors': 'ExecutorCount', 'uptime_secs': 'Uptime',
                             'num_tasks': 'TaskCount'}

spout_stats = {'Executors': ['Count', '%u', 'uint'], 'Tasks': ['Count', '%u', 'uint'],
               'Emitted': ['Count', '%f', 'double'],
               'Transferred': ['Count/sec', '%f', 'double'],
               'CompleteLatency': ['ms', '%f', 'double'], 'Acked': ['Count/Sec', '%f', 'double'],
               'Failed': ['Count/sec', '%f', 'double']}

bolt_stats = {'Executors': ['Count', '%u', 'uint'], 'Tasks': ['Count', '%u', 'uint'],
              'Emitted': ['Count/sec', '%f', 'double'],
              'Executed': ['Count/sec', '%f', 'double'],
              'Transferred': ['Count/sec', '%f', 'double'],
              'ExecuteLatency': ['ms', '%f', 'double'],
              'ProcessLatency': ['ms', '%f', 'double'],
              'Acked': ['Count/sec', '%f', 'double'],
              'Failed': ['Count/sec', '%f', 'double']}

diff_cols = ['Acked', 'Failed', 'Executed', 'Transferred', 'Emitted']
overall = {'ExecutorCount': ['Count', '%u', 'uint'],
           'WorkerCount': ['Count', '%u', 'uint'],
           'TaskCount': ['Count', '%u', 'uint'],
           'UptimeSecs': ['Count', '%u', 'uint']}

toplogy_mods = {}
lastchecktime = 0
lastinfotime = 0
maxinterval = 6
all_topology_stats = {}
bolt_array = {}
spout_array = {}
nimbus_host = '127.0.0.1'
nimbus_port = 6627
logging.basicConfig(filename='/tmp/storm_topology.log', level=logging.INFO,
                    format='%(asctime)s  %(levelname)s line:%(lineno)d %(message)s', filemode='w')
logging_levels = {'INFO': logging.INFO, 'DEBUG': logging.DEBUG, 'WARNING': logging.WARNING,
                  'ERROR': logging.ERROR, 'CRITICAL': logging.CRITICAL}


def get_avg(arr):
    if len(arr) < 1:
        return 0
    return sum(arr) / len(arr)


def normalize_stats(stats, duration):
    for k in stats:
        statsk = stats[k]
        if 'Emitted' in statsk and duration > 0:
            if statsk['Emitted'] > 0:
                statsk['Emitted'] = statsk['Emitted'] / duration
        if 'Acked' in statsk and duration > 0:
            if statsk['Acked'] > 0:
                statsk['Acked'] = statsk['Acked'] / duration
        if 'Executed' in statsk and duration > 0:
            if statsk['Executed'] > 0:
                statsk['Executed'] = statsk['Executed'] / duration


def freshen_topology(topology):
    tmpsavestats = None
    inf = None
    savedlastchecktime = 0
    tmp = md5.new()
    tmp.update(topology)
    filename = '/tmp/save_stats_for_' + tmp.hexdigest() + '.pk'
    try:
        inf = open(filename, 'rb')
    except IOError as e:
        logging.warn(e)
    if inf is not None:
        try:
            tmpsavestats = pickle.load(inf)
            savedlastchecktime = pickle.load(inf)
        except EOFError as e:
            logging.warn(e.message())
        inf.close()
    if not all_topology_stats[topology]['topology_stats_got']:
        logging.warn('Info not got for topology ' + topology)
        return
    overallstats = all_topology_stats[topology]['overallstats']
    boltspoutstats = all_topology_stats[topology]['boltspoutstats']
    of = open(filename, 'wb')
    if of is not None:
        pickle.dump(boltspoutstats, of)
        pickle.dump(time(), of)
        of.close()
    if overallstats['UptimeSecs'] > (lastchecktime - savedlastchecktime):
        if tmpsavestats is not None:
            for bolt in bolt_array[topology]:
                if bolt in tmpsavestats and bolt in boltspoutstats:
                    stats_new = boltspoutstats[bolt]
                    stats_old = tmpsavestats[bolt]
                    for key in bolt_stats:
                        if key == 'ExecuteLatency' or key == 'ProcessLatency':
                            continue
                        if key not in stats_new:
                            continue
                        if key not in stats_old:
                            continue
                        if key in diff_cols:
                            stats_new[key] -= stats_old[key]
            for spout in spout_array[topology]:
                if spout in tmpsavestats and spout in boltspoutstats:
                    stats_new = boltspoutstats[spout]
                    stats_old = tmpsavestats[spout]
                    for key in spout_stats:
                        if key == 'CompleteLatency':
                            continue
                        if key not in stats_new:
                            continue
                        if key not in stats_old:
                            continue
                        if key in diff_cols:
                            stats_new[key] -= stats_old[key]
            normalize_stats(boltspoutstats, lastchecktime - savedlastchecktime)
        else:
            normalize_stats(boltspoutstats, overallstats['UptimeSecs'])
    else:
        normalize_stats(boltspoutstats, overallstats['UptimeSecs'])


def freshen():
    global lastchecktime
    if time() > (lastchecktime + maxinterval):
        lastchecktime = time()
        get_topology_stats_for(topologies)
        for topology in topologies:
            freshen_topology(topology)


def callback_boltspout(name):
    freshen()
    first_pos = name.find('_')
    last_pos = name.rfind('_')
    topology_mod = name[0:first_pos]
    bolt = name[first_pos + 1: last_pos]
    statname = name[last_pos + 1:]
    topology = toplogy_mods[topology_mod]
    if not all_topology_stats[topology]['topology_stats_got']:
        logging.debug('Returing 0 for ' + name)
        return 0
    logging.debug('Got stats for ' + name + " " +
                  str(all_topology_stats[topology]['boltspoutstats'][bolt][statname]))
    return all_topology_stats[topology]['boltspoutstats'][bolt][statname]


def callback_overall(name):
    freshen()
    topology_mod, name = name.split('_')
    topology = toplogy_mods[topology_mod]
    if not all_topology_stats[topology]['topology_stats_got']:
        logging.debug('Returing 0 for ' + name)
        return 0
    logging.debug(topology + ' ' + name + ' ' +
                  str(all_topology_stats[topology]['overallstats'][name]))
    return all_topology_stats[topology]['overallstats'][name]


def update_task_count(component_task_count, component_name, count):
    if component_name not in component_task_count:
        component_task_count[component_name] = 0
    component_task_count[component_name] += count


def update_exec_count(component_exec_count, component_name, count):
    if component_name not in component_exec_count:
        component_exec_count[component_name] = 0
    component_exec_count[component_name] += count


def update_whole_num_stat_special(stats, store, boltname, statname):
    if boltname not in store:
        store[boltname] = {}
    if statname not in store[boltname]:
        store[boltname][statname] = 0
    for k in stats:
        if k == '__metrics' or k == '__ack_init' or k == '__ack_ack' or k == '__system':
            continue
        store[boltname][statname] += stats[k]


def update_whole_num_stat(stats, store, boltname, statname):
    if boltname not in store:
        store[boltname] = {}
    if statname not in store[boltname]:
        store[boltname][statname] = 0
    for k in stats:
        store[boltname][statname] += stats[k]


def update_avg_stats(stats, store, boltname, statname):
    if boltname not in store:
        store[boltname] = {}
    if statname not in store[boltname]:
        store[boltname][statname] = []
    for k in stats:
        store[boltname][statname].append(stats[k])


def get_topology_stats_for(topologies):
    all_topology_stats.clear()
    for topology in topologies:
        all_topology_stats[topology] = get_topology_stats(topology)


def refresh_topology_stats():
    logging.debug('Refreshing topology stats')
    for t in topologies:
        all_topology_stats[t] = {'topology_stats_got': False}
    global clusterinfo
    try:
        transport = TSocket.TSocket(nimbus_host, nimbus_port)
        transport.setTimeout(1000)
        framedtrasp = TTransport.TFramedTransport(transport)
        protocol = TBinaryProtocol.TBinaryProtocol(framedtrasp)
        client = Nimbus.Client(protocol)
        framedtrasp.open()
        boltspoutstats = None
        component_task_count = None
        component_exec_count = None
        clusterinfo = client.getClusterInfo()
        for tsummary in clusterinfo.topologies:
            if tsummary.name not in topologies:
                continue
            toplogyname = tsummary.name
            overallstats = {}
            overallstats['ExecutorCount'] = tsummary.num_executors
            overallstats['TaskCount'] = tsummary.num_tasks
            overallstats['WorkerCount'] = tsummary.num_workers
            overallstats['UptimeSecs'] = tsummary.uptime_secs
            all_topology_stats[toplogyname]['overallstats'] = overallstats
            boltspoutstats = {}
            component_task_count = {}
            component_exec_count = {}
            all_topology_stats[toplogyname]['boltspoutstats'] = boltspoutstats
            all_topology_stats[toplogyname]['component_task_count'] = component_task_count
            all_topology_stats[toplogyname]['component_exec_count'] = component_exec_count
            tinfo = client.getTopologyInfo(tsummary.id)
            all_topology_stats[toplogyname]['topology_stats_got'] = True
            for exstat in tinfo.executors:
                stats = exstat.stats
                update_whole_num_stat_special(stats.emitted[":all-time"], boltspoutstats,
                                              exstat.component_id, 'Emitted')
                update_whole_num_stat_special(stats.transferred[":all-time"], boltspoutstats,
                                              exstat.component_id, 'Transferred')

                numtask = exstat.executor_info.task_end - exstat.executor_info.task_end + 1
                update_task_count(component_task_count, exstat.component_id, numtask)
                update_exec_count(component_exec_count, exstat.component_id, 1)
                if stats.specific.bolt is not None:
                    update_whole_num_stat(stats.specific.bolt.acked[":all-time"], boltspoutstats,
                                          exstat.component_id, 'Acked')
                    update_whole_num_stat(stats.specific.bolt.failed[":all-time"], boltspoutstats,
                                          exstat.component_id, 'Failed')
                    update_whole_num_stat(stats.specific.bolt.executed[":all-time"], boltspoutstats,
                                          exstat.component_id, 'Executed')
                    update_avg_stats(stats.specific.bolt.process_ms_avg["600"], boltspoutstats,
                                     exstat.component_id, 'process_ms_avg')
                    update_avg_stats(stats.specific.bolt.execute_ms_avg["600"], boltspoutstats,
                                     exstat.component_id, 'execute_ms_avg')
                if stats.specific.spout is not None:
                    update_whole_num_stat(stats.specific.spout.acked[":all-time"], boltspoutstats,
                                          exstat.component_id, 'Acked')
                    update_whole_num_stat(stats.specific.spout.failed[":all-time"], boltspoutstats,
                                          exstat.component_id, 'Failed')
                    update_avg_stats(stats.specific.spout.complete_ms_avg[":all-time"], boltspoutstats,
                                     exstat.component_id, 'complete_ms_avg')
            if '__acker' in boltspoutstats:
                del boltspoutstats['__acker']
            for key in boltspoutstats:
                if 'complete_ms_avg' in boltspoutstats[key]:
                    avg = get_avg(boltspoutstats[key]['complete_ms_avg'])
                    boltspoutstats[key]['CompleteLatency'] = avg
                    del boltspoutstats[key]['complete_ms_avg']
                if 'process_ms_avg' in boltspoutstats[key]:
                    avg = get_avg(boltspoutstats[key]['process_ms_avg'])
                    boltspoutstats[key]['ProcessLatency'] = avg
                    del boltspoutstats[key]['process_ms_avg']
                if 'execute_ms_avg' in boltspoutstats[key]:
                    avg = get_avg(boltspoutstats[key]['execute_ms_avg'])
                    boltspoutstats[key]['ExecuteLatency'] = avg
                    del boltspoutstats[key]['execute_ms_avg']

            for key in component_task_count:
                if key in boltspoutstats:
                    boltspoutstats[key]['Tasks'] = component_task_count[key]
            for key in component_exec_count:
                if key in boltspoutstats:
                    boltspoutstats[key]['Executors'] = component_exec_count[key]
        framedtrasp.close()

    except Exception as e:
        clusterinfo = None
        logging.warn(e)


def get_topology_stats(toplogyname):
    global lastinfotime
    if (lastinfotime + 4) < time():
        for t in all_topology_stats:
            all_topology_stats[t] = None
        lastinfotime = time()
        refresh_topology_stats()
    return all_topology_stats[toplogyname]


def metric_init_topology(params):
    global descriptors
    groupname = ''
    if 'topology' in params and len(params['topology']):
        groupname = params['topology']
    else:
        return
    topology = groupname
    topology_mod = re.sub("\s+", "", topology)
    topology_mod = re.sub("[_]+", "", topology_mod)
    toplogy_mods[topology_mod] = topology
    if 'spouts' in params:
        spout_array[topology] = re.split('[,]+', params['spouts'])
        for spout in spout_array[topology]:
            for statname in spout_stats:
                d = {'name': topology_mod + '_' + spout + '_' + statname, 'call_back': callback_boltspout,
                     'time_max': 90,
                     'value_type': spout_stats[statname][2],
                     'units': spout_stats[statname][0],
                     'slope': 'both',
                     'format': spout_stats[statname][1],
                     'description': '',
                     'groups': groupname}
                descriptors.append(d)

    if 'bolts' in params:
        bolt_array[topology] = re.split('[,]+', params['bolts'])
        for bolt in bolt_array[topology]:
            for statname in bolt_stats:
                d = {'name': topology_mod + '_' + bolt + '_' + statname, 'call_back': callback_boltspout,
                     'time_max': 90,
                     'value_type': bolt_stats[statname][2],
                     'units': bolt_stats[statname][0],
                     'slope': 'both',
                     'format': bolt_stats[statname][1],
                     'description': '',
                     'groups': groupname}
                descriptors.append(d)

    for key in overall:
        d = {'name': topology_mod + '_' + key, 'call_back': callback_overall,
             'time_max': 90,
             'value_type': overall[key][2],
             'units': overall[key][0],
             'slope': 'both',
             'format': overall[key][1],
             'description': '',
             'groups': groupname}
        descriptors.append(d)
    logging.info('Inited metric for ' + groupname)


def metric_init(params):
    global topologies, nimbus_host, nimbus_port
    if 'nimbus_host' in params:
        nimbus_host = params['nimbus_host']
    if 'nimbus_port' in params:
        nimbus_port = params['nimbus_port']
    if 'topologies' not in params:
        return
    if 'storm_thrift_gen' in params:
        sys.path.append(params['storm_thrift_gen'])
    else:
        sys.path.append('/usr/lib/ganglia')
    if 'loglevel' in params:
        loglevel = params['loglevel'].strip().upper()
        if loglevel in logging_levels:
            logging.getLogger().setLevel(logging_levels[loglevel])

    global Nimbus, ttypes
    from stormpy.storm import Nimbus, ttypes

    tss = re.split('[,]+', params['topologies'])
    topologies = tss
    alltops = {}
    for t in tss:
        alltops[t] = {'topology': t}
        alltops[t]['tlen'] = len(t)
        t_bolts = t + '_bolts'
        if t_bolts in params:
            alltops[t]['bolts'] = params[t_bolts]
        t_spouts = t + '_spouts'
        if t_spouts in params:
            alltops[t]['spouts'] = params[t_spouts]
    for t in alltops:
        logging.info('Initing metric for ' + t)
        metric_init_topology(alltops[t])
    return descriptors

if __name__ == '__main__':
    params = {'topologies': 'SampleTopology,AnotherTopology',
              'SampleTopology_spouts': 'SampleSpoutTwo', 'SampleTopology_bolts': 'boltc',
              'AnotherTopology_spouts': 'Spout', 'AnotherTopology_bolts': 'bolta,boltb,boltd',
              'loglevel': 'ERROR'}
    metric_init(params)
    for d in descriptors:
        v = d['call_back'](d['name'])
        formt = "%s " + d['format']
        print formt % (d['name'], v)
