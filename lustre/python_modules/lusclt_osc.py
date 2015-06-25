#!/usr/bin/env python
"""
# collect lustre client metrics from osc stats files
# https://build.hpdd.intel.com/job/lustre-manual/lastSuccessfulBuild/artifact/lustre_manual.xhtml#lustreproc.clientstats
#
# based on gmond diskstat python module
#
##  Copyright Chris Hunter, Yale University ITS, 2014
##  License to use, modify, and distribute under the GPL
##  http://www.gnu.org/licenses/gpl.txt
"""
__author__ = 'chris.hunter (att) yale.edu (Chris Hunter)'

import os, re, time
import logging
from resource import getpagesize

#logging.basicConfig(level=logging.DEBUG)
logging.basicConfig()
logging.debug('Starting')

gmond_prefix='lusclt_'
gmond_group='lusclt'
tmax = 3600

descriptors = []
stats = dict()
last_val = dict()
cur_time = 0.0
last_update = 0.0

PAGE_SIZE = getpagesize()
MAX_UPDATE_TIME = 5

#OSC_DIR= '/tmp/osc'
OSC_DIR = '/proc/fs/lustre/osc'

##############################################################################
def osc_fslist(directory):
    '''return fs names based on folder names in osc directory'''
    fslist = []
    for fs in os.listdir(directory):
        fir = fs.find('-')
        sec = fs.find('-', fir + 1)
        thrd = fs.find('-',sec + 1)
        fs_name = fs[0:fir]
        if ('num_ref' not in fs_name) and (fs_name not in fslist):
            fslist.append(fs_name)
            yield fs_name

def osc_ostlist(directory,fs):
    '''return OST names based on folder names in osc directory'''
    ostlist = []
    for ost in os.listdir(directory):
        if (fs in ost):
            fir = ost.find('-')
            sec = ost.find('-', fir + 1)
            thrd = ost.find('-',sec + 1)
            ost_name = ost[fir+1:sec]
            if ost_name not in ostlist:
                ostlist.append(ost_name)
                yield ost_name

def get_diff(fs, ost, key, val, convert=1):
    '''return difference between cur_val - last_val, update last_val'''
    global stats, last_val
    if key in last_val[fs][ost]:
        logging.debug(' get_diff for ' + fs + '_' + ost + '_' + key + ': ' + str(val) + ' last_val: ' + str(last_val[fs][ost][key]))
    else:
        logging.debug(' get_diff for ' + fs + '_' + ost + '_' + key + ': ' + str(val))

    if key in last_val[fs][ost]:
        stats[fs][ost][key] = (val - last_val[fs][ost][key]) * float(convert)
    else:
        stats[fs][ost][key] = 0

    # If for some reason we have a negative diff we should assume counters reset
    # and should set it back to 0
    if stats[fs][ost][key] < 0:
        stats[fs][ost][key] = 0

    last_val[fs][ost][key] = val

def get_delta(fs, ost, key, val, convert=1):
    '''return rate per second from delta of cur_time - last_update, update last_val'''
    global stats, last_val
#    if key in last_val[fs][ost]:
#        logging.debug(' get_delta for ' + fs +  '_' + ost + '_' + key + ': ' + str(val) + ' last_val: ' + str(last_val[fs][ost][key]))
#    else:
#        logging.debug(' get_delta for ' + fs +  '_' + ost + '_' + key + ': ' + str(val))

    if convert == 0:
        logging.warning(' convert is zero!')

    interval = cur_time - last_update

    if key in last_val[fs][ost] and interval > 0:
        stats[fs][ost][key] = (val - last_val[fs][ost][key]) * float(convert) / float(interval)
    else:
        stats[fs][ost][key] = 0

    # If for some reason we have a negative diff we should assume counters reset
    # and should set it back to 0
    if stats[fs][ost][key] < 0:
        stats[fs][ost][key] = 0

    last_val[fs][ost][key] = val

