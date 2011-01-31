#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os


NAME_PREFIX = 'disk_free_'
PARAMS = {
    'mounts' : '/proc/mounts'
}


def metric_handler(name):
    """Return a value for the requested metric"""

    # parse path from name
    if name == NAME_PREFIX + 'rootfs':
        path = '/'
    else:
        path = '/' + name.replace(NAME_PREFIX, '').replace('_', '/')

    # get fs stats
    try:
        disk = os.statvfs(path)
    except OSError:
        return 0

    # We want metric to be in Gigabytes
    return (disk.f_bavail * disk.f_frsize) / 1073741824.0

    # TODO: Remaining percentage
    # print ( 100.0 * disk.f_bavail)  / disk.f_blocks


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
        return 0

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
                'call_back': metric_handler,
                'time_max': 60,
                'value_type': 'float',
                'units': 'GB',
                'slope': 'both',
                'format': '%u',
                'description': "Disk space available on %s" % mount_info[1],
                'groups': 'disk'
            })

    return descriptors


def metric_cleanup():
    """Cleanup"""

    pass


# the following code is for debugging and testing
if __name__ == '__main__':
    descriptors = metric_init({'mounts': '/proc/mounts'})
    for d in descriptors:
        print '%s = %s' % (d['name'], d['call_back'](d['name']))
