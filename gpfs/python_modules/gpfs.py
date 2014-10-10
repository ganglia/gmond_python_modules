#/******************************************************************************
#* Portions Copyright (C) 2007 Novell, Inc. All rights reserved.
#*
#* Redistribution and use in source and binary forms, with or without
#* modification, are permitted provided that the following conditions are met:
#*
#*  - Redistributions of source code must retain the above copyright notice,
#*    this list of conditions and the following disclaimer.
#*
#*  - Redistributions in binary form must reproduce the above copyright notice,
#*    this list of conditions and the following disclaimer in the documentation
#*    and/or other materials provided with the distribution.
#*
#*  - Neither the name of Novell, Inc. nor the names of its
#*    contributors may be used to endorse or promote products derived from this
#*    software without specific prior written permission.
#*
#* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS ``AS IS''
#* AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#* IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#* ARE DISCLAIMED. IN NO EVENT SHALL Novell, Inc. OR THE CONTRIBUTORS
#* BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#* CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
#* SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
#* INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
#* CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
#* ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#* POSSIBILITY OF SUCH DAMAGE.
#*
#* Author: Brad Nicholes (bnicholes novell.com)
#******************************************************************************/

import logging
import os
import time
import subprocess

descriptions = {}
descriptors = []
last_update = 0
cur_time = 0
stats = {}
last_val = {}

MAX_UPDATE_TIME = 15
FSYSTEMS = []

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s")
logging.debug('starting up')

MMPMON='/usr/lpp/mmfs/bin/mmpmon'

def update_stats():
	logging.debug('updating stats')
	global descriptions, last_update, stats, last_val, cur_time
	global MAX_UPDATE_TIME

	cur_time = time.time()

	if cur_time - last_update < MAX_UPDATE_TIME:
		logging.debug(' wait ' + str(int(MAX_UPDATE_TIME - (cur_time - last_update))) + ' seconds')
		return True

	#####
	# Update stats
	stats = {}

	# Get data from mmpmon
	p = subprocess.Popen(['/usr/lpp/mmfs/bin/mmpmon','-p','-i','mmpmon.cmd'],stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	for line in p.stdout:
		vals = line.split()
		logging.debug(' vals: ' + str(vals))
		#logging.debug(' fs: ' + vals[14])
		fs = vals[14]
		logging.debug(' Parsing FS: ' + fs)
		if fs not in stats:
			stats[fs] = {}
		if fs not in last_val:
			last_val[fs] = {}
		if fs not in FSYSTEMS:
			FSYSTEMS.append(fs)
		for label, content in descriptions.iteritems():
			#logging.debug(' Setting value for: ' + label)
			if label in last_val[fs]:
				stats[fs][label] = (int(vals[content['field']]) - int(last_val[fs][label])) * float(1)	
			else:
				#logging.debug(' New value for: ' + fs + '_' + label)
				stats[fs][label] = 0

			# This should never be negative so set it to zero if it is
			if stats[fs][label] < 0:
				stats[fs][label] = 0

			last_val[fs][label] = vals[content['field']]

	logging.debug(' success refreshing stats')
	logging.debug(' stats: ' + str(stats))
	logging.debug(' last_val: ' + str(stats))

	last_update = cur_time
	return True

def get_stat(name):
	logging.debug(' getting stat: ' + name)
	global stats

	ret = update_stats()

	if ret:
		fir = name.find('_')
		sec = name.find('_', fir + 1)

		fs = name[fir + 1:sec]
		label = name[sec + 1:]

		try:
			return stats[fs][label]
		except:
			logging.warning('failed to fetch [' + fs + '] ' + name)
			return 0 
	else:
		return 0

def metric_init(params):
	'''Initialize the module and return all metric descriptors'''
	global descriptions
	global descriptors
	
	descriptions = dict(
		bytes_read={
			'units': 'bytes',
			'field': 18,
			'description': 'The number of bytes read'},
		bytes_write={
			'units': 'bytes',
			'field': 20,
			'description': 'The number of bytes written'},
		open_req={
			'units': 'requests',
			'field': 22,
			'description': 'The number of open/create requests'},
		close_req={
			'units': 'requests',
			'field': 24,
			'description': 'The number of close requests'},
		read_req={
			'units': 'requests',
			'field': 26,
			'description': 'The number of application read requests'},
		write_req={
			'units': 'requests',
			'field': 28,
			'description': 'The number of application write requests'},
		readdir_req={
			'units': 'requests',
			'field': 30,
			'description': 'The number of application read directory requests'},
		inode_updates={
			'units': 'requests',
			'field': 32,
			'description': 'The number of inode update requests'},
		)

	update_stats()

	for label in descriptions:
		logging.debug(' Parsing description: ' + label)
		for fs in FSYSTEMS:
			logging.debug(' Parsing fs: ' + fs)
			d = {
				'name': 'gpfs_' + fs + '_' + label,
				'call_back': get_stat,
				'time_max': '60',
				'value_type': 'float',
				'units': descriptions[label]['units'],
				'slope': 'both',
				'format': '%f',
				'description': label,
				'groups': 'gpfs'
			}

			d.update(descriptions[label])
			descriptors.append(d)
		
	return descriptors

def metric_cleanup():
	'''Clean up the module
	Called on shutdown'''
	pass

if __name__ == '__main__':
	params = {'FSYSTEMS': ''}
	metric_init(params)
	while True:
		for d in descriptors:
			v = d['call_back'](d['name'])
			print 'value for %s is %u' % (d['name'], v)

		print 'Sleeping 15 seconds'
		time.sleep(15)
