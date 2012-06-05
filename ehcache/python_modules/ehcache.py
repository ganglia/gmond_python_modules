###  This script reports jmx ehcache metrics to ganglia.
###
###  Notes:
###    This script exposes ehcache MBeans to Ganglia. The following
###    are exposed:
###      - CacheHitCount
###      - CacheMissCount
###
###  Changelog:
###    v1.0.1 - 2010-07-30
###      * Initial version taken from jmxsh.py v1.0.5

###  Copyright Jamie Isaacs. 2010
###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt

import time
import subprocess
import traceback, sys, re
import tempfile
import logging

descriptors = []

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/gmond.log', filemode='w')
#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/gmond.log2')
logging.debug('starting up')

last_update = 0
stats = {}
last_val = {}

METRICS = {}
COMP = {}
HOST = 'localhost'
PORT = '8887'
NAME = PORT

MAX_UPDATE_TIME = 15
JMXSH = '/usr/share/java/jmxsh.jar'

def update_stats():
	logging.debug('updating stats')
	global last_update, stats, last_val
	
	cur_time = time.time()

	if cur_time - last_update < MAX_UPDATE_TIME:
		logging.debug(' wait ' + str(int(MAX_UPDATE_TIME - (cur_time - last_update))) + ' seconds')
		return True

	#####
	# Build jmxsh script into tmpfile
	sh  = '# jmxsh\njmx_connect -h ' + HOST + ' -p ' + PORT + '\n'
	sh += 'set obj [lindex [split [jmx_list net.sf.ehcache.hibernate] =] 2]\n'
	_mbean = 'net.sf.ehcache:type=SampledCache,SampledCacheManager=${obj},name='
	for name,mbean_name in METRICS.items():
		sh += 'puts "' + name + '_hit_count: [jmx_get -m ' + _mbean + mbean_name + ' CacheHitCount]"\n'
		sh += 'puts "' + name + '_miss_count: [jmx_get -m ' + _mbean + mbean_name + ' CacheMissCount]"\n'

	#logging.debug(sh)
	
	try:
		# run jmxsh.jar with the temp file as a script
		cmd = "java -jar " + JMXSH + " -q"
		p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err = p.communicate(sh)
		#logging.debug('cmd: ' + cmd + '\nout:\n' + out + '\nerr: ' + err + '\ncode: ' + str(p.returncode))

		if p.returncode:
			logging.warning('failed executing jmxsh\n' + cmd + '\n' + err)
			return False
	except:
		logging.warning('Error running jmx java\n' + traceback.print_exc(file=sys.stdout))
		return False

	# Calculate diff for each metric
	try:
		# now parse out the values
		for line in out.strip().split('\n'):
			params = line.split(': ')
			name = params[0]
			val = params[1]

			val = int(val)
			if name in last_val:
				if val > last_val[name]:
					stats[name] = val - last_val[name]
				else:
					# value was reset since last update
					stats[name] = 0
			else:
				stats[name] = 0

			last_val[name] = val

	except:
		logging.warning('Error parsing\n' + traceback.print_exc(file=sys.stdout))
		return False

	logging.debug('success refreshing stats')
	logging.debug('stats: ' + str(stats))
	logging.debug('last_val: ' + str(last_val))

	last_update = cur_time
	return True

def get_stat(name):
	logging.debug('getting stat: ' + name)

	ret = update_stats()

	if ret:
		first = 'jmx_' + NAME + '_'
		if name.startswith(first):
			label = name[len(first):]
		else:
			label = name

		try:
			return stats[label]
		except:
			logging.warning('failed to fetch ' + name)
			return 0
	else:
		return 0

def metric_init(params):
	global descriptors
	global METRICS,HOST,PORT,NAME

	logging.debug('init: ' + str(params))

	try:
		HOST = params.pop('host')
		PORT = params.pop('port')
		NAME = params.pop('name')
		
	except:
		logging.warning('Incorrect parameters')

	METRICS = params

	update_stats()

	# dynamically build our descriptors based on the first run of update_stats()
	descriptions = dict()
	for name in stats:
		descriptions[name] = {}

	time_max = 60
	for label in descriptions:
		if stats.has_key(label):

			d = {
				'name': 'jmx_' + NAME + '_' + label,
				'call_back': get_stat,
				'time_max': time_max,
				'value_type': 'uint',
				'units': '',
				'format': '%u',
				'slope': 'both',
				'description': label,
				'groups': 'jmx'
			}

			# Apply metric customizations from descriptions
			d.update(descriptions[label])

			descriptors.append(d)

		else:
			logging.error("skipped " + label)

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
	parser.add_option('-p', '--param', dest='param', default='', help='module parameters')
	parser.add_option('-v', '--value', dest='value', default='', help='module values')
	parser.add_option('-b', '--gmetric-bin', dest='gmetric_bin', default='/usr/bin/gmetric', help='path to gmetric binary')
	parser.add_option('-c', '--gmond-conf', dest='gmond_conf', default='/etc/ganglia/gmond.conf', help='path to gmond.conf')
	parser.add_option('-g', '--gmetric', dest='gmetric', action='store_true', default=False, help='submit via gmetric')
	parser.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False)
	parser.add_option('-t', '--test', dest='test', action='store_true', default=False, help='test the regex list')

	(options, args) = parser.parse_args()

	_param = options.param.split(',')
	_val = options.value.split('|')

	params = {}
	i = 0
	for name in _param:
		params[name] = _val[i]
		i += 1
	
	metric_init(params)

	if options.test:
		print('')
		print(' waiting ' + str(MAX_UPDATE_TIME) + ' seconds')
		time.sleep(MAX_UPDATE_TIME)
		update_stats()

	for d in descriptors:
		v = d['call_back'](d['name'])
		if not options.quiet:
			print ' %s: %s %s [%s]' % (d['name'], d['format'] % v, d['units'], d['description'])

		if options.gmetric:
			if d['value_type'] == 'uint':
				value_type = 'uint32'
			else:
				value_type = d['value_type']

			cmd = "%s --conf=%s --value='%s' --units='%s' --type='%s' --name='%s' --slope='%s'" % \
				(options.gmetric_bin, options.gmond_conf, v, d['units'], value_type, d['name'], d['slope'])
			os.system(cmd)

