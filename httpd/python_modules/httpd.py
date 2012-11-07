###  This script reports httpd metrics to ganglia.
###
###  Notes:
###    The following mod_status variables only report average values
###    over the lifetime of the running process: CPULoad, ReqPerSec,
###    BytesPerSec, and BytesPerReq. This script checks the system
###    for child process average memory usage and ignores the other
###    averages.
###
###    This script makes use of the ExtendedStatus metrics from
###    mod_status. To use these values you must enable them with the
###    "extended" option.
###
###    This script also exposes the startup values for prefork
###    variables including: StartServers, MinSpareServers,
###    MaxSpareServers, ServerLimit, MaxClients, MaxRequestsPerChild.
###    To use these values you must enable them with the "prefork"
###    option.
###
###    TODO
###       * Update avg memory usage to use Linux /proc/[pid]/statm
###       * Add scoreboard metrics?
###
###  Changelog:
###    v1.0.1 - 2010-07-21
###       * Initial version
###
###    v1.1.0 - 2010-08-03
###       * Code cleanup
###       * Removed CPU utilization
###

###  Copyright Jamie Isaacs. 2010
###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt

import time
import urllib
import subprocess
import traceback

import sys, re
import logging

descriptors = []

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/gmond.log', filemode='w')
logging.debug('starting up')

last_update = 0
last_update_server = 0
httpd_stats = {}
httpd_stats_last = {}
server_stats = {}

MAX_UPDATE_TIME = 15

#SCOREBOARD_KEY = ('_', 'S', 'R', 'W', 'K', 'D', 'C', 'L', 'G', 'I', '.')

def update_stats():
	logging.debug('updating stats')
	global last_update, httpd_stats, httpd_stats_last
	
	cur_time = time.time()

	if cur_time - last_update < MAX_UPDATE_TIME:
		logging.debug(' wait ' + str(int(MAX_UPDATE_TIME - (cur_time - last_update))) + ' seconds')
		return True
	else:
		last_update = cur_time

	#####
	# Update Apache stats
	try:
		httpd_stats = {}
		logging.debug(' opening URL: ' + str(STATUS_URL))
		f = urllib.urlopen(STATUS_URL, None, 2)

		for line in f.readlines():
			diff = False
			if 'Total Accesses:' in line:
				key = 'hits'
				diff = True
			elif 'Total kBytes:' in line:
				key = 'sent_kbytes'
				diff = True
			elif 'Uptime:' in line:
				key = 'uptime'
			elif 'BusyWorkers:' in line:
				key = 'busy_workers'
			elif 'IdleWorkers:' in line:
				key = 'idle_workers'
			#elif 'Scoreboard:' in line:
			#	line = line.strip().split(': ')
			#	logging.debug('  scb: ' + str(line))
			#	if len(line) == 2:
			#		scb = line[1]
			#		# Iterate over each character in scb
			#		for c in scb:
			#			print(c)
			#	continue
			else:
				continue

			line = line.strip().split(': ')
			logging.debug('  line: ' + str(line))

			if len(line) == 2:
				val = int(line[1])

				if diff:
					# Do we have an old value to calculate the delta?
					if key in httpd_stats_last:
						httpd_stats[key] = val - httpd_stats_last[key]
					else:
						httpd_stats[key] = 0

					httpd_stats_last[key] = val
				else:
					httpd_stats[key] = val

		f.close()
	except:
		logging.warning('error refreshing stats')
		logging.warning(traceback.print_exc(file=sys.stdout))
		return False

	if not httpd_stats:
		logging.warning('error refreshing stats')
		return False

	#####
	# Update Mem Utilization (avg_worker_size)
	# only measure the children, not the parent Apache process
	try:
		logging.debug(' updating avg_worker_size')
		p = subprocess.Popen("ps -u" + APACHE_USER + " -o rss,args | awk '/" + APACHE_BIN + "/ {sum+=$1; ++n} END {printf(\"%d\", sum/n)}'", shell=True, stdout=subprocess.PIPE)
		out, err = p.communicate()
		logging.debug('  result: ' + out)

		httpd_stats['avg_worker_size'] = int(out)
	except:
		logging.warning('error refreshing stats (avg_worker_size)')
		return False

	logging.debug('success refreshing stats')
	logging.debug('httpd_stats: ' + str(httpd_stats))

	return True

