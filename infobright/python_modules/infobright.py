"""
The MIT License

Copyright (c) 2008 Gilad Raphaelli <gilad@raphaelli.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

###  Changelog:
###    v1.0.0 - 2012-05-18
###       * Brighthouse columnar database "Infobright" module, derived from mysqld module
###

###  Requires:
###       * yum install Infobright-python

###  Copyright Bob Webber, 2012
###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt

import time
import MySQLdb
import logging

descriptors = []

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/infobrightstats.log', filemode='w')
logging.debug('starting up')

last_update = 0
infobright_conn_opts = {}
infobright_stats = {}
infobright_stats_last = {}
delta_per_second = False

REPORT_BRIGHTHOUSE = True
REPORT_BRIGHTHOUSE_ENGINE = False
REPORT_MASTER = True
REPORT_SLAVE  = True

MAX_UPDATE_TIME = 15

def update_stats(get_brighthouse=True, get_brighthouse_engine=True, get_master=True, get_slave=True):
	"""

	"""
	logging.debug('updating stats')
	global last_update
	global infobright_stats, infobright_stats_last

	cur_time = time.time()
	time_delta = cur_time - last_update
	if time_delta <= 0:
		#we went backward in time.
		logging.debug(" system clock set backwards, probably ntp")

	if cur_time - last_update < MAX_UPDATE_TIME:
		logging.debug(' wait ' + str(int(MAX_UPDATE_TIME - (cur_time - last_update))) + ' seconds')
		return True
	else:
		last_update = cur_time

	logging.debug('refreshing stats')
	infobright_stats = {}

	# Get info from DB
	try:
		conn = MySQLdb.connect(**infobright_conn_opts)

		cursor = conn.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute("SELECT GET_LOCK('gmetric-infobright', 0) as ok")
		lock_stat = cursor.fetchone()
		cursor.close()

		if lock_stat['ok'] == 0:
			return False

		# infobright variables have 'brighthouse_ib_' or 'brighthouse_ini_' prefix
		cursor = conn.cursor(MySQLdb.cursors.Cursor)
		cursor.execute("SHOW VARIABLES")
		#variables = dict(((k.lower(), v) for (k,v) in cursor))
		variables = {}
		for (k,v) in cursor:
			variables[k.lower()] = v
		cursor.close()

		# infobright status values have 'bh_gdc_' or 'bh_mm_' prefix
		cursor = conn.cursor(MySQLdb.cursors.Cursor)
		# cursor.execute("SHOW /*!50002 GLOBAL */ STATUS")
		cursor.execute("SHOW GLOBAL STATUS")
		#global_status = dict(((k.lower(), v) for (k,v) in cursor))
		global_status = {}
		for (k,v) in cursor:
			# print k, v
			global_status[k.lower()] = v
		cursor.close()

		# try not to fail ?
		# BRIGHTHOUSE ENGINE status variables are pretty obscure
		get_brighthouse_engine = get_brighthouse_engine and variables.has_key('brighthouse_ini_controlmessages')
		get_master = get_master and variables['log_bin'].lower() == 'on'

		if get_brighthouse_engine:
			logging.warn('get_brighthouse_engine status not implemented')
			
		master_logs = tuple
		if get_master:
			cursor = conn.cursor(MySQLdb.cursors.Cursor)
			cursor.execute("SHOW MASTER LOGS")
			master_logs = cursor.fetchall()
			cursor.close()

		slave_status = {}
		if get_slave:
			cursor = conn.cursor(MySQLdb.cursors.DictCursor)
			cursor.execute("SHOW SLAVE STATUS")
			res = cursor.fetchone()
			if res:
				for (k,v) in res.items():
					slave_status[k.lower()] = v
			else:
				get_slave = False
			cursor.close()

		cursor = conn.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute("SELECT RELEASE_LOCK('gmetric-infobright') as ok")
		cursor.close()

		conn.close()
	except MySQLdb.OperationalError, (errno, errmsg):
		logging.error('error updating stats')
		logging.error(errmsg)
		return False

	# process variables
	# http://dev.infobright.com/doc/refman/5.0/en/server-system-variables.html
	infobright_stats['version'] = variables['version']
	infobright_stats['max_connections'] = variables['max_connections']
	infobright_stats['query_cache_size'] = variables['query_cache_size']

	# process mysql status
	# http://www.infobright.com/
	interesting_mysql_status_vars = (
		'aborted_clients',
		'aborted_connects',
		'binlog_cache_disk_use',
		'binlog_cache_use',
		'bytes_received',
		'bytes_sent',
		'com_delete',
		'com_delete_multi',
		'com_insert',
		'com_insert_select',
		'com_load',
		'com_replace',
		'com_replace_select',
		'com_select',
		'com_update',
		'com_update_multi',
		'connections',
		'created_tmp_disk_tables',
		'created_tmp_files',
		'created_tmp_tables',
		'key_reads',
		'key_read_requests',
		'key_writes',
		'key_write_requests',
		'max_used_connections',
		'open_files',
		'open_tables',
		'opened_tables',
		'qcache_free_blocks',
		'qcache_free_memory',
		'qcache_hits',
		'qcache_inserts',
		'qcache_lowmem_prunes',
		'qcache_not_cached',
		'qcache_queries_in_cache',
		'qcache_total_blocks',
		'questions',
		'select_full_join',
		'select_full_range_join',
		'select_range',
		'select_range_check',
		'select_scan',
		'slave_open_temp_tables',
		'slave_retried_transactions',
		'slow_launch_threads',
		'slow_queries',
		'sort_range',
		'sort_rows',
		'sort_scan',
		'table_locks_immediate',
		'table_locks_waited',
		'threads_cached',
		'threads_connected',
		'threads_created',
		'threads_running',
		'uptime',
	)

	non_delta_mysql_status_vars = (
		'max_used_connections',
		'open_files',
		'open_tables',
		'qcache_free_blocks',
		'qcache_free_memory',
		'qcache_total_blocks',
		'slave_open_temp_tables',
		'threads_cached',
		'threads_connected',
		'threads_running',
		'uptime'
	)
	
	interesting_brighthouse_status_vars = (
		'bh_gdc_false_wakeup',
		'bh_gdc_hits',
		'bh_gdc_load_errors',
		'bh_gdc_misses',
		'bh_gdc_pack_loads',
		'bh_gdc_prefetched',
		'bh_gdc_readwait',
		'bh_gdc_read_wait_in_progress',
		'bh_gdc_redecompress',
		'bh_gdc_released',
		'bh_gdc_released',
		'bh_mm_alloc_blocs',
		'bh_mm_alloc_objs',
		'bh_mm_alloc_pack_size',
		'bh_mm_alloc_packs',
		'bh_mm_alloc_size',
		'bh_mm_alloc_temp',
		'bh_mm_alloc_temp_size',
		'bh_mm_free_blocks',
		'bh_mm_free_pack_size',
		'bh_mm_free_packs',
		'bh_mm_free_size',
		'bh_mm_free_temp',
		'bh_mm_free_temp_size',
		'bh_mm_freeable',
		'bh_mm_release1',
		'bh_mm_release2',
		'bh_mm_release3',
		'bh_mm_release4',
		'bh_mm_reloaded',
		'bh_mm_scale',
		'bh_mm_unfreeable',
		'bh_readbytes',
		'bh_readcount',
		'bh_writebytes',
		'bh_writecount',
	)
	
	non_delta_brighthouse_status_vars = (
		'bh_gdc_read_wait_in_progress',
		'bh_mm_alloc_size',
		'bh_mm_alloc_temp_size',
		'bh_mm_free_pack_size',
		'bh_mm_scale',
	)

	# don't put all of global_status in infobright_stats b/c it's so big
	all_interesting_status_vars = interesting_mysql_status_vars + interesting_brighthouse_status_vars
	all_non_delta_status_vars = non_delta_mysql_status_vars + non_delta_brighthouse_status_vars
	for key in all_interesting_status_vars:
		if key in all_non_delta_status_vars:
			infobright_stats[key] = global_status[key]
		else:
			# Calculate deltas for counters
			if time_delta <= 0:
				#systemclock was set backwards, not updating values.. to smooth over the graphs
				pass
			elif key in infobright_stats_last:
				if delta_per_second:
					infobright_stats[key] = (int(global_status[key]) - int(infobright_stats_last[key])) / time_delta
				else:
					infobright_stats[key] = int(global_status[key]) - int(infobright_stats_last[key])
			else:
				infobright_stats[key] = float(0)
			infobright_stats_last[key] = global_status[key]

	infobright_stats['open_files_used'] = int(global_status['open_files']) / int(variables['open_files_limit'])

	# process master logs
	if get_master:
		infobright_stats['binlog_count'] = len(master_logs)
		infobright_stats['binlog_space_current'] = master_logs[-1][1]
		#infobright_stats['binlog_space_total'] = sum((long(s[1]) for s in master_logs))
		infobright_stats['binlog_space_total'] = 0
		for s in master_logs:
			infobright_stats['binlog_space_total'] += int(s[1])
		infobright_stats['binlog_space_used'] = float(master_logs[-1][1]) / float(variables['max_binlog_size']) * 100

	# process slave status
	if get_slave:
		infobright_stats['slave_exec_master_log_pos'] = slave_status['exec_master_log_pos']
		#infobright_stats['slave_io'] = 1 if slave_status['slave_io_running'].lower() == "yes" else 0
		if slave_status['slave_io_running'].lower() == "yes":
			infobright_stats['slave_io'] = 1
		else:
			infobright_stats['slave_io'] = 0
		#infobright_stats['slave_sql'] = 1 if slave_status['slave_sql_running'].lower() =="yes" else 0
		if slave_status['slave_sql_running'].lower() == "yes":
			infobright_stats['slave_sql'] = 1
		else:
			infobright_stats['slave_sql'] = 0
		infobright_stats['slave_lag'] = slave_status['seconds_behind_master']
		infobright_stats['slave_relay_log_pos'] = slave_status['relay_log_pos']
		infobright_stats['slave_relay_log_space'] = slave_status['relay_log_space']


	logging.debug('success updating stats')
	logging.debug('infobright_stats: ' + str(infobright_stats))

def get_stat(name):
	logging.info("getting stat: %s" % name)
	global infobright_stats
	#logging.debug(infobright_stats)

	global REPORT_BRIGHTHOUSE
	global REPORT_BRIGHTHOUSE_ENGINE
	global REPORT_MASTER
	global REPORT_SLAVE

	ret = update_stats(REPORT_BRIGHTHOUSE, REPORT_BRIGHTHOUSE_ENGINE, REPORT_MASTER, REPORT_SLAVE)

	if ret:
		if name.startswith('infobright_'):
			# note that offset depends on length of "startswith"
			label = name[11:]
		else:
			label = name

		logging.debug("fetching %s" % name)
		try:
			return infobright_stats[label]
		except:
			logging.error("failed to fetch %s" % name)
			return 0
	else:
		return 0

def metric_init(params):
	global descriptors
	global infobright_conn_opts
	global infobright_stats
	global delta_per_second

	global REPORT_BRIGHTHOUSE
	global REPORT_BRIGHTHOUSE_ENGINE
	global REPORT_MASTER
	global REPORT_SLAVE

	REPORT_BRIGHTHOUSE = str(params.get('get_brighthouse', True)) == "True"
	REPORT_BRIGHTHOUSE_ENGINE = str(params.get('get_brighthouse_engine', True)) == "True"
	REPORT_MASTER = str(params.get('get_master', True)) == "True"
	REPORT_SLAVE  = str(params.get('get_slave', True)) == "True"

	logging.debug("init: " + str(params))

	infobright_conn_opts = dict(
		user = params.get('user'),
		passwd = params.get('passwd'),
		unix_socket = params.get('unix_socket', '/tmp/mysql-ib.sock'),
		connect_timeout = params.get('timeout', 30),
	)
	if params.get('host', '') != '':
		infobright_conn_opts['host'] = params.get('host')

	if params.get('port', 5029) != 5029:
		infobright_conn_opts['port'] = params.get('port')

	if params.get("delta_per_second", '') != '':
		delta_per_second = True

	mysql_stats_descriptions = {}
	master_stats_descriptions = {}
 	brighthouse_stats_descriptions = {}
	slave_stats_descriptions  = {}

	mysql_stats_descriptions = dict(
		aborted_clients = {
			'description': 'The number of connections that were aborted because the client died without closing the connection properly',
			'value_type': 'float',
			'units': 'clients',
		}, 

		aborted_connects = {
			'description': 'The number of failed attempts to connect to the Infobright server',
			'value_type': 'float',
			'units': 'conns',
		}, 

		binlog_cache_disk_use = {
			'description': 'The number of transactions that used the temporary binary log cache but that exceeded the value of binlog_cache_size and used a temporary file to store statements from the transaction',
			'value_type': 'float',
			'units': 'txns',
		}, 

		binlog_cache_use = {
			'description': ' The number of transactions that used the temporary binary log cache',
			'value_type': 'float',
			'units': 'txns',
		}, 

		bytes_received = {
			'description': 'The number of bytes received from all clients',
			'value_type': 'float',
			'units': 'bytes',
		}, 

		bytes_sent = {
			'description': ' The number of bytes sent to all clients',
			'value_type': 'float',
			'units': 'bytes',
		}, 

		com_delete = {
			'description': 'The number of DELETE statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_delete_multi = {
			'description': 'The number of multi-table DELETE statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_insert = {
			'description': 'The number of INSERT statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_insert_select = {
			'description': 'The number of INSERT ... SELECT statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_load = {
			'description': 'The number of LOAD statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_replace = {
			'description': 'The number of REPLACE statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_replace_select = {
			'description': 'The number of REPLACE ... SELECT statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_select = {
			'description': 'The number of SELECT statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_update = {
			'description': 'The number of UPDATE statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_update_multi = {
			'description': 'The number of multi-table UPDATE statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		connections = {
			'description': 'The number of connection attempts (successful or not) to the Infobright server',
			'value_type': 'float',
			'units': 'conns',
		}, 

		created_tmp_disk_tables = {
			'description': 'The number of temporary tables on disk created automatically by the server while executing statements',
			'value_type': 'float',
			'units': 'tables',
		}, 

		created_tmp_files = {
			'description': 'The number of temporary files Infobrights mysqld has created',
			'value_type': 'float',
			'units': 'files',
		}, 

		created_tmp_tables = {
			'description': 'The number of in-memory temporary tables created automatically by the server while executing statement',
			'value_type': 'float',
			'units': 'tables',
		}, 

		#TODO in graphs: key_read_cache_miss_rate = key_reads / key_read_requests

		key_read_requests = {
			'description': 'The number of requests to read a key block from the cache',
			'value_type': 'float',
			'units': 'reqs',
		}, 

		key_reads = {
			'description': 'The number of physical reads of a key block from disk',
			'value_type': 'float',
			'units': 'reads',
		}, 

		key_write_requests = {
			'description': 'The number of requests to write a key block to the cache',
			'value_type': 'float',
			'units': 'reqs',
		}, 

		key_writes = {
			'description': 'The number of physical writes of a key block to disk',
			'value_type': 'float',
			'units': 'writes',
		}, 

		max_used_connections = {
			'description': 'The maximum number of connections that have been in use simultaneously since the server started',
			'units': 'conns',
			'slope': 'both',
		}, 

		open_files = {
			'description': 'The number of files that are open',
			'units': 'files',
			'slope': 'both',
		}, 

		open_tables = {
			'description': 'The number of tables that are open',
			'units': 'tables',
			'slope': 'both',
		}, 

		# If Opened_tables is big, your table_cache value is probably too small. 
		opened_tables = {
			'description': 'The number of tables that have been opened',
			'value_type': 'float',
			'units': 'tables',
		}, 

		qcache_free_blocks = {
			'description': 'The number of free memory blocks in the query cache',
			'units': 'blocks',
			'slope': 'both',
		}, 

		qcache_free_memory = {
			'description': 'The amount of free memory for the query cache',
			'units': 'bytes',
			'slope': 'both',
		}, 

		qcache_hits = {
			'description': 'The number of query cache hits',
			'value_type': 'float',
			'units': 'hits',
		}, 

		qcache_inserts = {
			'description': 'The number of queries added to the query cache',
			'value_type': 'float',
			'units': 'queries',
		}, 

		qcache_lowmem_prunes = {
			'description': 'The number of queries that were deleted from the query cache because of low memory',
			'value_type': 'float',
			'units': 'queries',
		}, 

		qcache_not_cached = {
			'description': 'The number of non-cached queries (not cacheable, or not cached due to the query_cache_type setting)',
			'value_type': 'float',
			'units': 'queries',
		}, 

		qcache_queries_in_cache = {
			'description': 'The number of queries registered in the query cache',
			'value_type': 'float',
			'units': 'queries',
		}, 

		qcache_total_blocks = {
			'description': 'The total number of blocks in the query cache',
			'units': 'blocks',
		}, 

		questions = {
			'description': 'The number of statements that clients have sent to the server',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		# If this value is not 0, you should carefully check the indexes of your tables.
		select_full_join = {
			'description': 'The number of joins that perform table scans because they do not use indexes',
			'value_type': 'float',
			'units': 'joins',
		}, 

		select_full_range_join = {
			'description': 'The number of joins that used a range search on a reference table',
			'value_type': 'float',
			'units': 'joins',
		}, 

		select_range = {
			'description': 'The number of joins that used ranges on the first table',
			'value_type': 'float',
			'units': 'joins',
		}, 

		# If this is not 0, you should carefully check the indexes of your tables.
		select_range_check = {
			'description': 'The number of joins without keys that check for key usage after each row',
			'value_type': 'float',
			'units': 'joins',
		}, 

		select_scan = {
			'description': 'The number of joins that did a full scan of the first table',
			'value_type': 'float',
			'units': 'joins',
		}, 

		slave_open_temp_tables = {
			'description': 'The number of temporary tables that the slave SQL thread currently has open',
			'value_type': 'float',
			'units': 'tables',
			'slope': 'both',
		}, 

		slave_retried_transactions = {
			'description': 'The total number of times since startup that the replication slave SQL thread has retried transactions',
			'value_type': 'float',
			'units': 'count',
		}, 

		slow_launch_threads = {
			'description': 'The number of threads that have taken more than slow_launch_time seconds to create',
			'value_type': 'float',
			'units': 'threads',
		}, 

		slow_queries = {
			'description': 'The number of queries that have taken more than long_query_time seconds',
			'value_type': 'float',
			'units': 'queries',
		}, 

		sort_range = {
			'description': 'The number of sorts that were done using ranges',
			'value_type': 'float',
			'units': 'sorts',
		}, 

		sort_rows = {
			'description': 'The number of sorted rows',
			'value_type': 'float',
			'units': 'rows',
		}, 

		sort_scan = {
			'description': 'The number of sorts that were done by scanning the table',
			'value_type': 'float',
			'units': 'sorts',
		}, 

		table_locks_immediate = {
			'description': 'The number of times that a request for a table lock could be granted immediately',
			'value_type': 'float',
			'units': 'count',
		}, 

		# If this is high and you have performance problems, you should first optimize your queries, and then either split your table or tables or use replication.
		table_locks_waited = {
			'description': 'The number of times that a request for a table lock could not be granted immediately and a wait was needed',
			'value_type': 'float',
			'units': 'count',
		}, 

		threads_cached = {
			'description': 'The number of threads in the thread cache',
			'units': 'threads',
			'slope': 'both',
		}, 

		threads_connected = {
			'description': 'The number of currently open connections',
			'units': 'threads',
			'slope': 'both',
		}, 

		#TODO in graphs: The cache miss rate can be calculated as Threads_created/Connections

		# Threads_created is big, you may want to increase the thread_cache_size value. 
		threads_created = {
			'description': 'The number of threads created to handle connections',
			'value_type': 'float',
			'units': 'threads',
		}, 

		threads_running = {
			'description': 'The number of threads that are not sleeping',
			'units': 'threads',
			'slope': 'both',
		}, 

		uptime = {
			'description': 'The number of seconds that the server has been up',
			'units': 'secs',
			'slope': 'both',
		}, 

		version = {
			'description': "Infobright uses MySQL Version",
			'value_type': 'string',
		    'format': '%s',
		},

		max_connections = {
			'description': "The maximum permitted number of simultaneous client connections",
			'slope': 'zero',
		},

		query_cache_size = {
			'description': "The amount of memory allocated for caching query results",
			'slope': 'zero',
		},
 	)
 	
 	brighthouse_stats_descriptions = dict(
 		bh_gdc_read_wait_in_progress = {
 			'description': "The number of current read waits in Brighthouse tables.",
 			'slope': 'zero',
 		},
 
		bh_mm_alloc_size = {
			'description': "The Brighthouse memory allocation size.",
			'slope': 'zero',
		},
		
		bh_mm_alloc_temp_size = {
			'description': "Brighthouse memory allocation temp size.",
			'slope': 'zero',
		},
		
		bh_mm_free_pack_size = {
			'description': "Brighthouse memory free pack size.",
			'slope': 'zero',
		},
		
		bh_mm_scale = {
			'description': "Brighthouse memory scale.",
			'slope': 'zero',
		},

		bh_gdc_false_wakeup = {
			'description': "BrightHouse gdc false wakeup",
			'value_type':'float',
			'units': 'fwkups',
			'slope': 'both',
		},
		bh_gdc_hits = {
			'description': "BrightHouse gdc hits",
			'value_type':'float',
			'units': 'hits',
			'slope': 'both',
		},
		bh_gdc_load_errors = {
			'description': "BrightHouse gdc load errors",
			'value_type':'float',
			'units': 'lderrs',
			'slope': 'both',
		},
		bh_gdc_misses = {
			'description': "BrightHouse gdc misses",
			'value_type':'float',
			'units': 'misses',
			'slope': 'both',
		},
		bh_gdc_pack_loads = {
			'description': "BrightHouse gdc pack loads",
			'value_type':'float',
			'units': 'pklds',
			'slope': 'both',
		},
		bh_gdc_prefetched  = {
			'description': "BrightHouse gdc prefetched",
			'value_type':'float',
			'units': 'prftchs',
			'slope': 'both',
		},
# 		bh_gdc_read_wait_in_progress = {
# 			'description': "BrightHouse gdc in read wait",
# 			'value_type':'uint',
# 			'units': 'inrdwt',
# 			'slope': 'both',
# 		},
		bh_gdc_readwait = {
			'description': "BrightHouse gdc read waits",
			'value_type':'float',
			'units': 'rdwts',
			'slope': 'both',
		},
		bh_gdc_redecompress = {
			'description': "BrightHouse gdc redecompress",
			'value_type':'float',
			'units': 'rdcmprs',
			'slope': 'both',
		},
		bh_gdc_released = {
			'description': "BrightHouse gdc released",
			'value_type':'float',
			'units': 'rlss',
			'slope': 'both',
		},
		bh_mm_alloc_blocs = {
			'description': "BrightHouse mm allocated blocks",
			'value_type':'float',
			'units': 'blocks',
			'slope': 'both',
		},
		bh_mm_alloc_objs = {
			'description': "BrightHouse mm allocated objects",
			'value_type':'float',
			'units': 'objs',
			'slope': 'both',
		},
		bh_mm_alloc_pack_size = {
			'description': "BrightHouse mm allocated pack size",
			'value_type':'float',
			'units': 'pksz',
			'slope': 'both',
		},
		bh_mm_alloc_packs = {
			'description': "BrightHouse mm allocated packs",
			'value_type':'float',
			'units': 'packs',
			'slope': 'both',
		},
		bh_mm_alloc_temp = {
			'description': "BrightHouse mm allocated temp",
			'value_type':'float',
			'units': 'temps',
			'slope': 'both',
		},
		bh_mm_free_blocks = {
			'description': "BrightHouse mm free blocks",
			'value_type':'float',
			'units': 'blocks',
			'slope': 'both',
		},
		bh_mm_free_packs = {
			'description': "BrightHouse mm free packs",
			'value_type':'float',
			'units': 'packs',
			'slope': 'both',
		},
		bh_mm_free_size = {
			'description': "BrightHouse mm free size",
			'value_type':'float',
			'units': 'szunits',
			'slope': 'both',
		},
		bh_mm_free_temp = {
			'description': "BrightHouse mm free temp",
			'value_type':'float',
			'units': 'tmps',
			'slope': 'both',
		},
		bh_mm_free_temp_size = {
			'description': "BrightHouse mm temp size",
			'value_type':'float',
			'units': 'tmpunits',
			'slope': 'both',
		},
		bh_mm_freeable = {
			'description': "BrightHouse mm freeable",
			'value_type':'float',
			'units': 'allocunits',
			'slope': 'both',
		},
		bh_mm_release1 = {
			'description': "BrightHouse mm release1",
			'value_type':'float',
			'units': 'relunits',
			'slope': 'both',
		},
		bh_mm_release2 = {
			'description': "BrightHouse mm release2",
			'value_type':'float',
			'units': 'relunits',
			'slope': 'both',
		},
		bh_mm_release3 = {
			'description': "BrightHouse mm release3",
			'value_type':'float',
			'units': 'relunits',
			'slope': 'both',
		},
		bh_mm_release4 = {
			'description': "BrightHouse mm release4",
			'value_type':'float',
			'units': 'relunits',
			'slope': 'both',
		},
		bh_mm_reloaded = {
			'description': "BrightHouse mm reloaded",
			'value_type':'float',
			'units': 'reloads',
			'slope': 'both',
		},
		bh_mm_unfreeable = {
			'description': "BrightHouse mm unfreeable",
			'value_type':'uint',
			'units': 'relunits',
			'slope': 'both',
		},
		bh_readbytes = {
			'description': "BrightHouse read bytes",
			'value_type':'uint',
			'units': 'bytes',
			'slope': 'both',
		},
		bh_readcount = {
			'description': "BrightHouse read count",
			'value_type':'uint',
			'units': 'reads',
			'slope': 'both',
		},
		bh_writebytes = {
			'description': "BrightHouse write bytes",
			'value_type':'uint',
			'units': 'bytes',
			'slope': 'both',
		},
		bh_writecount = {
			'description': "BrightHouse write count",
			'value_type':'uint',
			'units': 'writes',
			'slope': 'both',
		}
	)


	if REPORT_MASTER:
		master_stats_descriptions = dict(
			binlog_count = {
				'description': "Number of binary logs",
				'units': 'logs',
				'slope': 'both',
			},

			binlog_space_current = {
				'description': "Size of current binary log",
				'units': 'bytes',
				'slope': 'both',
			},

			binlog_space_total = {
				'description': "Total space used by binary logs",
				'units': 'bytes',
				'slope': 'both',
			},

			binlog_space_used = {
				'description': "Current binary log size / max_binlog_size",
				'value_type': 'float',
				'units': 'percent',
				'slope': 'both',
			},
		)

	if REPORT_SLAVE:
		slave_stats_descriptions = dict(
			slave_exec_master_log_pos = {
				'description': "The position of the last event executed by the SQL thread from the master's binary log",
				'units': 'bytes',
				'slope': 'both',
			},

			slave_io = {
				'description': "Whether the I/O thread is started and has connected successfully to the master",
				'value_type': 'uint8',
				'units': 'True/False',
				'slope': 'both',
			},

			slave_lag = {
				'description': "Replication Lag",
				'units': 'secs',
				'slope': 'both',
			},

			slave_relay_log_pos = {
				'description': "The position up to which the SQL thread has read and executed in the current relay log",
				'units': 'bytes',
				'slope': 'both',
			},

			slave_sql = {
				'description': "Slave SQL Running",
				'value_type': 'uint8',
				'units': 'True/False',
				'slope': 'both',
			},
		)
		
	update_stats(REPORT_BRIGHTHOUSE, REPORT_BRIGHTHOUSE_ENGINE, REPORT_MASTER, REPORT_SLAVE)

	time.sleep(MAX_UPDATE_TIME)

	update_stats(REPORT_BRIGHTHOUSE, REPORT_BRIGHTHOUSE_ENGINE, REPORT_MASTER, REPORT_SLAVE)

	for stats_descriptions in (brighthouse_stats_descriptions, master_stats_descriptions, mysql_stats_descriptions, slave_stats_descriptions):
		for label in stats_descriptions:
			if infobright_stats.has_key(label):
				format = '%u'
				if stats_descriptions[label].has_key('value_type'):
					if stats_descriptions[label]['value_type'] == "float":
						format = '%f'

				d = {
					'name': 'infobright_' + label,
					'call_back': get_stat,
					'time_max': 60,
					'value_type': "uint",
					'units': "",
					'slope': "both",
					'format': format,
					'description': "http://www.brighthouse.com",
					'groups': 'infobright',
				}

				d.update(stats_descriptions[label])

				descriptors.append(d)

			else:
				logging.error("skipped " + label)

	#logging.debug(str(descriptors))
	return descriptors

def metric_cleanup():
	logging.shutdown()
	# pass

if __name__ == '__main__':
	from optparse import OptionParser
	import os

	logging.debug('running from cmd line')
	parser = OptionParser()
	parser.add_option("-H", "--Host", dest="host", help="Host running Infobright", default="localhost")
	parser.add_option("-u", "--user", dest="user", help="user to connect as", default="")
	parser.add_option("-p", "--password", dest="passwd", help="password", default="")
	parser.add_option("-P", "--port", dest="port", help="port", default=3306, type="int")
	parser.add_option("-S", "--socket", dest="unix_socket", help="unix_socket", default="")
	parser.add_option("--no-brighthouse", dest="get_brighthouse", action="store_false", default=True)
	parser.add_option("--no-brighthouse-engine", dest="get_brighthouse_engine", action="store_false", default=False)
	parser.add_option("--no-master", dest="get_master", action="store_false", default=True)
	parser.add_option("--no-slave", dest="get_slave", action="store_false", default=True)
	parser.add_option("-b", "--gmetric-bin", dest="gmetric_bin", help="path to gmetric binary", default="/usr/bin/gmetric")
	parser.add_option("-c", "--gmond-conf", dest="gmond_conf", help="path to gmond.conf", default="/etc/ganglia/gmond.conf")
	parser.add_option("-g", "--gmetric", dest="gmetric", help="submit via gmetric", action="store_true", default=False)
	parser.add_option("-q", "--quiet", dest="quiet", action="store_true", default=False)

	(options, args) = parser.parse_args()

	metric_init({
		'host': options.host,
		'passwd': options.passwd,
		'user': options.user,
		'port': options.port,
		'get_brighthouse': options.get_brighthouse,
		'get_brighthouse_engine': options.get_brighthouse_engine,
		'get_master': options.get_master,
		'get_slave': options.get_slave,
		'unix_socket': options.unix_socket,
	})

	for d in descriptors:
		v = d['call_back'](d['name'])
		if not options.quiet:
			print ' %s: %s %s [%s]' % (d['name'], v, d['units'], d['description'])

		if options.gmetric:
			if d['value_type'] == 'uint':
				value_type = 'uint32'
			else:
				value_type = d['value_type']

			cmd = "%s --conf=%s --value='%s' --units='%s' --type='%s' --name='%s' --slope='%s'" % \
				(options.gmetric_bin, options.gmond_conf, v, d['units'], value_type, d['name'], d['slope'])
			os.system(cmd)

