#!/usr/bin/env python
################################################################################
# Disk Free gmond module for Ganglia
# Copyright (c) 2011 Michael T. Conigliaro <mike [at] conigliaro [dot] org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
################################################################################

import os


NAME_PREFIX = 'disk_free_'
PARAMS = {
    'mounts'    : '/proc/mounts',
    'unit_type' : 'absolute' # 'absolute' or 'percent'
}


def get_value(name):
    """Return a value for the requested metric"""

    # parse path from name
    if name == NAME_PREFIX + 'rootfs':
        path = '/'
    else:
        path = '/' + name.replace(NAME_PREFIX, '').replace('_', '/')

    # get fs stats
    try:
        disk = os.statvfs(path)
        if PARAMS['unit_type'] == 'percent':
            result = (float(disk.f_bavail) / float(disk.f_blocks)) * 100
        else:
            result = (disk.f_bavail * disk.f_frsize) / float(2**30) # GB

    except OSError:
        result = 0

    except ZeroDivisionError:
        result = 0

    return result


def metric_init(lparams):
    """Initialize metric descriptors"""

    global PARAMS

    # set parameters
    for key in lparams:
        PARAMS[key] = lparams[key]

    # read mounts file
    try:
        f = open(PARAMS['mounts'])
    except IOError:
        f = []

    # parse mounts and create descriptors
    descriptors = []
    for line in f:
        if line.startswith('/'):
            mount_info = line.split()

            # create key from path
            if mount_info[1] == '/':
                path_key = 'rootfs'
            else:
                path_key = mount_info[1][1:].replace('/', '_')

            descriptors.append({
                'name': NAME_PREFIX + path_key,
                'call_back': get_value,
                'time_max': 60,
                'value_type': 'float',
                'units': '%' if PARAMS['unit_type'] == 'percent' else 'GB',
                'slope': 'both',
                'format': '%f',
                'description': "Disk space available on %s" % mount_info[1],
                'groups': 'disk'
            })

    return descriptors


def metric_cleanup():
    """Cleanup"""

    pass


# the following code is for debugging and testing
if __name__ == '__main__':
    descriptors = metric_init(PARAMS)
    for d in descriptors:
        print (('%s = %s') % (d['name'], d['format'])) % (d['call_back'](d['name']))
