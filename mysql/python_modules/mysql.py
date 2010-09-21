#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import threading
import time
import traceback
import MySQLdb

descriptors = list()
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

        self.dbuser   = "scott"
        self.dbpasswd = "tiger"
        self.dbhost   = ""
        self.read_default_file  = "/etc/my.cnf"
        self.read_default_group = "client"

        for attr in ("dbuser", "dbpasswd", "dbhost", "read_default_file", "read_default_group"):
            if attr in params:
                setattr(self, attr, params[attr])

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
        conn = None
        try:
            conn = MySQLdb.connect(host=self.dbhost,
                                   user=self.dbuser, passwd=self.dbpasswd,
                                   use_unicode=True, charset="utf8",
                                   read_default_file=self.read_default_file,
                                   read_default_group=self.read_default_group,
                                   )

            my_status = {}

            conn.query("show global status")
            r = conn.store_result()
            while True:
                row = r.fetch_row(1,0)
                if not row:
                    break
                my_status[ row[0][0].lower() ] = int(row[0][1]) if row[0][1].isdigit() else row[0][1]

            conn.query("show table status from oriri like 'health'") # fixme
            r = conn.store_result()
            row = r.fetch_row(1,1)
            my_status["innodb_free"] = float(row[0]["Data_free"])

            self.metric["my_select"] = my_status["com_select"] \
                                     + my_status["qcache_hits"]     \
                                     + my_status["qcache_inserts"]  \
                                     + my_status["qcache_not_cached"]
            self.metric["my_insert"] = my_status["com_insert"] \
                                     + my_status["com_replace"]
            self.metric["my_update"] = my_status["com_update"]
            self.metric["my_delete"] = my_status["com_delete"]

            self.metric["my_qps"]          = my_status["queries"]
            self.metric["my_slow_queries"] = my_status["slow_queries"]

            self.metric["my_threads_connected"] = my_status["threads_connected"]
            self.metric["my_threads_running"]   = my_status["threads_running"]

            self.metric["my_innodb_free"] = my_status["innodb_free"]/1024/1024/1024

            self.metric["my_innodb_buffer_pool_hit"] = \
                100.0 - ( float(my_status["innodb_buffer_pool_reads"]) / float(my_status["innodb_buffer_pool_read_requests"]) * 100.0 )
            self.metric["my_innodb_buffer_pool_dirty_pages"] = \
                ( float(my_status["innodb_buffer_pool_pages_dirty"]) / float(my_status["innodb_buffer_pool_pages_data"]) * 100.0 )
            self.metric["my_innodb_buffer_pool_total"] = \
                float(my_status["innodb_buffer_pool_pages_total"]) * float(my_status["innodb_page_size"]) / 1024/1024/1024
            self.metric["my_innodb_buffer_pool_free"] = \
                float(my_status["innodb_buffer_pool_pages_free"])  * float(my_status["innodb_page_size"]) / 1024/1024/1024

            self.metric["my_qcache_free"] = int(my_status["qcache_free_memory"])

            self.metric["my_key_cache"] = \
                100 - ( float(my_status["key_reads"]) / float(my_status["key_read_requests"]) * 100 )
            self.metric["my_query_cache"] = \
                100 * ( float(my_status["qcache_hits"]) / float(my_status["qcache_inserts"] + my_status["qcache_hits"] + my_status["qcache_not_cached"]) )
            self.metric["my_table_lock_immediate"] = \
                100 * ( float(my_status["table_locks_immediate"]) / float(my_status["table_locks_immediate"] + my_status["table_locks_waited"]) )
            self.metric["my_thread_cache"] = \
                100 - ( float(my_status["threads_created"]) / float(my_status["connections"]) * 100 )
            self.metric["my_tmp_table_on_memory"] = \
                100 * ( float(my_status["created_tmp_tables"]) / float( (my_status["created_tmp_disk_tables"] + my_status["created_tmp_tables"]) or 1 ) )

        except MySQLdb.MySQLError:
            traceback.print_exc()

        finally:
            if conn:
                conn.close()

    def metric_of(self, name):
        val = 0
        if name in self.metric:
            _Lock.acquire()
            val = self.metric[name]
            #print >>sys.stderr, name, val
            _Lock.release()
        return val