def get_osc_stats(directory,fs,ost):
    '''read osc stats file, return as nested list'''
    out = []

    for fspath in os.listdir(directory):
        if (fs in fspath) and (ost in fspath):   #substring test
            logging.debug(' opening file ' + str(directory) + '/' + str(fspath) + '/stats')
            try:
                osc_statsfile = open("%s/%s/stats" % (directory, fspath))
            except IOError:
                osc_statsfile = []

            for line in osc_statsfile:
                item = re.split("\s+", line.rstrip())
                out.append(item)
            #logging.debug(' out: ' + str(out))
            return out

def update_stats():
    '''get osc stats, update stats entries'''
    logging.debug(' update_stats')
    global last_update, stats, last_val, cur_time
    global MAX_UPDATE_TIME

    cur_time = time.time()
    if cur_time - last_update < MAX_UPDATE_TIME:
        logging.debug(' skipping update wait ' + str(int(MAX_UPDATE_TIME - (cur_time - last_update))) + ' seconds')
        return True

    ### update stats
    stats = dict()

    stats['osc'] = dict()
    stats['osc']['total']= dict()
    stats['osc']['total']['read_bytes_per_sec'] = 0
    stats['osc']['total']['write_bytes_per_sec'] = 0
    stats['osc']['total']['ost_ops'] = 0

    for fs in osc_fslist(OSC_DIR):
        logging.debug(' fs: ' + fs)
        if fs not in stats:
            stats[fs] = dict()
        if fs not in last_val:
            last_val[fs] = dict()

        stats[fs]['total'] = dict()
        stats[fs]['total']['read_bytes_per_sec'] = 0
        stats[fs]['total']['write_bytes_per_sec'] = 0
        stats[fs]['total']['ost_ops'] = 0

        for ost in osc_ostlist(OSC_DIR,fs):
            logging.debug(' ost: ' + ost)
            if ost not in stats[fs]:
                stats[fs][ost] = dict()
            if ost not in last_val[fs]:
                last_val[fs][ost] = dict()

            vals = []
            vals = get_osc_stats(OSC_DIR,fs,ost)
            #logging.debug(' vals: ' + str(vals))
            for n in range(len(vals)):
                if 'read_bytes' in vals[n]:
                    get_delta(fs, ost, 'reads', long(vals[n][1]))
                    get_delta(fs, ost, 'read_bytes_per_sec', long(vals[n][6]))
                    stats[fs]['total']['ost_ops'] += stats[fs][ost]['reads']
                    stats[fs]['total']['read_bytes_per_sec'] += stats[fs][ost]['read_bytes_per_sec']

                if 'write_bytes' in vals[n]:
                    get_delta(fs, ost, 'writes', long(vals[n][1]))
                    get_delta(fs, ost, 'write_bytes_per_sec', long(vals[n][6]))
                    stats[fs]['total']['ost_ops'] += stats[fs][ost]['writes']
                    stats[fs]['total']['write_bytes_per_sec'] += stats[fs][ost]['write_bytes_per_sec']

                #if 'ost_read' in vals[n]:
                #    get_delta(fs, ost, 'reads', long(vals[n][1]))
                #    get_delta(fs, ost, 'read_bytes_per_sec', long(vals[n][6]))
                #    stats[fs]['total']['ost_ops'] += stats[fs][ost]['reads']
                #    stats[fs]['total']['read_bytes_per_sec'] += stats[fs][ost]['reads_bytes_per_sec']
                #    
                #if 'ost_write' in vals[n]:
                #    get_delta(fs, ost, 'writes', long(vals[n][1]))
                #    get_delta(fs, ost, 'write_bytes_per_sec', long(vals[n][6]))
                #    stats[fs]['total']['ost_ops'] += stats[fs][ost]['writes']
                #    stats[fs]['total']['write_bytes_per_sec'] += stats[fs][ost]['write_bytes_per_sec']

                if 'ost_statfs' in vals[n]:
                    get_delta(fs,ost,'ost_statfs', long(vals[n][1]))
                    stats[fs]['total']['ost_ops'] += stats[fs][ost]['ost_statfs']

                if 'ost_sync' in vals[n]:
                    get_delta(fs,ost,'ost_sync', long(vals[n][1]))
                    stats[fs]['total']['ost_ops'] += stats[fs][ost]['ost_sync']

                if 'ost_setattr' in vals[n]:
                    get_delta(fs,ost,'ost_setattr', long(vals[n][1]))
                    stats[fs]['total']['ost_ops'] += stats[fs][ost]['ost_setattr']

                if 'ost_get_info' in vals[n]:
                    get_delta(fs,ost,'ost_get_info', long(vals[n][1]))
                    stats[fs]['total']['ost_ops'] += stats[fs][ost]['ost_get_info']

                if 'ost_set_info' in vals[n]:
                    get_delta(fs,ost,'ost_set_info', long(vals[n][1]))
                    stats[fs]['total']['ost_ops'] += stats[fs][ost]['ost_set_info']

                #if 'ost_connect' in vals[n]:
                #    get_delta(fs,ost,'ost_connect', long(vals[n][1]))
                #    stats[fs]['total']['ost_ops'] += stats[fs][ost]['ost_connect']

                if 'ost_destroy' in vals[n]:
                    get_delta(fs,ost,'ost_destroy', long(vals[n][1]))
                    stats[fs]['total']['ost_ops'] += stats[fs][ost]['ost_destroy']

                if 'ost_punch' in vals[n]:
                    get_delta(fs,ost,'ost_punch', long(vals[n][1]))
                    stats[fs]['total']['ost_ops'] += stats[fs][ost]['ost_punch']

                #if 'ost_quotactl' in vals[n]:
                #    get_delta(fs,ost,'ost_quotactl', long(vals[n][1]))
                #    stats[fs]['total']['ost_ops'] += stats[fs][ost]['ost_quotactl']

                if 'ldlm_cancel' in vals[n]:
                    get_delta(fs,ost,'ldlm_cancel', long(vals[n][1]))
                    stats[fs]['total']['ost_ops'] += stats[fs][ost]['ldlm_cancel']
            #end for n 

            logging.debug(' stats['+fs+']['+ost+']' + str(stats[fs][ost]))
            logging.debug(' last_val: ' + str(last_val))
        #end for ost

        stats['osc']['total']['read_bytes_per_sec'] += stats[fs]['total']['read_bytes_per_sec']
        stats['osc']['total']['write_bytes_per_sec'] += stats[fs]['total']['write_bytes_per_sec']
        stats['osc']['total']['ost_ops'] += stats[fs]['total']['ost_ops']
    #end for fs

    logging.debug(' success refreshing stats')
    last_update = cur_time
    return True

