#!/usr/bin/env python3
# Name: gmond_3par.py
# Desc: Ganglia Python module for gathering HP 3PAR storage metrics via ssh
# Author: Evan Fraser (evan.fraser@trademe.co.nz)
# Date: 07/05/2015
import warnings,time,readline
from pprint import pprint

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import paramiko


array_dict = {}

descriptors = list()
METRICSDICT = {
    'time' : 0,
    'data' : {}
}

'''This is the minimum interval between querying the RPA for metrics.
Each ssh query takes 1.6s so we limit the interval between getting metrics to this interval.'''

METRICS_CACHE_MAX = 15


def run_ssh_thread(ip,user,passwd,cmd):

    sshcon = paramiko.SSHClient()
    sshcon.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        sshcon.connect(ip, username=user,password=passwd,look_for_keys='False')
        stdin, stdout, stderr = sshcon.exec_command(cmd)


    except paramiko.ssh_exception.AuthenticationException as e:
        print('Failed to perform SSH', e)
        exit(1)

    except:
        print('Failed to perform SSH')
        exit(1)

    output_list = []
    for line in stdout:
        #print(line)
        output_list.append(line)

    return output_list


def get_vol_perf_stats(ip, user, passwd):

    cmd = 'statvv -iter 1 -rw'
    line_list = run_ssh_thread(ip, user, passwd, cmd)
    vol_perf_stats = []
    line_num = 0
    for line in line_list:
        line_num += 1
        if '---' in line:
            break
        '''if line_num == 2:
            print(line)'''
        if line_num >= 4:

            #volname, metrictype, iocur, ioavg,iomax,thrcur,thravg,thrmax,latcur,latavg,sizecur,sizeavg,qlen = line.split()
            vol_perf_stats.append(line)

    return vol_perf_stats


def get_cpg_stats(ip, user, passwd):

    cmd = 'showcpg'
    line_list = run_ssh_thread(ip, user, passwd, cmd)

    cpg_stats = []
    line_num = 0
    for line in line_list:
        line_num += 1
        if '-------------------------------------------------' in line:
            break
        '''if line_num == 2:
            print(line)'''
        if line_num >= 4:

            cpg_stats.append(line)

    return cpg_stats

def get_cpu_stats(ip, user, passwd):

    cmd = 'statcpu -iter 1 -t'
    line_list = run_ssh_thread(ip, user, passwd, cmd)

    cpu_stats = []
    line_num = 0
    for line in line_list:
        line_num += 1

        if line_num >= 3:
            if bool(line.strip()):
                cpu_stats.append(line)

    return cpu_stats

def get_vol_list(ip, user, passwd):
    '''Get a list of volumes to build metric definitions with'''
    cmd = 'showvv'

    showvv_list = run_ssh_thread(ip, user, passwd, cmd)

    vol_list = []
    line_num = 0
    for line in showvv_list:

        line_num += 1
        if '-------------------------' in line:
            break
        if '-----' in line or 'rcpy.' in line or '.srdata' in line or '0 admin' in line:
            continue
        if line_num >= 4:
            vol_stats = line.split()
            vol_list.append(vol_stats[1])

    return vol_list

def get_cpg_list(ip, user, passwd):
    '''Get a list of CPGs to build metric definitions with'''
    cmd = 'showcpg'

    showcpg_list = run_ssh_thread(ip, user, passwd, cmd)

    cpg_list = []
    line_num = 0
    for line in showcpg_list:

        line_num += 1
        if '-------------------------' in line:
            break
        if '-----' in line or 'rcpy.' in line or '.srdata' in line or '0 admin' in line:
            continue
        if line_num >= 4:
            cpg_stats = line.split()
            cpg_list.append(cpg_stats[1])

    return cpg_list

def get_cpu_list(ip, user, passwd):
    '''Get a list of cpus to build metric definitions with'''
    cmd = 'statcpu -iter 1 -t'

    showcpu_list = run_ssh_thread(ip, user, passwd, cmd)

    cpu_list = []
    line_num = 0
    for line in showcpu_list:
        line_num += 1
        if line_num >= 3:
            cpu_stats = line.split()
            if len(cpu_stats) > 2:
                #statcpu output has format: '#, total'  We just want the node number
                cpu_list.append(cpu_stats[0].split(',')[0])

    return cpu_list


