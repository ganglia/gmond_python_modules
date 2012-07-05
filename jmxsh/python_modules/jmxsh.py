###  This script reports jmx metrics to ganglia.
###
###  Notes:
###    This script exposes user defined MBeans to Ganglia. The
###    initial execution will attempt to determin value types based
###    on the returned values.
###
###  Changelog:
###    v0.0.1 - 2010-07-29
###      * Initial version
###
###    v1.0.1 - 2010-07-30
###      * Modified jmxsh to read from stdin
###      * Tested to work with gmond python module
###
###    v1.0.2 - 2010-08-05
###      * Added support for composite data
###
###    v1.0.3 - 2010-08-10
###      * Added support additional slope variable
###
###    v1.0.4 - 2010-08-10
###      * Removed slope variable
###      * Added delta/diff option
###        - diff will compute difference since last update
###        - delta wil compute difference per second since last update
###
###    v1.0.5 - 2010-08-11
###      * Fixed bug with value resets

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
METRIC_GROUP = 'jmx'

MAX_UPDATE_TIME = 15
JMXSH = '/usr/share/java/jmxsh.jar'

def get_numeric(val):
	'''Try to return the numeric value of the string'''

	try:
		return float(val)
	except:
		pass

	return val

def get_gmond_format(val):
	'''Return the formatting and value_type values to use with gmond'''
	tp = type(val).__name__

	if tp == 'int':
		return ('uint', '%u')
	elif tp == 'float':
		return ('float', '%.4f')
	elif tp == 'string':
		return ('string', '%u')
	else:
		return ('string', '%u')

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
	for name,mbean in METRICS.items():
		sh += 'puts "' + name + ': [jmx_get -m ' + mbean + ']"\n'

	#logging.debug(sh)
	
	try:
		# run jmxsh.jar with the temp file as a script
		cmd = "java -jar " + JMXSH + " -q"
		p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err = p.communicate(sh)
		#logging.debug('cmd: ' + cmd + '\nout: ' + out + '\nerr: ' + err + '\ncode: ' + str(p.returncode))

		if p.returncode:
			logging.warning('failed executing jmxsh\n' + cmd + '\n' + err)
			return False
	except:
		logging.warning('Error running jmx java\n' + traceback.print_exc(file=sys.stdout))
		return False

	try:
		# now parse out the values
		for line in out.strip().split('\n'):
			params = line.split(': ')
			name = params[0]
			val = params[1]

			if 'CompositeDataSupport' in val:
				# break up the composite data into separate values
				composite_contents = re.search('{(.*?)}', val, re.DOTALL)
				if composite_contents:
					for composite_vals in composite_contents.group(1).split(', '):
						_params = composite_vals.split('=')
						_name = name + '_' + _params[0]
						_val = _params[1]

						stats[_name] = get_numeric(_val)
				else:
					logging.warning('failed extracting composite values for ' + name)
					continue

				continue

			try:
				comp = COMP[name]
				if 'diff' in comp:
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

				elif 'delta' in comp:
					val = float(val)
					interval = cur_time - last_update
					if name in last_val and interval > 0:
						if val > last_val[name]:
							stats[name] = (val - last_val[name]) / float(interval)
						else:
							# value was reset since last update
							stats[name] = 0.0
					else:
						stats[name] = 0.0

					last_val[name] = val

			except KeyError:
				stats[name] = get_numeric(val)

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
	global METRICS,HOST,PORT,NAME,METRIC_GROUP

	logging.debug('init: ' + str(params))

	try:
		HOST = params.pop('host')
		PORT = params.pop('port')
		NAME = params.pop('name')
		METRIC_GROUP = params.pop('metric_group')
		
	except:
		logging.warning('Incorrect parameters')

	# Setup METRICS variable from parameters
	for name,mbean in params.items():
		val = mbean.split('##')
		METRICS[name] = val[0]

		# If optional delta/diff exists in value
		try:
			COMP[name] = val[1]
		except IndexError:
			pass

	update_stats()

	# dynamically build our descriptors based on the first run of update_stats()
	descriptions = dict()
	for name in stats:
		(value_type, format) = get_gmond_format(stats[name])
		descriptions[name] = {
			'value_type': value_type,
			'format': format
		}

	time_max = 60
	for label in descriptions:
		if stats.has_key(label):

			d = {
				'name': 'jmx_' + NAME + '_' + label,
				'call_back': get_stat,
				'time_max': time_max,
				'value_type': 'float',
				'units': '',
				'format': '%u',
				'slope': 'both',
				'description': label,
				'groups': METRIC_GROUP
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

