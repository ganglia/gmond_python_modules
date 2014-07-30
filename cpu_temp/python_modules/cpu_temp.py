#!/usr/bin/env python2
import os

descriptors = list()
sysdir = '/sys/devices/platform/'
handler_dict = dict()

def metric_init(params):
    global descriptors
    try:
        coretemp_list = [i for i in os.listdir(sysdir) if i.startswith('coretemp')]
    except OSError:
        print 'No dir named' + sysdir
        os._exit(1)
    if not coretemp_list:
        print 'No dir name starts with coretemp'
        os._exit(1)
    for coretemp in coretemp_list:
        coreinput_list = [i for i in os.listdir(sysdir + coretemp) if i.endswith('_input')]
        try:
            with open(sysdir + coretemp + '/temp1_label','r') as f:
                phy_id_prefix = f.read().split()[-1]
        except IOError:
            print 'No temp1_label file'
            os._exit(1)
        for coreinput in coreinput_list:
            build_descriptor(coretemp,coreinput,phy_id_prefix)

def build_descriptor(coretemp,coreinput,phy_id_prefix):
    global handler_dict
    if coreinput == 'temp1_input':
        name = 'physical_' + phy_id_prefix + '_avg'
        description = 'Physical id ' + phy_id_prefix
        groups = 'cpu_temp_avg'
        handler_dict[name] = sysdir + coretemp + '/temp1_input'
    else:
        with open(sysdir + coretemp + '/' + coreinput[:-6] + '_label','r') as f:
            coreid = f.read().split()[-1]
        name = 'physical_' + phy_id_prefix + '_core_' + coreid
        description = 'Physical id ' + phy_id_prefix + ' Core ' + coreid
        groups = 'cpu_temp'
        handler_dict[name] = sysdir + coretemp + '/' + coreinput
    call_back = metric_handler
    time_max = 60
    value_type = 'float'
    units = 'C'
    slope = 'both'
    format = '%.1f'
    d = {'name': name,
        'call_back': call_back,
        'time_max': time_max,
        'value_type': value_type,
        'units': units,
        'slope': slope,
        'format': format,
        'description': description,
        'groups': groups
        }
    try:
        call_back(name)
        descriptors.append(d)
    except:
        print 'Build descriptor Failed'

def metric_handler(name):
    try:
        with open(handler_dict.get(name),'r') as f:
            temp = f.read()
    except:
        temp = 0
    temp_float = int(temp) / 1000.0
    return temp_float

def metric_cleanup():
    pass

if __name__ == '__main__':
     metric_init({})
     for d in descriptors:
         v = d['call_back'](d['name'])
         print 'value for %s is %.1f %s' % (d['name'],v,d['units'])
         for k,v in d.iteritems():
             print k,v