def get_value(metric):
    '''get value for name format: gmond_prefix_ + fs_ + ost_ + metric'''
    logging.debug(' getting value: ' + metric)
    global stats

    ret = update_stats()

    if ret:
        if metric.startswith(gmond_prefix):
            fir = metric.find('_')
            sec = metric.find('_', fir + 1)
            thrd = metric.find('_',sec + 1)
            fs = metric[fir+1:sec]
            ost = metric[sec+1:thrd]
            label = metric[thrd+1:]

            try:
                return stats[fs][ost][label]
            except:
                logging.warning('failed to fetch stats [' + fs + '][' + ost + ']' + metric)

    else:
        return 0

def metric_init(params):
    '''initialize descriptor data structure and call update_stats'''
    global descriptors
    logging.debug('metric_init: ' + str(params))

    descriptions = dict(
        reads = {
            'units': 'req/s',
            'description': 'read requests'},
        read_bytes_per_sec = {
            'units': 'bytes/sec',
            'description': 'read bytes/sec'},
        writes = {
            'units': 'req/s',
            'description': 'write requests'},
        write_bytes_per_sec = {
            'units': 'bytes/sec',
            'description': 'write bytes/sec'},
        ost_statfs = {
            'units'       : 'calls/s',
            'description' : 'stat calls'},
        ost_sync = {
            'units'       : 'calls/s',
            'description' : 'sync calls'},
        ost_setattr = {
            'units'       : 'calls/s',
            'description' : 'setattr calls'},
        ost_set_info = {
            'units'       : 'calls/s',
            'description' : 'set_info calls'},
        ost_get_info = {
            'units'       : 'calls/s',
            'description' : 'get_info calls'},
        ost_connect = {
            'units'       : 'calls/s',
            'description' : 'ost_connect calls'},
        ost_destroy = {
            'units'       : 'calls/s',
            'description' : 'ost_destroy object destory calls'},
        #http://lists.lustre.org/pipermail/lustre-discuss/2011-June/015728.html
        ost_punch = {
            'units'       : 'calls/s',
            'description' : 'ost_punch object truncate calls'},
        ost_quotactl = {
            'units'       : 'calls/s',
            'description' : 'quotactl calls'},
        ldlm_cancel = {
            'units'       : 'calls/s',
            'description' : 'ldlm_cancel calls'},
        obd_ping = {
            'units'       : 'req/s',
            'description' : 'obd_ping requests'},
        ost_ops = {
            'units'       : 'calls/s',
            'description' : 'ost op calls'},
    )
    logging.debug('descriptions: ' + str(descriptions))

    update_stats()

    fslist = list(osc_fslist(OSC_DIR))
    fslist.append('osc')
    logging.debug(str(type(fslist))+' fslist: '+str(fslist))
    for fs in fslist:
        ostlist = list(osc_ostlist(OSC_DIR,fs))
        if 'osc' is fs:
            ostlist = ['total']
        else:
            ostlist.append('total')
        logging.debug(str(type(ostlist))+' ostlist: '+str(ostlist))
        for ost in ostlist:
            for label in descriptions:
                logging.debug(' fs: ' + fs + ' ost: ' + ost + ' label: ' + str(label))
                if stats[fs][ost].has_key(label):
                    d = {
                        'name'        : gmond_prefix + fs + '_' + ost + '_' + label,
                        'call_back'   : get_value,
                        'time_max'    : tmax,
                        'value_type'  : 'float',
                        'format'      : '%f',
                        'units'       : descriptions[label]['units'],
                        'slope'       : 'both', # zero|positive|negative|both
                        'description' : descriptions[label]['description'],
                        'groups'      : gmond_group,
                        }
                    # Apply metric customizations from descriptions
                    #d.update(descriptions[label])	
                    descriptors.append(d)
                else:
                    logging.debug(' skipped ' + gmond_prefix + fs + '_' + ost + '_' + label)

                #logging.debug(' descriptors: ' + str(descriptors))

    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

