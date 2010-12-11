#!/usr/bin/env python
# -*- coding: utf-8 -*-
import beanstalkc

HOST='localhost'
PORT=14711
def stat_handler(name):
    bean=beanstalkc.Connection(host=HOST,port=PORT)
    return bean.stats()[name]
    
def tube_stat_handler(name):
    bean=beanstalkc.Connection(host=HOST,port=PORT)
    return bean.stats_tube(name.split('_')[0])[name.split('_')[1]]
    
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
        
    #now get all the tubes
    bean=beanstalkc.Connection(host=HOST,port=PORT)
    tubes=bean.tubes()
    for tube in tubes:
        descriptors.append(
        {'name': tube+'_total-jobs',
            'call_back': tube_stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'total jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Number of Beanstalkd Jobs ('+tube+')',
            'groups': 'beanstalkd'})
        descriptors.append(
        {'name': tube+'_current-watching',
            'call_back': tube_stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'clients',
            'slope': 'both',
            'format': '%u',
            'description': 'Number Watchers ('+tube+')',
            'groups': 'beanstalkd'})
        descriptors.append(
        {'name': tube+'_current-jobs-buried',
            'call_back': tube_stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Current Number of Jobs Burried ('+tube+')',
            'groups': 'beanstalkd'})
        descriptors.append(
        {'name': tube+'_current-jobs-ready',
            'call_back': tube_stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'clients',
            'slope': 'both',
            'format': '%u',
            'description': 'Current Jobs Ready ('+tube+')',
            'groups': 'beanstalkd'})
        descriptors.append(
        {'name': tube+'_current-waiting',
            'call_back': tube_stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Current Number of Jobs Waiting ('+tube+')',
            'groups': 'beanstalkd'})
    
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
