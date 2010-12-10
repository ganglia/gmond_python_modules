###  This script reports disk stat metrics to ganglia.
###
###  Notes:
###    This script exposes values in /proc/diskstats and calculates
###    various statistics based on the Linux kernel 2.6. To find
###    more information on these values, look in the Linux kernel
###    documentation for "I/O statistics fields".
###
###    This script has the option of explicitly setting which devices
###    to check using the "devices" option in your configuration. If
###    you set this value, it will invalidate the MIN_DISK_SIZE and
###    IGNORE_DEV options described below. This enables you to
###    monitor specific partitions instead of the entire device.
###    Example value: "sda1 sda2".
###    Example value: "sda sdb sdc".
###
###    This script also checks for a minimum disk size in order to
###    only measure interesting devices by default.
###    [Can be overriden if "devices" is set]
###
###    This script looks for disks to check in /proc/partitions while
###    ignoring any devices present in IGNORE_DEV by default.
###    [Can be overriden if "devices" is set]
###
###  Changelog:
###    v1.0.1 - 2010-07-22
###       * Initial version
###
###    v1.0.2 - 2010-08-03
###       * Modified reads_per_sec to not calculate per second delta.
###         This enables us to generate a better graph by stacking
###         reads/writes with reads/writes merged.
###

###  Copyright Jamie Isaacs. 2010
###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt

import time
import subprocess
import traceback
import logging

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/gmond.log', filemode='w')
logging.debug('starting up')

last_update = 0
cur_time = 0
stats = {}
last_val = {}

MAX_UPDATE_TIME = 30
BYTES_PER_SECTOR = 512

# 5 GB
MIN_DISK_SIZE = 5242880
DEVICES = ''
IGNORE_DEV = 'dm-|loop|drbd'

PARTITIONS_FILE = '/proc/partitions'
DISKSTATS_FILE = '/proc/diskstats'

PARTITIONS = []