def update_server_stats():
	logging.debug('updating server stats')
	global last_update_server, server_stats

	# If the uptime is still greater than the last checked uptime
	# This will ensure these prefork values are only updated on apache restart
	if last_update_server != 0 and httpd_stats['uptime'] >= last_update_server:
		logging.debug(' wait until server restarts')
		return True
	else:
		if httpd_stats:
			last_update_server = httpd_stats['uptime']
		else:
			# Stats have not been loaded
			last_update_server = 0

	#####
	# Update apache version
	logging.debug(' updating server_version')
	try:
		p = subprocess.Popen(APACHE_CTL + ' -v', shell=True, stdout=subprocess.PIPE)
		out, err = p.communicate()

		for line in out.split('\n'):
			if 'Server version:' in line:
				key = 'server_version'
			else:
				continue

			line = line.split(': ')
			logging.debug('  line: ' + str(line))

			if len(line) == 2:
				server_stats[key] = line[1]
	except:
		logging.warning('error refreshing stats (server_version)')
		return False

	if REPORT_PREFORK:
		#####
		# Update prefork values
		logging.debug(' updating prefork stats')

		# Load Apache config file
		f = open(APACHE_CONF, 'r')
		c = f.read()
		f.close()

		# Find the prefork section
		m = re.search('prefork\.c>(.*?)<', c, re.DOTALL)
		if m:
			prefork = m.group(1).strip()
		else:
			logging.warning('failed updating server stats: prefork')
			return False

		# Extract the values
		for line in prefork.split('\n'):
			if 'StartServers' in line:
				key = 'start_servers'
			elif 'MinSpareServers' in line:
				key = 'min_spare_servers'
			elif 'MaxSpareServers' in line:
				key = 'max_spare_servers'
			elif 'ServerLimit' in line:
				key = 'server_limit'
			elif 'MaxClients' in line:
				key = 'max_clients'
			elif 'MaxRequestsPerChild' in line:
				key = 'max_requests_per_child'
			else:
				continue

			line = line.split()
			logging.debug('  line: ' + str(line))

			if len(line) == 2:
				server_stats[key] = int(line[1])


	logging.debug('success refreshing server stats')
	logging.debug('server_stats: ' + str(server_stats))

	return True

def get_stat(name):
	logging.debug('getting stat: ' + name)

	ret = update_stats()

	if ret:
		if name.startswith('httpd_'):
			label = name[6:]
		else:
			label = name

		try:
			return httpd_stats[label]
		except:
			logging.warning('failed to fetch ' + name)
			return 0
	else:
		return 0

def get_server_stat(name):
	logging.debug('getting server stat: ' + name)

	ret = update_server_stats()

	if ret:
		if name.startswith('httpd_'):
			label = name[6:]
		else:
			label = name

		try:
			return server_stats[label]
		except:
			logging.warning('failed to fetch: ' + name)
			return 0
	else:
		return 0

