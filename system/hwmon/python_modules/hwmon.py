#!/usr/bin/env python

root = '/sys/class/hwmon'
descriptors = []
mapping = {}

import os, glob, re

def temp_finder(name):
    val = open(mapping[name]).read().strip()
    return int(val) / 1000.0

def metric_init(params):
    global descriptors

    sensors = sorted(glob.glob(os.path.join(root, 'hwmon*')))

    for s in sensors:
        temps = glob.glob(os.path.join(s, 'device/temp*_input'))
        # dict values are default labels if no label files exist
        probes = dict(zip(temps, [os.path.basename(x) for x in temps]))

        for i in probes.keys():
            try:
                fname = i.replace('input', 'label')
                fhandle = open(fname, 'r')
                probes[i] = fhandle.read().strip().replace(' ', '_').lower()
                fhandle.close()
            except (IOError, OSError):
                pass

        for i, l in probes.iteritems():
            num = re.search('\d+', i)
            device = i[num.start():num.end()]
            name = 'hwmon_dev%s_%s' % (device, l)
            item = {'name': name,
                    'call_back': temp_finder,
                    'time_max': 90,
                    'value_type': 'float',
                    'units': 'C',
                    'slope': 'both',
                    'format': '%0.2f',
                    'description': 'Temperature for hwmon probe %s' % l,
                    'groups': 'hwmon'}
            descriptors.append(item)
            mapping[name] = i

    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

if __name__ == '__main__':
    metric_init(None)
    for d in descriptors:
        v = d['call_back'](d['name'])
        print 'value for %s: %s' % (d['name'],  str(v))