def get_partitions():
	logging.debug('getting partitions')
	global PARTITIONS

	if DEVICES != '':
		# Explicit device list has been set
		logging.debug(' DEVICES has already been set')
		out = DEVICES

	else:	
		# Load partitions
		awk_cmd = "awk 'NR > 1 && $0 !~ /" + IGNORE_DEV + "/ && $4 !~ /[0-9]$/ {ORS=\" \"; print $4}' "
		p = subprocess.Popen(awk_cmd + PARTITIONS_FILE, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err = p.communicate()
		logging.debug('  result: ' + out)
		
		if p.returncode:
			logging.warning('failed getting partitions')
			return p.returncode

	for dev in out.split():
		if DEVICES != '':
			# Explicit device list has been set
			PARTITIONS.append(dev)
		else:		
			# Load disk block size
			f = open('/sys/block/' + dev + '/size', 'r')
			c = f.read()
			f.close()

			# Make sure device is large enough to collect stats
			if (int(c) * BYTES_PER_SECTOR / 1024) > MIN_DISK_SIZE:
				PARTITIONS.append(dev)
			else:
				logging.debug(' ignoring ' + dev + ' due to size constraints')

	logging.debug('success getting partitions')
	return 0

def update_stats():
	logging.debug('updating stats')
	global last_update, stats, last_val, cur_time
	global MAX_UPDATE_TIME
	
	cur_time = time.time()

	if cur_time - last_update < MAX_UPDATE_TIME:
		logging.debug(' wait ' + str(int(MAX_UPDATE_TIME - (cur_time - last_update))) + ' seconds')
		return True

	#####
	# Update diskstats
	stats = {}

	if not PARTITIONS:
		part = get_partitions()	
		if part:
			# Fail if return is non-zero
			logging.warning('error getting partitions')
			return False

	# Get values for each disk device
	for dev in PARTITIONS:
		logging.debug(" dev: " + dev)

		# Setup storage lists
		if not dev in stats:
			stats[dev] = {}
		if not dev in last_val:
			last_val[dev] = {}

		# Get values from diskstats file
		p = subprocess.Popen("awk -v dev=" + dev + " '$3 == dev' " + DISKSTATS_FILE, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err = p.communicate()
		
		vals = out.split()
		logging.debug('  vals: ' + str(vals))

		get_diff(dev, 'reads',  int(vals[3]))
		get_diff(dev, 'writes', int(vals[7]))

		get_diff(dev, 'reads_merged',  int(vals[4]))
		get_diff(dev, 'writes_merged', int(vals[8]))

		get_delta(dev, 'read_kbytes_per_sec',  int(vals[5]), float(BYTES_PER_SECTOR) / 1024)
		get_delta(dev, 'write_kbytes_per_sec', int(vals[9]), float(BYTES_PER_SECTOR) / 1024)

		get_diff(dev, 'read_time',  int(vals[6]))
		get_diff(dev, 'write_time', int(vals[10]))

		get_diff(dev, 'io_time', int(vals[12]))
		get_diff(dev, 'weighted_io_time', int(vals[13]))


	logging.debug('success refreshing stats')
	logging.debug('stats: ' + str(stats))
	logging.debug('last_val: ' + str(last_val))

	last_update = cur_time
	return True

def get_delta(dev, key, val, convert=1):
	logging.debug(' get_delta for ' + dev +  '_' + key)
	global stats, last_val

	if convert == 0:
		logging.warning(' convert is zero!')

	interval = cur_time - last_update

	if key in last_val[dev] and interval > 0:

		if val < last_val[dev][key]:
			logging.debug('  fixing int32 wrap')
			val += 4294967296

		stats[dev][key] = int((val - last_val[dev][key]) * float(convert) / float(interval))
	else:
		stats[dev][key] = 0

	last_val[dev][key] = int(val)

def get_diff(dev, key, val):
	logging.debug(' get_diff for ' + dev + '_' + key)
	global stats, last_val

	if key in last_val[dev]:
		stats[dev][key] = val - last_val[dev][key]
	else:
		stats[dev][key] = 0

	last_val[dev][key] = val

def get_stat(name):
	logging.debug(' getting stat: ' + name)
	global stats

	ret = update_stats()

	if ret:
		if name.startswith('diskstat_'):
			fir = name.find('_')
			sec = name.find('_', fir + 1)

			dev = name[fir+1:sec]
			label = name[sec+1:]

			try:
				return stats[dev][label]
			except:
				logging.warning('failed to fetch [' + dev + '] ' + name)
				return 0
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
	global MIN_DISK_SIZE, DEVICES

	DEVICES = params.get('devices')

	logging.debug('init: ' + str(params))

	time_max = 60

	descriptions = dict(
		reads = {
			'units': 'reads',
			'description': 'The number of reads completed'},

		reads_merged = {
			'units': 'reads',
			'description': 'The number of reads merged. Reads which are adjacent to each other may be merged for efficiency. Multiple reads may become one before it is handed to the disk, and it will be counted (and queued) as only one I/O.'},

		read_kbytes_per_sec = {
			'units': 'Kbytes/sec',
			'description': 'The number of Kbytes read per second'},

		read_time = {
			'units': 'ms',
			'description': 'The time in milliseconds spent reading'},

		writes = {
			'units': 'writes',
			'description': 'The number of writes completed'},

		writes_merged = {
			'units': 'writes',
			'description': 'The number of writes merged. Writes which are adjacent to each other may be merged for efficiency. Multiple writes may become one before it is handed to the disk, and it will be counted (and queued) as only one I/O.'},

		write_kbytes_per_sec = {
			'units': 'Kbytes/sec',
			'description': 'The number of Kbytes written per second'},

		write_time = {
			'units': 'ms',
			'description': 'The time in milliseconds spent writing'},

		io_time = {
			'units': 'ms',
			'description': 'The time in milliseconds spent in I/O operations'},

		weighted_io_time = {
			'units': 'ms',
			'description': 'The weighted time in milliseconds spend in I/O operations. This measures each I/O start, I/O completion, I/O merge, or read of these stats by the number of I/O operations in progress times the number of milliseconds spent doing I/O.'}
	)

	update_stats()

	descriptors = []
	for label in descriptions:
		for dev in PARTITIONS: 
			if stats[dev].has_key(label):

				d = {
					'name': 'diskstat_' + dev + '_' + label,
					'call_back': get_stat,
					'time_max': time_max,
					'value_type': 'uint',
					'units': '',
					'slope': 'both',
					'format': '%u',
					'description': label,
					'groups': 'diskstat'
				}

				# Apply metric customizations from descriptions
				d.update(descriptions[label])	

				descriptors.append(d)
			else:
				logging.error("skipped " + label)

	#logging.debug('descriptors: ' + str(descriptors))

	# For command line testing
	#time.sleep(MAX_UPDATE_TIME)
	#update_stats()

	return descriptors

def metric_cleanup():
	logging.shutdown()
	# pass

if __name__ == '__main__':
	from optparse import OptionParser
	import os

	logging.debug('running from cmd line')
	parser = OptionParser()
	parser.add_option('-d', '--devices', dest='devices', default='', help='devices to explicitly check')
	parser.add_option('-b', '--gmetric-bin', dest='gmetric_bin', default='/usr/bin/gmetric', help='path to gmetric binary')
	parser.add_option('-c', '--gmond-conf', dest='gmond_conf', default='/etc/ganglia/gmond.conf', help='path to gmond.conf')
	parser.add_option('-g', '--gmetric', dest='gmetric', action='store_true', default=False, help='submit via gmetric')
	parser.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False)

	(options, args) = parser.parse_args()

	metric_init({
		'devices': options.devices,
	})

	for d in descriptors:
		v = d['call_back'](d['name'])
		if not options.quiet:
			print ' %s: %s %s [%s]' % (d['name'], v, d['units'], d['description'])

		if options.gmetric:
			cmd = "%s --conf=%s --value='%s' --units='%s' --type='%s' --name='%s' --slope='%s'" % \
				(options.gmetric_bin, option.gmond_conf, v, d['units'], d['value_type'], d['name'], d['slope'])
			os.system(cmd)

