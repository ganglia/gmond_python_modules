#!/usr/bin/env python
# -*- coding: utf-8 -*-
import beanstalkc

def stat_handler(name):
    bean=beanstalkc.Connection(host='localhost',port=14711)
    return bean.stats()[name]
    
def metric_init(params):
    global descriptors

    descriptors = [{'name': 'current-connections',
        'call_back': stat_handler,
        'time_max': 90,
        'value_type': 'uint',
        'units': 'connections',
        'slope': 'both',
        'format': '%u',
        'description': 'Number of Current Connections to Beanstalkd',
        'groups': 'beanstalkd'},
        {'name': 'total-jobs',
            'call_back': stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'total jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Number of Beanstalkd Jobs',
            'groups': 'beanstalkd'},
        {'name': 'current-jobs-ready',
            'call_back': stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Number of Beanstalkd Jobs \'ready\'',
            'groups': 'beanstalkd'},
        {'name': 'current-jobs-buried',
            'call_back': stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Number of Beanstalkd Jobs \'buried\'',
            'groups': 'beanstalkd'},
        {'name': 'current-jobs-delayed',
            'call_back': stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Number of Beanstalkd Jobs \'delayed\'',
            'groups': 'beanstalkd'},
        {'name': 'current-waiting',
            'call_back': stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Number of Beanstalkd Jobs \'waiting\'',
            'groups': 'beanstalkd'},
        {'name': 'job-timeouts',
            'call_back': stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Number of Beanstalkd Jobs Timeouts',
            'groups': 'beanstalkd'},
        {'name': 'cmd-bury',
            'call_back': stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Number of Beanstalkd Burries',
            'groups': 'beanstalkd'}
        ]

    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    metric_init(None)
    for d in descriptors:
        v = d['call_back'](d['name'])
        print 'value for %s is %u' % (d['name'],  v)
