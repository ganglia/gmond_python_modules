import logging
import logging.handlers
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

    logging.debug("ganglia_moab: Entering moab::get_metrics")

    params = global_params

    if ( 'showq_bin' not in params ):
        pass
    elif ( (time.time()-METRICS['time']) > METRICS_CACHE_MAX ):
        new_metrics = {}
        units = {}
        descr = {}
        prefix=""
        query_gres = False
        mdiag = None
        if ( "metric_prefix" in params ):
            prefix = params["metric_prefix"]+"_"
        if ( 'moab_home_dir' in params ):
            os.environ['MOABHOMEDIR'] = params['moab_home_dir']
        command = [ params['showq_bin'], "-s", "--xml" ]
        if ( 'moab_server' in params ):
            command.append("--host=%s" % params['moab_server'])
        if ( 'moab_port' in params ):
            command.append("--port=%s" % str(params['moab_port']))
        if ( 'timeout' in params ):
            command.append("--timeout=%s" % str(params['timeout']))
        if ( 'query_gres' in params ):
            query_gres = str(params['query_gres'])=='True'
            if ( 'mdiag_bin' in params ):
                mdiag = params['mdiag_bin']
        logging.debug("ganglia_moab: %s" % " ".join(command))
        try:
            p = subprocess.Popen(command,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 close_fds=True)
            xmldoc = minidom.parseString("\n".join(p.stdout.readlines()))
            p.stdout.close()
            logging.debug("ganglia_moab: %s" % xmldoc.toxml())
            xmlclusters = xmldoc.getElementsByTagName("cluster")
            for xmlcluster in xmlclusters:
                if ( xmlcluster.hasAttributes() ):
                    metric_name = None
                    metric_value = None
                    metric_descr = None
                    metric_units = None
                    for attr in xmlcluster.attributes.keys():
                        if ( attr=="LocalActiveNodes"  ):
                            metric_name = prefix+"allocated_nodes"
                            metric_value = int(xmlcluster.attributes["LocalActiveNodes"].value)
                            metric_units = "nodes"
                            metric_descr = "Allocated Nodes"
                        elif ( attr=="LocalIdleNodes"  ):
                            metric_name = prefix+"idle_nodes"
                            metric_value = int(xmlcluster.attributes["LocalIdleNodes"].value)
                            metric_units = "nodes"
                            metric_descr = "Idle Nodes"
                        elif ( attr=="LocalUpNodes"  ):
                            metric_name = prefix+"up_nodes"
                            metric_value = int(xmlcluster.attributes["LocalUpNodes"].value)
                            metric_descr = "Up Nodes"
                            metric_units = "nodes"
                        elif ( attr=="LocalConfigNodes"  ):
                            metric_name = prefix+"total_nodes"
                            metric_value = int(xmlcluster.attributes["LocalConfigNodes"].value)
                            metric_descr = "Total Nodes"
                            metric_units = "nodes"
                        elif ( attr=="LocalAllocProcs" ):
                            metric_name = prefix+"allocated_cores"
                            metric_value = int(xmlcluster.attributes["LocalAllocProcs"].value)
                            metric_units = "cores"
                            metric_descr = "Allocated Processor Cores"
                        elif ( attr=="LocalIdleProcs" ):
                            metric_name = prefix+"idle_cores"
                            metric_value = int(xmlcluster.attributes["LocalIdleProcs"].value)
                            metric_units = "cores"
                            metric_descr = "Idle Processor Cores"
                        elif ( attr=="LocalUpProcs" ):
                            metric_name = prefix+"up_cores"
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
                            metric_name = prefix+"running_jobs"
                            new_metrics[metric_name]  = int(xmlqueue.attributes["count"].value)
                            units[metric_name] = "jobs"
                            descr[metric_name] = "Running Jobs"
                        elif ( xmlqueue.attributes["option"].value=="eligible" ):
                            metric_name = prefix+"eligible_jobs"
                            new_metrics[metric_name]  = int(xmlqueue.attributes["count"].value)
                            units[metric_name] = "jobs"
                            descr[metric_name] = "Eligible Jobs"
                        elif ( xmlqueue.attributes["option"].value=="blocked" ):
                            metric_name = prefix+"blocked_jobs"
                            new_metrics[metric_name]  = int(xmlqueue.attributes["count"].value)
                            units[metric_name] = "jobs"
                            descr[metric_name] = "Blocked Jobs"

            if ( query_gres and mdiag is not None ):
                try:
                    command = [ mdiag,"-n","GLOBAL","--xml" ]
                    if ( 'moab_server' in params ):
                        command.append("--host=%s" % params['moab_server'])
                    if ( 'moab_port' in params ):
                        command.append("--port=%s" % str(params['moab_port']))
                    if ( 'timeout' in params ):
                        command.append("--timeout=%s" % str(params['timeout']))
                    logging.debug("ganglia_moab: %s" % " ".join(command))
                    p = subprocess.Popen(command,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT,
                                         close_fds=True)
                    xmldoc = minidom.parseString("\n".join(p.stdout.readlines()))
                    p.stdout.close()
                    logging.debug("ganglia_moab: %s" % xmldoc.toxml())
                    xmlnodes = xmldoc.getElementsByTagName("node")
                    for xmlnode in xmlnodes:
                        if ( xmlnode.hasAttributes() ):
                            if ( "GRES" in xmlnode.attributes.keys() ):
                                greses = xmlnode.attributes["GRES"].value
                                for gres in greses.split(";"):
                                    (name,value) = gres.split("=")
                                    metric_name = "%s%s_gres_total" % (prefix,name.lower())
                                    new_metrics[metric_name]  = int(value)
                                    units[metric_name] = "GRES"
                                    descr[metric_name] = "%s GRES Total" % name.lower()
                                    # zero out things that might get updated later
                                    metric_name = "%s%s_gres_used" % (prefix,name.lower())
                                    new_metrics[metric_name]  = 0
                                    units[metric_name] = "GRES"
                                    descr[metric_name] = "%s GRES Used" % name.lower()
                                    metric_name = "%s%s_gres_avail" % (prefix,name.lower())
                                    new_metrics[metric_name]  = 0
                                    units[metric_name] = "GRES"
                                    descr[metric_name] = "%s GRES Available" % name.lower()
                            if ( "AGRES" in xmlnode.attributes.keys() ):
                                greses = xmlnode.attributes["AGRES"].value
                                for gres in greses.split(";"):
                                    (name,value) = gres.split("=")
                                    metric_name = "%s%s_gres_avail" % (prefix,name.lower())
                                    new_metrics[metric_name]  = int(value)
                            if ( "DEDGRES" in xmlnode.attributes.keys() ):
                                greses = xmlnode.attributes["DEDGRES"].value
                                for gres in greses.split(";"):
                                    (name,value) = gres.split("=")
                                    metric_name = "%s%s_gres_used" % (prefix,name.lower())
                                    new_metrics[metric_name]  = int(value)
                except Exception as e:
                    logging.warning("ganglia_moab: %s" % str(e))
                    pass
            METRICS = {
                'time': time.time(),
                'data': new_metrics,
                'units': units,
                'descr': descr
            }
        except Exception as e:
            logging.warning("ganglia_moab: %s" % str(e))
            pass

    logging.debug("ganglia_moab: Leaving moab::get_metrics")

    return [METRICS]