def get_metric(name):
    """Callback function to get the metrics"""

    global METRICSDICT

    metrics = {}

    if (time.time() - METRICSDICT['time']) > METRICS_CACHE_MAX:
        print('time expired, will get metrics')
        for array in array_dict:
            arrayname = array_dict[array]
            #Get vol performance statistics
            vol_perf_stats = get_vol_perf_stats(array_dict[array]['ipaddr'], array_dict[array]['user'], array_dict[array]['pass'])

            for vol in vol_perf_stats:
                vol_name, metric_type, iocur, ioavg,iomax,thrcur,thravg,thrmax,latcur,latavg,sizecur,sizeavg,qlen = vol.split()
                #print(vol_name)

                '''don't give metrics on rcopy snapshots'''
                if 'rcpy' in vol_name:
                    continue
                elif 'r' in metric_type:
                    #print('IOcurr: ',iocur)
                    metrics[array_dict[array]['array_name'] + '_' + vol_name + '_read_iops'] = float(iocur)
                    metrics[array_dict[array]['array_name'] + '_' + vol_name + '_read_latency'] = float(latcur)
                    metrics[array_dict[array]['array_name'] + '_' + vol_name + '_read_throughput'] = float(thrcur)
                    metrics[array_dict[array]['array_name'] + '_' + vol_name + '_read_iosize'] = float(sizecur)

                elif 'w' in metric_type:
                    metrics[array_dict[array]['array_name'] + '_' + vol_name + '_write_iops'] = float(iocur)
                    metrics[array_dict[array]['array_name'] + '_' + vol_name + '_write_latency'] = float(latcur)
                    metrics[array_dict[array]['array_name'] + '_' + vol_name + '_write_throughput'] = float(thrcur)
                    metrics[array_dict[array]['array_name'] + '_' + vol_name + '_write_iosize'] = float(sizecur)
                elif 't' in metric_type:
                    metrics[array_dict[array]['array_name'] + '_' + vol_name + '_qlen'] = float(qlen)

            '''Get CPG Statistics'''
            cpg_statistics = get_cpg_stats(array_dict[array]['ipaddr'], array_dict[array]['user'], array_dict[array]['pass'])

            for cpg in cpg_statistics:
                cpg_num, cpg_name, warn_pc, num_vv, num_tpvv, num_tdvv, usr_vvs, usr_snaps, cpg_total_user, \
                cpg_used_user, cpg_total_snap, cpg_used_snap, cpg_total_adm, cpg_used_adm = cpg.split()
                metrics[array_dict[array]['array_name'] + '_' + cpg_name + '_cpg_usr_used'] = float(cpg_used_user)
                metrics[array_dict[array]['array_name'] + '_' + cpg_name + '_cpg_snap_used'] = float(cpg_used_snap)
                metrics[array_dict[array]['array_name'] + '_' + cpg_name + '_cpg_usr_used'] = float(cpg_used_user)
                metrics[array_dict[array]['array_name'] + '_' + cpg_name + '_cpg_num_vvols'] = float(num_vv)


            '''Get Node CPU Statistics'''
            cpu_statistics = get_cpu_stats(array_dict[array]['ipaddr'], array_dict[array]['user'], array_dict[array]['pass'])
            for node in cpu_statistics:
                '''node,cpu user sys idle intr/s ctxt/s'''

                node_num, user_cpu, sys_cpu, idle_cpu, intrs_cpu, ctxts_cpu = node.split()
                #remove the ', total' from the node number
                node_num = node_num.split(',')[0]
                metrics[array_dict[array]['array_name'] + '_node' + node_num + '_user_cpu'] = float(user_cpu)
                metrics[array_dict[array]['array_name'] + '_node' + node_num + '_sys_cpu'] = float(sys_cpu)
                metrics[array_dict[array]['array_name'] + '_node' + node_num + '_idle_cpu'] = float(idle_cpu)
                metrics[array_dict[array]['array_name'] + '_node' + node_num + '_intrs_cpu'] = float(intrs_cpu)
                metrics[array_dict[array]['array_name'] + '_node' + node_num + '_ctxts_cpu'] = float(ctxts_cpu)

        METRICSDICT= {
            'time': time.time(),
            'data': metrics
        }

    if name in METRICSDICT['data']:
        return METRICSDICT['data'][name]
    else:
        return 0

