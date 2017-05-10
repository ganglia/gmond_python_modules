import os
import subprocess
import sys
import time
from xml.dom import minidom

METRICS = {
    'time' : 0,
    'data' : {},
    'units': {},
    'descr': {}
}

METRICS_CACHE_MAX = 60


def get_metrics():
    """Return all metrics"""
    global METRICS

    params = global_params

    if ( 'showq_bin' not in params ):
        pass
    elif ( (time.time()-METRICS['time']) > METRICS_CACHE_MAX ):
        new_metrics = {}
        units = {}
        descr = {}
        
        if ( 'moab_home_dir' in params ):
            os.environ['MOABHOMEDIR'] = params['moab_home_dir']
        command = [ params['showq_bin'], "-s", "--xml" ]
        if ( 'moab_server' in params ):
            command.append("--host=%s" % params['moab_server'])
        if ( 'moab_port' in params ):
            command.append("--port=%d" % params['moab_port'])
        if ( 'timeout' in params ):
            command.append("--timeout=%d" % params['timeout'])
        if ( 'debug' in params ):
            print str(command)

        p = subprocess.Popen(command,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             close_fds=True)
        try:
            xmldoc = minidom.parseString("\n".join(p.stdout.readlines()))
            p.stdout.close()
            xmlclusters = xmldoc.getElementsByTagName("cluster")
            for xmlcluster in xmlclusters:
                if ( xmlcluster.hasAttributes() ):
                    metric_name = None
                    metric_value = None
                    metric_descr = None
                    metric_units = None
                    for attr in xmlcluster.attributes.keys():
                        if ( attr=="LocalActiveNodes"  ):
                            metric_name = "allocated_nodes"
                            metric_value = int(xmlcluster.attributes["LocalActiveNodes"].value)
                            metric_units = "nodes"
                            metric_descr = "Allocated Nodes"
                        elif ( attr=="LocalIdleNodes"  ):
                            metric_name = "idle_nodes"
                            metric_value = int(xmlcluster.attributes["LocalIdleNodes"].value)
                            metric_units = "nodes"
                            metric_descr = "Idle Nodes"
                        elif ( attr=="LocalUpNodes"  ):
                            metric_name = "up_nodes"
                            metric_value = int(xmlcluster.attributes["LocalUpNodes"].value)
                            metric_descr = "Up Nodes"
                            metric_units = "nodes"
                        elif ( attr=="LocalAllocProcs" ):
                            metric_name = "allocated_cores"
                            metric_value = int(xmlcluster.attributes["LocalAllocProcs"].value)
                            metric_units = "cores"
                            metric_descr = "Allocated Processor Cores"
                        elif ( attr=="LocalIdleProcs" ):
                            metric_name = "idle_cores"
                            metric_value = int(xmlcluster.attributes["LocalIdleProcs"].value)
                            metric_units = "cores"
                            metric_descr = "Idle Processor Cores"
                        elif ( attr=="LocalUpProcs" ):
                            metric_name = "up_cores"
                            metric_value = int(xmlcluster.attributes["LocalUpProcs"].value)
                            metric_units = "cores"
                            metric_descr = "Up Processor Cores"
                        if ( metric_name is not None and
                             metric_value is not None and
                             metric_descr is not None and
                             metric_units is not None ):
                            new_metrics[metric_name] = metric_value
                            units[metric_name] = metric_units
                            descr[metric_name] = metric_descr

            xmlqueues = xmldoc.getElementsByTagName("queue")
            for xmlqueue in xmlqueues:
                if ( xmlqueue.hasAttributes() ):
                    if ( "option" in xmlqueue.attributes.keys() and 
                         "count" in xmlqueue.attributes.keys() ):
                        if ( xmlqueue.attributes["option"].value=="active" ):
                            metric_name = "running_jobs"
                            new_metrics[metric_name]  = int(xmlqueue.attributes["count"].value)
                            units[metric_name] = "jobs"
                            descr[metric_name] = "Running Jobs"
                        elif ( xmlqueue.attributes["option"].value=="eligible" ):
                            metric_name = "eligible_jobs"
                            new_metrics[metric_name]  = int(xmlqueue.attributes["count"].value)
                            units[metric_name] = "jobs"
                            descr[metric_name] = "Eligible Jobs"
                        elif ( xmlqueue.attributes["option"].value=="blocked" ):
                            metric_name = "blocked_jobs"
                            new_metrics[metric_name]  = int(xmlqueue.attributes["count"].value)
                            units[metric_name] = "jobs"
                            descr[metric_name] = "Blocked Jobs"
                
            METRICS = {
                'time': time.time(),
                'data': new_metrics,
                'units': units,
                'descr': descr
            }
        except Exception as e:
            sys.stderr.write("WARNING:  %s\n" % str(e))
            pass

    return [METRICS]


def get_value(name):
    """Return a value for the requested metric"""
    try:
        
        metrics = get_metrics()[0]

        if ( name in metrics['data'].keys() ):
            result = metrics['data'][name]
        else:
            result = 0

    except Exception as e:
        result = 0

    return result

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d


def metric_init(params):
    global descriptors, metric_map, Desc_Skel, global_params

    descriptors = []

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_value,
        'time_max'    : METRICS_CACHE_MAX,
        'value_type'  : 'uint',
        'format'      : '%d',
        'units'       : 'count/s',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'XXX',
    }

    global_params = params

    metrics = get_metrics()[0]

    for item in metrics['data']:
        descriptors.append(create_desc(Desc_Skel, {
                'name'          : item,
                'description'   : metrics['descr'][item],
                'groups'        : params['metric_prefix'],
                'units'         : metrics['units'][item]
                }))

    return descriptors


def metric_cleanup():
    """Clean up the metric module"""
    pass


#This code is for debugging and unit testing
if __name__ == '__main__':
    
    params = {
        "metric_prefix" : "moab",
        #"debug"         : True,
        "moab_home_dir" : "/var/spool/moab",
        #"moab_server"   : "moabsrv.mydomain.org",
        #"moab_port"     : 42559,
        "showq_bin"     : "/opt/moab/bin/showq",
        "timeout"       : 30,
    }
    
    descriptors = metric_init(params)

    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print '%s = %s' % (d['name'],  v)
        print 'Sleeping %d seconds\n' % METRICS_CACHE_MAX
        time.sleep(METRICS_CACHE_MAX)