def get_value(name):
    """Return a value for the requested metric"""
    logging.debug("ganglia_moab: Entering moab::get_value")
    try:
        metrics = get_metrics()[0]
        if ( name in metrics['data'].keys() ):
            result = metrics['data'][name]
        else:
            result = 0
    except Exception as e:
        result = 0

    logging.debug("ganglia_moab: Leaving moab::get_value")
    return result


def create_desc(skel, prop):
    #logging.debug("ganglia_moab: Entering moab::create_desc")
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    #logging.debug("ganglia_moab: Leaving moab::create_desc")
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

    # configure logging
    logfmt = "%(asctime)s gmond-moab %(levelname)s: %(message)s"
    if ( 'logformat' in params ):
        logfmt = params['logformat']
    if ( 'logfile' in params ):
        if ( params['logfile'].upper() in ["SYSLOG"] ):
            logging.basicConfig(level=logging.INFO,
                                format=logfmt)
            logfac = "user"
            if ( 'logfacility' in params ):
                logfac = params['logfacility'].lower()
            logaddr = ('localhost',logging.handlers.SYSLOG_UDP_PORT)
            if ( 'logdevice' in params ):
                logaddr = params['logdevice']
            logging.getLogger().addHandler(logging.handlers.SysLogHandler(address=logaddr,facility=logfac))
        else:
            logging.basicConfig(filename=params['logfile'],
                                level=logging.INFO,
                                format=logfmt)
    else:
        logging.basicConfig(level=logging.INFO,
                            format=logfmt)
    if ( 'loglevel' in params ):
        if ( params['loglevel'].upper() in ["CRITICAL"] ):
            logging.getLogger().setLevel(logging.CRITICAL)
        elif ( params['loglevel'].upper() in ["DEBUG"] ):
            logging.getLogger().setLevel(logging.DEBUG)
        elif ( params['loglevel'].upper() in ["ERROR"] ):
            logging.getLogger().setLevel(logging.ERROR)
        elif ( params['loglevel'].upper() in ["FATAL"] ):
            logging.getLogger().setLevel(logging.FATAL)
        elif ( params['loglevel'].upper() in ["INFO"] ):
            logging.getLogger().setLevel(logging.INFO)
        elif ( params['loglevel'].upper() in ["WARN","WARNING"] ):
            logging.getLogger().setLevel(logging.WARN)
        else:
            raise RuntimeError("Unknown loglevel \"%s\"" % params['loglevel'])
    logging.debug("ganglia_moab: Finished configuring logging in moab::metric_init")

    metrics = get_metrics()[0]
    logging.debug("ganglia_moab: METRICS: %s" % str(metrics))

    for item in metrics['data']:
        descriptors.append(create_desc(Desc_Skel, {
                'name'          : item,
                'description'   : metrics['descr'][item],
                'groups'        : params['metric_prefix'],
                'units'         : metrics['units'][item]
                }))

    logging.debug("ganglia_moab: DESCRIPTORS: %s " % str(descriptors))

    logging.debug("ganglia_moab: Leaving moab::metric_init")
    return descriptors


def metric_cleanup():
    """Clean up the metric module"""
    pass


#This code is for debugging and unit testing
if __name__ == '__main__':
    
    params = {
        "metric_prefix" : "moab",
        #"logdevice"     : "/dev/log",
        #"loglevel"      : "DEBUG",
        #"logfile"       : "SYSLOG",
        #"logfacility"   : "user",
        "mdiag_bin"     : "/opt/moab/bin/mdiag",
        #"mdiag_bin"     : "/usr/local/moab/default/bin/mdiag",
        "moab_home_dir" : "/var/spool/moab",
        #"moab_server"   : "moabsrv.mydomain.org",
        #"moab_port"     : 42559,
        #"query_gres"    : "True",
        "showq_bin"     : "/opt/moab/bin/showq",
        #"showq_bin"     : "/usr/local/moab/default/bin/showq",
        "timeout"       : 30,
    }
    
    descriptors = metric_init(params)

    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print '%s (%s) = %s %s' % (d['description'],  d['name'],  v, d['units'])
        print 'Sleeping %d seconds\n' % METRICS_CACHE_MAX
        time.sleep(METRICS_CACHE_MAX)