def create_desc(skel, prop):
    d = skel.copy()

    for k,v in iter(prop.items()):
        d[k] = v
    return d


def define_metrics(Desc_Skel, array_name, vols, ip, cpgs, cpus):
    '''Volume metrics'''
    for vol in vols:
        '''Iops'''
        descriptors.append(create_desc(Desc_Skel, {
                    "name": (array_name + '_' + vol + '_read_iops').encode('ascii', 'ignore'),
                    "units": 'iops',
                    "description" : "Read IOs per second",
                    'groups': 'io',
                    "spoof_host"  : str(ip) + ':' + array_name,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name": (array_name + '_' + vol + '_write_iops').encode('ascii', 'ignore'),
                    "units": 'iops',
                    "description" : "Write IOs per second",
                    'groups': 'io',
                    "spoof_host"  : str(ip) + ':' + array_name,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name": (array_name + '_' + vol + '_qlen').encode('ascii', 'ignore'),
                    "units": 'ios',
                    "description" : "Queue Length",
                    'groups': 'io',
                    "spoof_host"  : str(ip) + ':' + array_name,
                    }))
        '''Latency'''
        descriptors.append(create_desc(Desc_Skel, {
                    "name": (array_name + '_' + vol + '_read_latency').encode('ascii', 'ignore'),
                    "units": 'ms',
                    "description" : "Read response time",
                    'groups': 'latency',
                    "spoof_host"  : str(ip) + ':' + array_name,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name": (array_name + '_' + vol + '_write_latency').encode('ascii', 'ignore'),
                    "units": 'ms',
                    "description" : "Write response time",
                    'groups': 'latency',
                    "spoof_host"  : str(ip) + ':' + array_name,
                    }))
        '''Throughput'''
        descriptors.append(create_desc(Desc_Skel, {
                    "name": (array_name + '_' + vol + '_read_throughput').encode('ascii', 'ignore'),
                    "units": 'KB',
                    "description" : "Read throughput",
                    'groups': 'throughput',
                    "spoof_host"  : str(ip) + ':' + array_name,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name": (array_name + '_' + vol + '_write_throughput').encode('ascii', 'ignore'),
                    "units": 'KB',
                    "description" : "Write throughput",
                    'groups': 'throughput',
                    "spoof_host"  : str(ip) + ':' + array_name,
                    }))
        '''IOsz'''
        descriptors.append(create_desc(Desc_Skel, {
                    "name": (array_name + '_' + vol + '_read_iosize').encode('ascii', 'ignore'),
                    "units": 'KB',
                    "description" : "Read IO Size",
                    'groups': 'io',
                    "spoof_host"  : str(ip) + ':' + array_name,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name": (array_name + '_' + vol + '_write_iosize').encode('ascii', 'ignore'),
                    "units": 'KB',
                    "description" : "Write IO Size",
                    'groups': 'io',
                    "spoof_host"  : str(ip) + ':' + array_name,
                    }))

    for cpg in cpgs:
        descriptors.append(create_desc(Desc_Skel, {
                    "name": (array_name + '_' + cpg + '_cpg_usr_used').encode('ascii', 'ignore'),
                    "units": 'MB',
                    "description" : "CPG User Capacity",
                    'groups': 'CPG',
                    "spoof_host"  : str(ip) + ':' + array_name,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name": (array_name + '_' + cpg + '_cpg_snap_used').encode('ascii', 'ignore'),
                    "units": 'MB',
                    "description" : "CPG Snap Capacity",
                    'groups': 'CPG',
                    "spoof_host"  : str(ip) + ':' + array_name,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name": (array_name + '_' + cpg + '_num_vvols').encode('ascii', 'ignore'),
                    "units": 'VVs',
                    "description" : "CPG Number of VVols",
                    'groups': 'CPG',
                    "spoof_host"  : str(ip) + ':' + array_name,
                    }))

    for cpu in cpus:
        print((array_name + '_node' + str(cpu) + '_user_cpu').encode('ascii', 'ignore'))
        descriptors.append(create_desc(Desc_Skel, {
                    "name": (array_name + '_node' + str(cpu) + '_user_cpu').encode('ascii', 'ignore'),
                    "units": 'Percent',
                    "description" : "Node CPU User",
                    'groups': 'CPU',
                    "spoof_host"  : str(ip) + ':' + array_name,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name": (array_name + '_node' + str(cpu) + '_sys_cpu').encode('ascii', 'ignore'),
                    "units": 'Percent',
                    "description" : "Node CPU System",
                    'groups': 'CPU',
                    "spoof_host"  : str(ip) + ':' + array_name,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name": (array_name + '_node' + str(cpu) + '_idle_cpu').encode('ascii', 'ignore'),
                    "units": 'Percent',
                    "description" : "Node CPU Idle",
                    'groups': 'CPU',
                    "spoof_host"  : str(ip) + ':' + array_name,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name": (array_name + '_node' + str(cpu) + '_intrs_cpu').encode('ascii', 'ignore'),
                    "units": 'intr/s',
                    "description" : "Node CPU Interupts/s",
                    'groups': 'CPU',
                    "spoof_host"  : str(ip) + ':' + array_name,
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name": (array_name + '_node' + str(cpu) + '_ctxts_cpu').encode('ascii', 'ignore'),
                    "units": 'ctxt/s',
                    "description" : "Node CPU Context Switches",
                    'groups': 'CPU',
                    "spoof_host"  : str(ip) + ':' + array_name,
                    }))


    return descriptors


