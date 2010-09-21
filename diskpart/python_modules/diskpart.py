#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import threading
import time

descriptors = list()
mount_points = list()
Desc_Skel   = {}
_Worker_Thread = None
_Lock = threading.Lock() # synchronization lock

class UpdateMetricThread(threading.Thread):

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running      = False
        self.shuttingdown = False
        self.refresh_rate = 10
        if "refresh_rate" in params:
            self.refresh_rate = int(params["refresh_rate"])
        self.metric       = {}

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        self.running = True

        while not self.shuttingdown:
            _Lock.acquire()
            self.update_metric()
            _Lock.release()
            time.sleep(self.refresh_rate)

        self.running = False

    def update_metric(self):
        for mtp in mount_points:
            #print >>sys.stderr, "mtp: ", mtp
            st = os.statvfs(mtp)
            if mtp == "/":
                part = "diskpart-root"
            else:
                part = "diskpart-" + mtp.replace('/', '_').lstrip('_')
            #print >>sys.stderr, "%u %u %u" % (st.f_blocks, st.f_bavail, st.f_bsize)
            self.metric[ part+"-total" ] = float(st.f_blocks * st.f_bsize) / 1024/1024/1024
            self.metric[ part+"-used"  ] = float((st.f_blocks - st.f_bavail) * st.f_bsize) / 1024/1024/1024

            self.metric[ part+"-inode-total" ] = st.f_files
            self.metric[ part+"-inode-used"  ] = st.f_files - st.f_favail


    def metric_of(self, name):
        val = 0
        if name in self.metric:
            _Lock.acquire()
            val = self.metric[name]
            _Lock.release()
        return val

def is_remotefs(dev, type):
    if dev.find(":") >= 0:
        return True
    elif dev.startswith("//") and (type == "smbfs" or type == "cifs"):
        return True
    return False

def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread, mount_points

    print '[diskpart] diskpart'
    print params

    # initialize skeleton of descriptors
    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : metric_of,
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%.3f',
        'units'       : 'GB',
        'slope'       : 'both',
        'description' : 'XXX',
        'groups'      : 'disk',
        }

    if "refresh_rate" not in params:
        params["refresh_rate"] = 10

    # IP:HOSTNAME
    if "spoof_host" in params:
        Desc_Skel["spoof_host"] = params["spoof_host"]

    f = open("/proc/mounts", "r")
    # 0         1     2    3
    # /dev/sda4 /home ext3 rw,relatime,errors=continue,data=writeback 0 0
    for l in f:
        (dev, mtp, fstype, opt) = l.split(None, 3)
        if is_remotefs(dev, fstype):
            continue
        elif opt.startswith('ro'):
            continue
        elif not dev.startswith('/dev/') \
          and not (mtp == "/" and fstype == "tmpfs"): # for netboot
            continue;

        if mtp == "/":
            part = "diskpart-root"
        else:
            part = "diskpart-" + mtp.replace('/', '_').lstrip('_')
        #print >>sys.stderr, "dev=%s mount_point=%s part=%s" % (dev, mtp, part)

        descriptors.append(create_desc(Desc_Skel, {
                    "name"       : part + "-total",
                    "description": "total partition space",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"       : part + "-used",
                    "description": "partition space used",
                    }))

        descriptors.append(create_desc(Desc_Skel, {
                    "name"       : part + "-inode-total",
                    "description": "total number of inode",
                    "value_type" : "uint",
                    "format"     : "%d",
                    "units"      : "inode",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"       : part + "-inode-used",
                    "description": "total number of inode used",
                    "value_type" : "uint",
                    "format"     : "%d",
                    "units"      : "inode",
                    }))

        mount_points.append(mtp)

    _Worker_Thread = UpdateMetricThread(params)
    _Worker_Thread.start()

    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_of(name):
    return _Worker_Thread.metric_of(name)

def metric_cleanup():
    _Worker_Thread.shutdown()

if __name__ == '__main__':
    try:
        params = {
            }
        metric_init(params)
        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is '+d['format']) % (d['name'],  v)
            time.sleep(5)
    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except:
        print sys.exc_info()[0]
        raise