def metric_init(params):
	global descriptors

	global STATUS_URL, APACHE_CONF, APACHE_CTL, APACHE_BIN, APACHE_USER
	global REPORT_EXTENDED, REPORT_PREFORK

	STATUS_URL	= params.get('status_url')
	APACHE_CONF	= params.get('apache_conf')
	APACHE_CTL	= params.get('apache_ctl').replace('/','\/')
	APACHE_BIN	= params.get('apache_bin').replace('/','\/')
	APACHE_USER	= params.get('apache_user')
	REPORT_EXTENDED = str(params.get('get_extended', True)) == 'True'
	REPORT_PREFORK	 = str(params.get('get_prefork', True)) == 'True'

	logging.debug('init: ' + str(params))

	time_max = 60

	descriptions = dict(
		server_version = {
			'call_back': get_server_stat,
			'value_type': 'string',
			'units': '',
			'description': 'Apache version number'},

		busy_workers = {
			'units': 'workers',
			'description': 'Busy Workers'},

		idle_workers = {
			'units': 'workers',
			'description': 'Idle Workers'},

		avg_worker_size = {
			'units': 'KB',
			'description': 'Average Worker Size'},
	)

	if REPORT_EXTENDED:
		descriptions['hits'] = {
				'units': 'req',
				'description': 'The number of requests that clinets have sent to the server'}

		descriptions['sent_kbytes'] = {
				'units': 'KB',
				'description': 'The number of Kbytes sent to all clients'}

		descriptions['uptime'] = {
				'units': 'sec',
				'description': 'The number of seconds that the Apache server has been up'}

	if REPORT_PREFORK:
		descriptions['start_servers'] = {
				'call_back': get_server_stat,
				'units': 'processes',
				'slope': 'zero',
				'description': 'The number of child server processes created at startup'}

		descriptions['min_spare_servers'] = {
				'call_back': get_server_stat,
				'units': 'processes',
				'slope': 'zero',
				'description': 'The minimum number of idle child server processes'}

		descriptions['spare_servers'] = {
				'call_back': get_server_stat,
				'units': 'processes',
				'slope': 'zero',
				'description': 'The maximum number of idle child server processes'}

		descriptions['server_limit'] = {
				'call_back': get_server_stat,
				'units': 'processes',
				'slope': 'zero',
				'description': 'The upper limit on configurable number of processes'}

		descriptions['max_clients'] = {
				'call_back': get_server_stat,
				'units': 'connections',
				'slope': 'zero',
				'description': 'The maximum number of connections that will be processed simultaneously'}

		descriptions['max_requests_per_child'] = {
				'call_back': get_server_stat,
				'time_max': time_max,
				'units': 'requests',
				'slope': 'zero',
				'description': 'The maximum number of requests that an individual child server will handle during its life'}

	update_stats()
	update_server_stats()

	for label in descriptions:
		if httpd_stats.has_key(label):
			d = {
				'name': 'httpd_' + label,
				'call_back': get_stat,
				'time_max': time_max,
				'value_type': 'uint',
				'units': '',
				'slope': 'both',
				'format': '%u',
				'description': label,
				'groups': 'httpd'
			}

		elif server_stats.has_key(label):
			d = {
				'name': 'httpd_' + label,
				'call_back': get_server_stat,
				'time_max': time_max,
				'value_type': 'uint',
				'units': '',
				'slope': 'both',
				'format': '%u',
				'description': label,
				'groups': 'httpd'
			}

		else:
			logging.error("skipped " + label)
			continue

		# Apply metric customizations from descriptions
		d.update(descriptions[label])
		descriptors.append(d)

	#logging.debug('descriptors: ' + str(descriptors))

	return descriptors

def metric_cleanup():
	logging.shutdown()
	# pass

if __name__ == '__main__':
	from optparse import OptionParser
	import os

	logging.debug('running from cmd line')
	parser = OptionParser()
	parser.add_option('-U', '--URL', dest='status_url', default='http://localhost/server-status?auto', help='URL for Apache status page')
	parser.add_option('-a', '--apache-conf', dest='apache_conf', default='/etc/httpd/conf/httpd.conf', help='path to httpd.conf')
	parser.add_option('-t', '--apache-ctl', dest='apache_ctl', default='/usr/sbin/apachectl', help='path to apachectl')
	parser.add_option('-d', '--apache-bin', dest='apache_bin', default='/usr/sbin/httpd', help='path to httpd')
	parser.add_option('-u', '--apache-user', dest='apache_user', default='apache', help='username that runs httpd')        
	parser.add_option('-e', '--extended', dest='get_extended', action='store_true', default=False)
	parser.add_option('-p', '--prefork', dest='get_prefork', action='store_true', default=False)
	parser.add_option('-b', '--gmetric-bin', dest='gmetric_bin', default='/usr/bin/gmetric', help='path to gmetric binary')
	parser.add_option('-c', '--gmond-conf', dest='gmond_conf', default='/etc/ganglia/gmond.conf', help='path to gmond.conf')
	parser.add_option('-g', '--gmetric', dest='gmetric', action='store_true', default=False, help='submit via gmetric')
	parser.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False)

	(options, args) = parser.parse_args()

	metric_init({
		'status_url': options.status_url,
		'apache_conf': options.apache_conf,
		'apache_ctl': options.apache_ctl,
		'apache_bin': options.apache_bin,
		'apache_user': options.apache_user,
		'get_extended': options.get_extended,
		'get_prefork': options.get_prefork
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