def metric_init(params):
    """metric_init(params) this is called by gmond to initialise the metrics"""

    global array_dict

    array_dict = { 
        'array1': {'array_name': 'array1', 'ipaddr': '192.168.1.50', 'user': '3paruser', 'pass': '3parpass'},
        'array2': {'array_name': 'array2', 'ipaddr': '192.168.1.51', 'user': '3paruser', 'pass': '3parpass'},

    }

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_metric,
        'time_max'    : 600,
        'value_type'  : 'double',
        'format'      : '%0f',
        'units'       : 'XXX',
        'slope'       : 'both',
        'description' : 'XXX',
        'groups'      : 'storage',
    }
    descriptors = []

    for array in array_dict:
        ip = array_dict[array]['ipaddr']
        user = array_dict[array]['user']
        passwd = array_dict[array]['pass']
        '''Get a list of volumes in the array'''
        vols = get_vol_list(ip, user, passwd)

        '''Get a list of CPGs in the array'''
        cpgs = get_cpg_list(ip, user, passwd)

        '''Get a list of CPUs in the array - Only getting totals per node at this point'''
        cpus = get_cpu_list(ip, user, passwd)

        '''create descriptors for the array'''
        array_descriptors = define_metrics(Desc_Skel, array_dict[array]['array_name'], vols, ip, cpgs, cpus)
        descriptors = descriptors + array_descriptors

    return descriptors


if __name__ == '__main__':
    """Main function, for when executed from CLI"""
    params = {
        'array1': {'array_name': 'array1', 'ipaddr': '192.168.1.50', 'user': '3paruser', 'pass': '3parpass'},
        'array2': {'array_name': 'array2', 'ipaddr': '192.168.1.51', 'user': '3paruser', 'pass': '3parpass'},

    }

    descriptors = metric_init(params)
    #pprint(descriptors)
    #print(len(descriptors))
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            #print('value for %s is %u' % (d['name'],  v))
        print('Sleeping 5 seconds')
        time.sleep(5)