# For testing
if __name__ == '__main__':
    logging.debug('running from cmd line')
    metric_init({})
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print ' %s: %s %s [%s]' % (d['name'], v, d['units'], d['description'])

        print 'Sleeping 15 seconds'
        time.sleep(15)

##############################################################################
# The statistics recorded in osc/*/stats file
# snapshot_time - UNIX epoch instant the stats file was read.
# req_waittime - Amount of time a request waited in the queue before being handled by an available server thread. 
# req_active - Number of requests currently being handled. 
# read_bytes 
# write_bytes 
# ost_read - LUDOC-220 https://jira.hpdd.intel.com/browse/LUDOC-220
#  JH: OST_READ moves some number of bytes from memory on an OST to memory on a client.
#  JH: That number of bytes is used to tally the osc_reads stat.
#  JH: With mmap, a memory access that faults triggers an OST_READ.
#  JH: An access that doesn't fault tallies nothing.
# ost_write 
# ost_setattr
# ost_statfs
# ost_sync
# ost_get_info
# ost_set_info
# ost_connect
# ost_destroy
# ost_punch
# ost_quotactl
# ldlm_cancel
# obd_ping
# 
##############################
# LUDOC-220 https://jira.hpdd.intel.com/browse/LUDOC-220
#
# JH: The osc_read counter from llite should be the sum of all
#  read_bytes stats over all oscs associated to that superblock.
# JH: The ost_read stat is about how long the RPCs took.
#
# AD: your supposition is correct:
#  $ lctl get_param llite.*.stats | grep read
#   read_bytes                1025 samples [bytes] 0 1048576 1073741824
#   osc_read                  1029 samples [bytes] 4096 1048576 1073762304
#  $ lctl get_para osc.*.stats | grep read
#   read_bytes                1029 samples [bytes] 4096 1048576 1073762304 112589999072870
#   ost_read                  1029 samples [usec] 1391 595570 347839127 120942246579015
# AD: llite.*.stats:osc_read == osc.*.stats:read_bytes

##############################################################################
