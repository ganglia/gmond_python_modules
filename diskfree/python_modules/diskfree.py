#!/usr/bin/python


import os


name_prefix = 'disk_free_'
descriptors = list()


# return a value for the requested metric
def metric_handler(name):

    # parse path from name
    if name == name_prefix + 'rootfs':
        path = '/'
    else:
        path = '/' + name.replace(name_prefix, '').replace('_', '/')

    # get fs stats
    try:
        disk = os.statvfs(path)
    except OSError:
        return 0

    return (disk.f_bavail * disk.f_frsize) / 1024000000


# initialize metric descriptors
def metric_init(params):
    global descriptors

    # read mounts file
    try:
        f = open(params['mounts'])
    except IOError:
        return 0

    # parse mounts
    for line in f:
        if line.startswith('/'):
            mount_info = line.split()

            # create key from path
            if mount_info[1] == '/':
                path_key = 'rootfs'
            else:
                path_key = mount_info[1][1:].replace('/', '_')

            descriptors.append({
                'name': name_prefix + path_key,
                'call_back': metric_handler,
                'time_max': 60,
                'value_type': 'uint',
                'units': 'GB',
                'slope': 'both',
                'format': '%u',
                'description': "Disk space available on %s" % mount_info[1],
                'groups': 'disk'
            })

    return descriptors


# cleanup
def metric_cleanup():
    pass


# the following code is for debugging and testing
if __name__ == '__main__':
    params = {'mounts': 'mounts'}
    metric_init(params)
    for d in descriptors:
        print '%s = %s' % (d['name'], d['call_back'](d['name']))