def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread

    print '[mysql] mysql'
    print params

    # initialize skeleton of descriptors
    Desc_Skel = {
        "name"        : "XXX",
        "call_back"   : metric_of,
        "time_max"    : 60,
        "value_type"  : "uint",
        "units"       : "XXX",
        "slope"       : "XXX", # zero|positive|negative|both
        "format"      : "%d",
        "description" : "XXX",
        "groups"      : "mysql",
        }

    if "refresh_rate" not in params:
        params["refresh_rate"] = 10

    _Worker_Thread = UpdateMetricThread(params)
    _Worker_Thread.start()
    _Worker_Thread.update_metric()

    # IP:HOSTNAME
    if "spoof_host" in params:
        Desc_Skel["spoof_host"] = params["spoof_host"]

    query_skel = create_desc(Desc_Skel, {
            "name"       : "XXX",
            "units"      : "query/sec",
            "slope"      : "positive",
            "format"     : "%d",
            "description": "XXX",
            })
    descriptors.append(create_desc(query_skel, {
                "name"       : "my_select",
                "description": "SELECT query", }));
    descriptors.append(create_desc(query_skel, {
                "name"       : "my_insert",
                "description": "INSERT query", }));
    descriptors.append(create_desc(query_skel, {
                "name"       : "my_update",
                "description": "UPDATE query", }));
    descriptors.append(create_desc(query_skel, {
                "name"       : "my_delete",
                "description": "DELETE query", }));

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "my_qps",
                "units"      : "q/s",
                "slope"      : "positive",
                "description": "queries per second", }));
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "my_slow_queries",
                "units"      : "queries",
                "slope"      : "both",
                "description": "total number of slow queries", }));

    threads_skel = create_desc(Desc_Skel, {
            "name"       : "XXX",
            "units"      : "threads",
            "slope"      : "both",
            "format"     : "%d",
            "description": "XXX",
            })
    descriptors.append(create_desc(threads_skel, {
                "name"       : "my_threads_connected",
                "description": "threads connected", }));
    descriptors.append(create_desc(threads_skel, {
                "name"       : "my_threads_running",
                "description": "threads running", }));

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "my_innodb_free",
                "value_type" : "float",
                "format"     : "%.3f",
                "units"      : "GB",
                "slope"      : "both",
                "description": "Innodb free area", }));

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "my_innodb_buffer_pool_hit",
                "value_type" : "float",
                "format"     : "%.2f",
                "units"      : "%",
                "slope"      : "both",
                "description": "Innodb buffer pool hit ratio", }));
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "my_innodb_buffer_pool_dirty_pages",
                "value_type" : "float",
                "format"     : "%.2f",
                "units"      : "%",
                "slope"      : "both",
                "description": "Innodb buffer pool dirty pages ratio", }));

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "my_innodb_buffer_pool_total",
                "value_type" : "float",
                "format"     : "%.3f",
                "units"      : "GB",
                "slope"      : "both",
                "description": "Innodb total size of buffer pool", }));
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "my_innodb_buffer_pool_free",
                "value_type" : "float",
                "format"     : "%.3f",
                "units"      : "GB",
                "slope"      : "both",
                "description": "Innodb free size of buffer pool", }));

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "my_qcache_free",
                "value_type" : "uint",
                "format"     : "%d",
                "units"      : "Bytes",
                "slope"      : "both",
                "description": "query cache free area", }));

    ratio_skel = create_desc(Desc_Skel, {
            "name"       : "XXX",
            "units"      : "%",
            "slope"      : "both",
            "value_type" : "float",
            "format"     : "%.2f",
            "description": "XXX",
            })
    descriptors.append(create_desc(ratio_skel, {
                "name"       : "my_key_cache",
                "description": "key cache hit ratio", }));
    descriptors.append(create_desc(ratio_skel, {
                "name"       : "my_query_cache",
                "description": "query cache hit ratio", }));
    descriptors.append(create_desc(ratio_skel, {
                "name"       : "my_table_lock_immediate",
                "description": "table lock immediate ratio", }));
    descriptors.append(create_desc(ratio_skel, {
                "name"       : "my_thread_cache",
                "description": "thread cache ratio", }));
    descriptors.append(create_desc(ratio_skel, {
                "name"       : "my_tmp_table_on_memory",
                "description": "tmp table on memory ratio", }));


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
            'dbuser'      : 'health',
            'dbpasswd'    : '',
            'dbhost'      : 'localhost',
            #'spoof_host'  : '10.10.4.6:db109',
            'refresh_rate': 5,
            }
        metric_init(params)
        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is '+d['format']) % (d['name'],  v)
            print
            time.sleep(5)
    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except StandardError:
        os._exit(1)
