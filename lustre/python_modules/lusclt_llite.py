#!/usr/bin/env python
"""
# collect lustre client metrics from llite stats
# https://build.hpdd.intel.com/job/lustre-manual/lastSuccessfulBuild/artifact/lustre_manual.xhtml#lustreproc.clientstats
#
# based on gmond diskstat python module
# and https://github.com/jthiltges/ganglia-gmond-modules-lustre
#
##  Copyright Chris Hunter, Yale University, 2014
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

#LLITE_DIR= '/tmp/llite'
LLITE_DIR = '/proc/fs/lustre/llite'

#IGNORE_FS
##############################################################################
def get_lus_version():
   '''return lustre version number'''
   fsvers = '/proc/fs/lustre/version'
   logging.debug(' opening file ' + fsvers)

   try:
       fobj = open(fsvers)
   except IOError:
      logging.debug('ERROR opening file ' + fsvers)
      exit()

   #regex split along consecutive whitespace chars
   vals = []
   for line in fobj:
      item = re.split("\s+", line.rstrip())
      vals.append(item)       

   #logging.debug(' vals: ' + str(vals))
   for n in range(len(vals)):
      if 'lustre:' in vals[n]:
         vers_string = vals[n][1]
         #logging.debug(' vers_string: ' + str(vers_string))
         fir = vers_string.find('.')
         sec = vers_string.find('.', fir + 1)
         lus_version = vers_string[0:fir] + '.' + vers_string[fir+1:sec]

   logging.debug(' lus_version: ' + str(lus_version))
   return float(lus_version)

def llite_fs(directory):
    '''return fs names based on folder names in llite directory'''
    for fs in os.listdir(directory):
        fs_name, _, fs_id = fs.partition('-')
        yield fs_name

def get_diff(fs, key, val, convert=1):
    '''return difference between cur_val - last_val, update last_val'''
    global stats, last_val
    if key in last_val[fs]:
        logging.debug(' get_diff for ' + fs + '_' + key + ': ' + str(val) + ' last_val: ' + str(last_val[fs][key]))
    else:
        logging.debug(' get_diff for ' + fs + '_' + key + ': ' + str(val))

    if key in last_val[fs]:
        stats[fs][key] = (val - last_val[fs][key]) * float(convert)
    else:
        stats[fs][key] = 0

    # If for some reason we have a negative diff we should assume counters reset
    # and should set it back to 0
    if stats[fs][key] < 0:
        stats[fs][key] = 0

    last_val[fs][key] = val

def get_delta(fs, key, val, convert=1):
    '''return rate per second from delta of cur_time - last_update, update last_val'''
    global stats, last_val
    if key in last_val[fs]:
        logging.debug(' get_delta for ' + fs +  '_' + key + ': ' + str(val) + ' last_val: ' + str(last_val[fs][key]))
    else:
        logging.debug(' get_delta for ' + fs +  '_' + key + ': ' + str(val))

    if convert == 0:
        logging.warning(' convert is zero!')

    interval = cur_time - last_update

    if key in last_val[fs] and interval > 0:
        stats[fs][key] = (val - last_val[fs][key]) * float(convert) / float(interval)
    else:
        stats[fs][key] = 0

    last_val[fs][key] = val

def get_llite_stats(directory,fs):
    '''read llite stats file, return as nested list'''
    out = []

    for fspath in os.listdir(directory):
        if (fs in fspath):   #substring test
            logging.debug(' opening file ' + str(directory) + '/' + str(fspath) + '/stats')
            try:
                llite_stats = open("%s/%s/stats" % (directory, fspath))
            except IOError:
                llite_stats = []

            for line in llite_stats:
                item = re.split("\s+", line.rstrip())
                out.append(item)
            #logging.debug(' out: ' + str(out))
            return out

def update_stats():
    '''get llite stats, update stats entries'''
    logging.debug(' update_stats')
    global last_update, stats, last_val, cur_time
    global MAX_UPDATE_TIME

    cur_time = time.time()
    if cur_time - last_update < MAX_UPDATE_TIME:
        logging.debug(' skipping update wait ' + str(int(MAX_UPDATE_TIME - (cur_time - last_update))) + ' seconds')
        return True

    ### update stats
    stats = dict()

    stats['total'] = dict()
    stats['total']['file_ops'] = 0
    stats['total']['inode_ops'] = 0

    for fs in llite_fs(LLITE_DIR):
        logging.debug(' fs: ' + fs)
        if fs not in stats:
            stats[fs] = dict()
        if fs not in last_val:
            last_val[fs] = dict()

        vals = []
        vals = get_llite_stats(LLITE_DIR,fs)
        logging.debug(' vals: ' + str(vals))
        stats[fs]['file_ops'] = 0
        stats[fs]['inode_ops'] = 0
        for n in range(len(vals)):
            #LU-333 for lustre < 2.1.0, llite reads stats artificially inflated
            if 'read_bytes' in vals[n]:
                get_delta(fs, 'read_bytes_per_sec', long(vals[n][6]))
                if ('read_bytes_per_sec' in stats['total']):
                    stats['total']['read_bytes_per_sec'] += stats[fs]['read_bytes_per_sec']
                else:
                    stats['total']['read_bytes_per_sec'] = stats[fs]['read_bytes_per_sec']

                get_delta(fs, 'reads', long(vals[n][1]))
                stats[fs]['file_ops'] += stats[fs]['reads']

            if 'write_bytes' in vals[n]:
                get_delta(fs, 'write_bytes_per_sec', long(vals[n][6]))
                if ('write_bytes_per_sec' in stats['total']):
                    stats['total']['write_bytes_per_sec'] += stats[fs]['write_bytes_per_sec']
                else:
                    stats['total']['write_bytes_per_sec'] = stats[fs]['write_bytes_per_sec']

                get_delta(fs, 'writes', long(vals[n][1]))
                stats[fs]['file_ops'] += stats[fs]['writes']

            #if 'brw_read' in vals[n]:
            #    get_delta(fs, 'brw_read', long(vals[n][1]))
            #    get_delta(fs, 'brw_read_bytes_per_sec', long(vals[n][6]))
            #if 'brw_write' in vals[n]:
            #    get_delta(fs, 'brw_write', long(vals[n][1]))
            #    get_delta(fs, 'brw_write_bytes_per_sec', long(vals[n][6]))
            if 'ioctl' in vals[n]:
                get_delta(fs, 'ioctl', long(vals[n][1]))
                stats[fs]['file_ops'] += stats[fs]['ioctl']

            if 'open' in vals[n]:
                get_delta(fs,'ll_open', long(vals[n][1]))
                stats[fs]['file_ops'] += stats[fs]['ll_open']

            if 'close' in vals[n]:
                get_delta(fs,'ll_close', long(vals[n][1]))
                stats[fs]['file_ops'] += stats[fs]['ll_close']

            if 'mmap' in vals[n]:
                get_delta(fs,'mmap', long(vals[n][1]))
                stats[fs]['file_ops'] += stats[fs]['mmap']

            if 'seek' in vals[n]:
                get_delta(fs,'seek', long(vals[n][1]))
                stats[fs]['file_ops'] += stats[fs]['seek']

            if 'fsync' in vals[n]:
                get_delta(fs,'fsync', long(vals[n][1]))
                stats[fs]['file_ops'] += stats[fs]['fsync']

            if 'setattr' in vals[n]:
                get_delta(fs,'ll_setattr', long(vals[n][1]))
                stats[fs]['inode_ops'] += stats[fs]['ll_setattr']

            if 'truncate' in vals[n]:
                get_delta(fs,'truncate', long(vals[n][1]))
                stats[fs]['inode_ops'] += stats[fs]['truncate']

            if 'flock' in vals[n]:
                get_delta(fs,'flock', long(vals[n][1]))
                stats[fs]['inode_ops'] += stats[fs]['flock']

            if 'getattr' in vals[n]:
                get_delta(fs,'ll_getattr', long(vals[n][1]))
                stats[fs]['inode_ops'] += stats[fs]['ll_getattr']

        stats['total']['file_ops'] += stats[fs]['file_ops']
        stats['total']['inode_ops'] += stats[fs]['inode_ops']
    logging.debug(' success refreshing stats')
    logging.debug(' stats: ' + str(stats))
    logging.debug(' last_val: ' + str(last_val))

    last_update = cur_time
    return True

##############################################################################
# The statistics recorded in llite/*/stats file
# snapshot_time - UNIX epoch instant the stats file was read.
# dirty_page_hits - The number of write operations that have been
#   satisfied by the dirty page cache. See Lustre Manual Section 32.4.1,
#   Tuning the Client I/O RPC Stream for more information about dirty
#   cache behavior in a Lustre file system.
# dirty_page_misses - The number of write operations that were not satisfied by the dirty page 
#   cache.
# read_bytes - The number of read operations that have occurred. Three
#   additional parameters are displayed:
#    min    The minimum number of bytes read in a single request since the counter was reset.
#    max    The maximum number of bytes read in a single request since the counter was reset.
#    sum    The accumulated sum of bytes of all read requests since the counter was reset.
# write_bytes - The number of write operations that have occurred. Three
#   additional parameters are displayed:
#    min    The minimum number of bytes written in a single request since the counter was reset.
#    max    The maximum number of bytes written in a single request since the counter was reset.
#    sum    The accumulated sum of bytes of all write requests since the counter was reset.
# brw_read - The number of pages that have been read. Three additional
#   parameters are displayed:
#    min    The minimum number of bytes read in a single block read/write (brw) read request since 
#   the counter was reset.
#    max    The maximum number of bytes read in a single brw read requests since the counter was 
#   reset.
#    sum    The accumulated sum of bytes of all brw read requests since the counter was reset.
# ioctl - The number of combined file and directory ioctl operations.
# open - The number of open operations that have succeeded.
# close - The number of close operations that have succeeded.
# seek - The number of times seek has been called.
# fsync - The number of times fsync has been called.
# truncate - The total number of calls to both locked and lockless truncate.
# setxattr - The number of times extended attributes have been set.
# getxattr - The number of times value(s) of extended attributes have been fetche
##############################################################################
## lustre/llite/lproc_llite.c opcodes
# llite_opcode_table[LPROC_LL_FILE_OPCODES] = {
#       /* file operation */
#       { LPROC_LL_DIRTY_HITS,     LPROCFS_TYPE_REGS, "dirty_pages_hits" },
#       { LPROC_LL_DIRTY_MISSES,   LPROCFS_TYPE_REGS, "dirty_pages_misses" },
#       { LPROC_LL_WB_WRITEPAGE,   LPROCFS_CNTR_AVGMINMAX|LPROCFS_TYPE_PAGES,"writeback_from_writepage" },
#       { LPROC_LL_WB_PRESSURE,    LPROCFS_CNTR_AVGMINMAX|LPROCFS_TYPE_PAGES,"writeback_from_pressure" },
#       { LPROC_LL_WB_OK,          LPROCFS_CNTR_AVGMINMAX|LPROCFS_TYPE_PAGES,"writeback_ok_pages" },
#       { LPROC_LL_WB_FAIL,        LPROCFS_CNTR_AVGMINMAX|LPROCFS_TYPE_PAGES,"writeback_failed_pages" },
#       { LPROC_LL_READ_BYTES,     LPROCFS_CNTR_AVGMINMAX|LPROCFS_TYPE_BYTES,"read_bytes" },
#       { LPROC_LL_WRITE_BYTES,    LPROCFS_CNTR_AVGMINMAX|LPROCFS_TYPE_BYTES,"write_bytes" },
#       { LPROC_LL_BRW_READ,       LPROCFS_CNTR_AVGMINMAX|LPROCFS_TYPE_PAGES,"brw_read" },
#       { LPROC_LL_BRW_WRITE,      LPROCFS_CNTR_AVGMINMAX|LPROCFS_TYPE_PAGES,"brw_write" },
#       { LPROC_LL_IOCTL,          LPROCFS_TYPE_REGS, "ioctl" },
#       { LPROC_LL_OPEN,           LPROCFS_TYPE_REGS, "open" },
#       { LPROC_LL_RELEASE,        LPROCFS_TYPE_REGS, "close" },
#       { LPROC_LL_MAP,            LPROCFS_TYPE_REGS, "mmap" },
#       { LPROC_LL_LLSEEK,         LPROCFS_TYPE_REGS, "seek" },
#       { LPROC_LL_FSYNC,          LPROCFS_TYPE_REGS, "fsync" },
#       /* inode operation */
#       { LPROC_LL_SETATTR,        LPROCFS_TYPE_REGS, "setattr" },
#       { LPROC_LL_TRUNC,          LPROCFS_TYPE_REGS, "truncate" },
#       { LPROC_LL_LOCKLESS_TRUNC, LPROCFS_TYPE_REGS, "lockless_truncate"},
#       { LPROC_LL_FLOCK,          LPROCFS_TYPE_REGS, "flock" },
#       { LPROC_LL_GETATTR,        LPROCFS_TYPE_REGS, "getattr" },
#       /* special inode operation */
#       { LPROC_LL_STAFS,          LPROCFS_TYPE_REGS, "statfs" },
#       { LPROC_LL_ALLOC_INODE,    LPROCFS_TYPE_REGS, "alloc_inode" },
#       { LPROC_LL_SETXATTR,       LPROCFS_TYPE_REGS, "setxattr" },
#       { LPROC_LL_GETXATTR,       LPROCFS_TYPE_REGS, "getxattr" },
#       { LPROC_LL_LISTXATTR,      LPROCFS_TYPE_REGS, "listxattr" },
#       { LPROC_LL_REMOVEXATTR,    LPROCFS_TYPE_REGS, "removexattr" },
#       { LPROC_LL_INODE_PERM,     LPROCFS_TYPE_REGS, "inode_permission" },
#       { LPROC_LL_DIRECT_READ,    LPROCFS_CNTR_AVGMINMAX|LPROCFS_TYPE_PAGES,"direct_read" },
#       { LPROC_LL_DIRECT_WRITE,   LPROCFS_CNTR_AVGMINMAX|LPROCFS_TYPE_PAGES,"direct_write" },
#       { LPROC_LL_LOCKLESS_READ,  LPROCFS_CNTR_AVGMINMAX|LPROCFS_TYPE_BYTES,"lockless_read_bytes" },
#       { LPROC_LL_LOCKLESS_WRITE, LPROCFS_CNTR_AVGMINMAX|LPROCFS_TYPE_BYTES,"lockless_write_bytes" },
#};
##############################################################################
def get_value(metric):
    '''get value for name format: gmond_prefix_ + fs_ + metric'''
    logging.debug(' getting value: ' + metric)
    global stats

    ret = update_stats()

    if ret:
        if metric.startswith(gmond_prefix):
            fir = metric.find('_')
            sec = metric.find('_', fir + 1)
            fs = metric[fir+1:sec]
            label = metric[sec+1:]

            try:
                return stats[fs][label]
            except:
                logging.warning('failed to fetch [' + fs + '] ' + metric)
                return 0
            else:
                label = metric
                try:
                    return stats[label]
                except:
                    logging.warning('failed to fetch ' + metric)
                    return 0
    else:
        return 0

def metric_init(params):
    '''initialize descriptor data structure and call update_stats'''
    global descriptors
    logging.debug('metric_init: ' + str(params))

    descriptions = dict(
        dirty_page_hits = {
            'units'       : 'hits/s',
            'description' : 'dirty page hits'},
        dirty_page_misses = {
            'units'       : 'misses/s',
            'description' : 'dirty page misses'},
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
        brw_read = {
            'units': 'pages/s',
            'description': 'brw_read pages'},
        brw_read_bytes_per_sec = {
            'units': 'bytes/s',
            'description': 'brw_read bytes/sec'},
        brw_write = {
            'units': 'pages/s',
            'description': 'brw_write pages'},
        brw_write_bytes_per_sec = {
            'units': 'bytes/s',
            'description': 'brw_write bytes/sec'},
        ioctl = {
            'units'       : 'calls/s',
            'description' : 'ioctl calls'},
        ll_open = {
            'units'       : 'calls/s',
            'description' : 'open calls'},
        ll_close = { 
            'units'       : 'calls/s',
            'description' : 'close calls'},
        mmap = {
            'units'       : 'calls/s',
            'description' : 'mmap calls'},
        seek = {
            'units'       : 'calls/s',
            'description' : 'seek calls'},
        fsync = {
            'units'       : 'calls/s',
            'description' : 'fsync calls'},
        file_ops = {
            'units'       : 'calls/s',
            'description' : 'filedata calls'},
        #       /* inode operation */
        ll_setattr = {
            'units'       : 'calls/s',
            'description' : 'setattr calls'},
        truncate = {
            'units'       : 'calls/s',
            'description' : 'truncate calls'},
        lockless_truncate = {
            'units'       : 'calls/s',
            'description' : 'lockless_truncate calls'},
        flock = {
            'units'       : 'calls/s',
            'description' : 'flock calls'},
        ll_getattr = {
            'units'       : 'calls/s',
            'description' : 'getattr calls'},
        #       /* special inode operation */
        statfs = {
            'units'       : 'calls/s',
            'description' : 'statfs calls'},
        alloc_inode = {
            'units'       : 'calls/s',
            'description' : 'alloc_inode calls'},
        setxattr = {
            'units'       : 'calls/s',
            'description' : 'setxattr calls'},
        getxattr = {
            'units'       : 'calls/s',
            'description' : 'getxattr calls'},
        listxattr = {
            'units'       : 'calls/s',
            'description' : 'listxattr calls'},
        removeattr = {
            'units'       : 'calls/s',
            'description' : 'removeattr calls'},
        inode_permission = {
            'units'       : 'calls/s',
            'description' : 'inode_permission calls'},
        inode_ops = {
            'units'       : 'calls/s',
            'description' : 'metadata calls'},
        direct_read = {
            'units': 'req/s',
            'description': 'DIO read requests'},
        direct_read_bytes_per_sec = {
            'units': 'bytes/sec',
            'description': 'DIO read bytes/sec'},
        direct_write = {
            'units': 'req/s',
            'description': 'DIO write requests'},
        direct_write_bytes_per_sec = {
            'units': 'bytes/sec',
            'description': 'DIO write bytes/sec'},
        lockless_read = {
            'units': 'req/s',
            'description': 'lockless read requests'},
        lockless_read_bytes_per_sec = {
            'units': 'bytes/sec',
            'description': 'lockless read bytes/sec'},
        lockless_write = {
            'units': 'req/s',
            'description': 'DIO write requests'},
        lockless_write_bytes_per_sec = {
            'units': 'bytes/sec',
            'description': 'lockless write bytes/sec'},
    )
    logging.debug('descriptions: ' + str(descriptions))

    update_stats()

    fslist = list(llite_fs(LLITE_DIR))
    print type(fslist),str(fslist)
    fslist.append('total')
    for label in descriptions:
        for fs in fslist:
            if stats[fs].has_key(label):
                d = {
                    'name'        : gmond_prefix + fs + '_' + label,
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
                logging.debug(' skipped ' + gmond_prefix + fs + '_' + label)

    logging.debug(' descriptors: ' + str(descriptors))

    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

# For testing
if __name__ == '__main__':
    logging.debug('running from cmd line')
    # check lustre version number
    version_num = get_lus_version()
    if version_num <= 2.2:
       print 'WARNING older lustre llite stats have bugs (eg. LU-333), recommend using version 2.4 or newer.' 
       print 'Alternatively use lustre osc stats to gather metrics'
       try:
          input = raw_input('Press Enter to continue')
       except EOFError:
          pass
    
    metric_init({})
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print ' %s: %s %s [%s]' % (d['name'], v, d['units'], d['description'])

        print 'Sleeping 15 seconds'
        time.sleep(15)

##############################################################################
## Example llite stats file:
# snapshot_time             1413916626.38038 secs.usecs
# dirty_pages_hits          1153104073 samples [regs]
# dirty_pages_misses        24106860852 samples [regs]
# read_bytes                5188558413 samples [bytes] 1 18874368 1271164760881392
# write_bytes               1795805569 samples [bytes] 0 6291456 98709392849888
# brw_read                  3807381 samples [pages] 4096 4096 15595032576
# ioctl                     188616 samples [regs]
# open                      54694519 samples [regs]
# close                     55489004 samples [regs]
# mmap                      64898 samples [regs]
# seek                      13405025637 samples [regs]
# fsync                     1230 samples [regs]
# setattr                   2122882 samples [regs]
# truncate                  14823 samples [regs]
# getattr                   178422160 samples [regs]
# statfs                    39 samples [regs]
# alloc_inode               11994241 samples [regs]
# setxattr                  401 samples [regs]
# getxattr                  1843750871 samples [regs]
# listxattr                 32 samples [regs]
# removexattr               596 samples [regs]
# inode_permission          492967435 samples [regs]
