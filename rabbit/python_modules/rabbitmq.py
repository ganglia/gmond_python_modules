#!/usr/bin/python2.4

import itertools
import json
import logging
import logging.handlers
import optparse
import os
import pprint
import sys
import threading
import time
import urllib2

from string import Template

global descriptors, last_update, vhost, username, password, url_template, result, result_dict, keyToPath

log = None

JSON_PATH_SEPARATOR = "?"
METRIC_TOKEN_SEPARATOR = "___"

INTERVAL = 10
descriptors = list()
username, password = "guest", "guest"
stats = {}
keyToPath = {}
last_update = None
#last_update = {}
compiled_results = {"nodes": None, "queues": None, "connections": None, "exchanges": None, "overview": None}
#Make initial stat test time dict
#for stat_type in ('queues', 'connections','exchanges', 'nodes'):
#    last_update[stat_type] = None

### CONFIGURATION SECTION ###
STATS = ['nodes', 'queues', 'overview']

# QUEUE METRICS #
keyToPath['rmq_messages_ready'] = "%s{0}messages_ready".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_messages_unacknowledged'] = "%s{0}messages_unacknowledged".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_backing_queue_ack_egress_rate'] = "%s{0}backing_queue_status{0}avg_ack_egress_rate".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_backing_queue_ack_ingress_rate'] = "%s{0}backing_queue_status{0}avg_ack_ingress_rate".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_backing_queue_egress_rate'] = "%s{0}backing_queue_status{0}avg_egress_rate".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_backing_queue_ingress_rate'] = "%s{0}backing_queue_status{0}avg_ingress_rate".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_backing_queue_mirror_senders'] = "%s{0}backing_queue_status{0}mirror_senders".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_memory'] = "%s{0}memory".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_consumers'] = "%s{0}consumers".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_messages'] = "%s{0}messages".format(JSON_PATH_SEPARATOR)

RATE_METRICS = [
    'rmq_backing_queue_ack_egress_rate',
    'rmq_backing_queue_ack_ingress_rate',
    'rmq_backing_queue_egress_rate',
    'rmq_backing_queue_ingress_rate',
    'rmq_exchange_publish_in_rate',
    'rmq_exchange_publish_out_rate',
]

QUEUE_METRICS = ['rmq_messages_ready',
                 'rmq_messages_unacknowledged',
                 'rmq_backing_queue_ack_egress_rate',
                 'rmq_backing_queue_ack_ingress_rate',
                 'rmq_backing_queue_egress_rate',
                 'rmq_backing_queue_ingress_rate',
                 'rmq_backing_queue_mirror_senders',
                 'rmq_memory',
                 'rmq_consumers',
                 'rmq_messages']

# NODE METRICS #
keyToPath['rmq_disk_free'] = "%s{0}disk_free".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_disk_free_alarm'] = "%s{0}disk_free_alarm".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_fd_used'] = "%s{0}fd_used".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_fd_used'] = "%s{0}fd_used".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_mem_used'] = "%s{0}mem_used".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_proc_used'] = "%s{0}proc_used".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_sockets_used'] = "%s{0}sockets_used".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_mem_alarm'] = "%s{0}mem_alarm".format(JSON_PATH_SEPARATOR)  # Boolean
keyToPath['rmq_running'] = "%s{0}running".format(JSON_PATH_SEPARATOR)  # Boolean

NODE_METRICS = ['rmq_disk_free', 'rmq_mem_used', 'rmq_disk_free_alarm', 'rmq_running', 'rmq_proc_used',
    'rmq_fd_used', 'rmq_mem_alarm', 'rmq_sockets_used']

# EXCHANGE METRICS #

keyToPath['rmq_exchange_publish_in_rate'] = "%s{0}message_stats{0}publish_in_details{0}rate".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_exchange_publish_out_rate'] = "%s{0}message_stats{0}publish_out_details{0}rate".format(JSON_PATH_SEPARATOR)

EXCHANGE_METRICS = ['rmq_exchange_publish_in_rate', 'rmq_exchange_publish_out_rate']

keyToPath['rmq_overview_message_stats_publish'] = "message_stats{0}publish".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_overview_message_stats_ack'] = "message_stats{0}ack".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_overview_message_stats_deliver_get'] = "message_stats{0}deliver_get".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_overview_message_stats_deliver'] = "message_stats{0}deliver".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_overview_message_stats_deliver_no_ack'] = "message_stats{0}deliver_no_ack".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_overview_queue_totals_messages'] = "queue_totals{0}messages".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_overview_queue_totals_messages_ready'] = "queue_totals{0}messages_ready".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_overview_queue_totals_messages_unacknowledged'] = "queue_totals{0}messages_unacknowledged".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_overview_object_totals_consumers'] = "object_totals{0}consumers".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_overview_object_totals_queues'] = "object_totals{0}queues".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_overview_object_totals_exchanges'] = "object_totals{0}exchanges".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_overview_object_totals_connections'] = "object_totals{0}connections".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_overview_object_totals_channels'] = "object_totals{0}channels".format(JSON_PATH_SEPARATOR)

OVERVIEW_METRICS = ['rmq_overview_message_stats_publish', 'rmq_overview_message_stats_ack', 'rmq_overview_message_stats_deliver_get',
    'rmq_overview_message_stats_deliver', 'rmq_overview_message_stats_deliver_no_ack',
    'rmq_overview_queue_totals_messages', 'rmq_overview_queue_totals_messages_ready',
    'rmq_overview_queue_totals_messages_unacknowledged', 'rmq_overview_object_totals_consumers',
    'rmq_overview_object_totals_queues', 'rmq_overview_object_totals_exchanges',
    'rmq_overview_object_totals_connections', 'rmq_overview_object_totals_channels']

def dig_it_up(obj, path):
    try:
        path = path.split(JSON_PATH_SEPARATOR)
        return reduce(lambda x, y: x[y], path, obj)
    except Exception, e:
        # not WARN because the False return is used for control flow
        # (zero assumed)
        log.debug('dig_it_up Exception %r  path: %s' % (e, path))
        return False


def refreshStats(stats=('nodes', 'queues', 'overview'), vhosts=['/']):
    global url_template, last_update

    now = time.time()

    if not last_update:
        diff = INTERVAL
    else:
        diff = now - last_update

    if diff >= INTERVAL or not last_update:
        log.debug("Fetching Results after %d seconds" % INTERVAL)
        last_update = now
        for stat in stats:
            for vhost in vhosts:
                if stat in ('nodes', 'overview'):
                    vhost = '/'
                result_dict = {}
                if stat == 'overview':
                    urlstring = overview_url
                else:
                    urlstring = url_template.safe_substitute(stats=stat, vhost=vhost)
                log.debug('urlspring: %s' % urlstring)
                result = json.load(urllib2.urlopen(urlstring))
                # Rearrange results so entry is held in a dict keyed by name - queue name, host name, etc.
                if stat in ("queues", "nodes", "exchanges"):
                    for entry in result:
                        name = entry['name']
                        result_dict[name] = entry
                    compiled_results[(stat, vhost)] = result_dict
                elif stat in ("overview"):
                    compiled_results[(stat, vhost)] = result

    return compiled_results

def list_queues(vhost):
    global compiled_results
    queues = compiled_results[('queues', vhost)].keys()
    return queues

def list_nodes():
    global compiled_results
    nodes = compiled_results[('nodes', '/')].keys()
    return nodes


def list_exchanges(vhost):
    global compiled_results
    exchanges = compiled_results[('exchanges', vhost)].keys()
    return exchanges

def getQueueStat(name):
    refreshStats(stats=STATS, vhosts=vhosts)
    # Split a name like "rmq_backing_queue_ack_egress_rate.access"

    # handle queue names with . in them

    log.debug(name)
    stat_name, queue_name, vhost = name.split(METRIC_TOKEN_SEPARATOR)

    vhost = vhost.replace('-', '/')  # decoding vhost from metric name
    # Run refreshStats to get the result object
    result = compiled_results[('queues', vhost)]

    value = dig_it_up(result, keyToPath[stat_name] % queue_name)

    if zero_rates_when_idle and stat_name in RATE_METRICS and 'idle_since' in result[queue_name].keys():
        value = 0

    return float(value)


def getNodeStat(name):
    refreshStats(stats=STATS, vhosts=vhosts)
    # Split a name like "rmq_backing_queue_ack_egress_rate.access"
    stat_name, node_name, vhost = name.split(METRIC_TOKEN_SEPARATOR)
    vhost = vhost.replace('-', '/')  # decoding vhost from metric name

    result = compiled_results[('nodes', '/')]
    value = dig_it_up(result, keyToPath[stat_name] % node_name)

    log.debug('name: %r value: %r' % (name, value))

    return float(value)

def getNodeSumStat(name):
    refreshStats(stats=STATS, vhosts=vhosts)
    # Split a name like "rmq_backing_queue_ack_egress_rate.access"
    stat_name, dummyName, vhost = name.split(METRIC_TOKEN_SEPARATOR)
    vhost = vhost.replace('-', '/')  # decoding vhost from metric name

    result = compiled_results[('nodes', '/')]
    total = 0.0
    for node_name in list_nodes():
        value = dig_it_up(result, keyToPath[stat_name] % node_name)
        total += value

    log.debug('name: %r value: %r' % (name, total))

    return total

def getOverviewStat(name):
    refreshStats(stats=STATS, vhosts=vhosts)
    # Split a name like "rmq_backing_queue_ack_egress_rate.access"

    # handle queue names with . in them

    log.debug(name)
    stat_name, vhost = name.split(METRIC_TOKEN_SEPARATOR)

    vhost = vhost.replace('-', '/')  # decoding vhost from metric name
    # Run refreshStats to get the result object
    result = compiled_results[('overview', vhost)]

    value = dig_it_up(result, keyToPath[stat_name])

    return float(value)

def getExchangeStat(name):
    refreshStats(stats=STATS, vhosts=vhosts)
    # Split a name like "rmq_backing_queue_ack_egress_rate.access"

    # handle queue names with . in them

    log.debug(name)
    stat_name, exchange_name, vhost = name.split(METRIC_TOKEN_SEPARATOR)

    vhost = vhost.replace('-', '/')  # decoding vhost from metric name
    # Run refreshStats to get the result object
    result = compiled_results[('exchanges', vhost)]

    value = dig_it_up(result, keyToPath[stat_name] % exchange_name)

    if zero_rates_when_idle and stat_name in RATE_METRICS and 'idle_since' in result[exchange_name].keys():
        value = 0

    return float(value)


def product(*args, **kwds):
    # replacement for itertools.product
    # product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
    pools = map(tuple, args) * kwds.get('repeat', 1)
    result = [[]]
    for pool in pools:
        result = [x + [y] for x in result for y in pool]
    for prod in result:
        yield tuple(prod)


def str2bool(string):
    if string.lower() in ("yes", "true"):
        return True
    if string.lower() in ("no", "false"):
        return False
    raise Exception("Invalid value of the 'zero_rates_when_idle' param, use one of the ('true', 'yes', 'false', 'no')")


def metric_init(params):
    ''' Create the metric definition object '''
    global descriptors, stats, vhost, username, password, urlstring, url_template, overview_url, compiled_results, STATS, vhosts, zero_rates_when_idle
    if log is None:
        setup_logging('syslog', params['syslog_facility'], params['log_level'])
    log.info('received the following params: %r' % params)
    # Set this globally so we can refresh stats
    if 'host' not in params:
        params['host'], params['vhost'], params['username'], params['password'], params['port'] = "localhost", "/", "guest", "guest", "15672"
    if 'zero_rates_when_idle' not in params:
        params['zero_rates_when_idle'] = "false"

    # Set the vhosts as a list split from params
    vhosts = params['vhost'].split(',')
    username, password = params['username'], params['password']
    host = params['host']
    port = params['port']
    STATS = params['stats']
    if type(STATS) is str:
        STATS = STATS.split(',')

    zero_rates_when_idle = str2bool(params['zero_rates_when_idle'])

    url = 'http://%s:%s/api/$stats/$vhost' % (host, port)
    overview_url = 'http://%s:%s/api/overview' % (host, port)
    base_url = 'http://%s:%s/api' % (host, port)
    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, base_url, username, password)
    handler = urllib2.HTTPBasicAuthHandler(password_mgr)
    opener = urllib2.build_opener(handler)
    opener.open(base_url)
    urllib2.install_opener(opener)
    url_template = Template(url)

    refreshStats(stats=STATS, vhosts=vhosts)

    def metric_handler(name):
        if 15 < time.time() - metric_handler.timestamp:
            metric_handler.timestamp = time.time()
            return refreshStats(stats=STATS, vhosts=vhosts)

    def create_desc(prop):
        d = {
            'name'        : 'XXX',
            'call_back'   : getQueueStat,
            'time_max'    : 60,
            'value_type'  : 'uint',
            'units'       : 'units',
            'slope'       : 'both',
            'format'      : '%d',
            'description' : 'XXX',
            'groups'      : params["metric_group"],
        }

        for k, v in prop.iteritems():
            d[k] = v
        return d

    def buildQueueDescriptors():
        for vhost, metric in product(vhosts, QUEUE_METRICS):
            queues = list_queues(vhost)
            for queue in queues:
                name = "{1}{0}{2}{0}{3}".format(METRIC_TOKEN_SEPARATOR, metric, queue, vhost.replace('/', '-'))
                log.debug(name)
                d1 = create_desc({'name': name.encode('ascii', 'ignore'),
                                  'call_back': getQueueStat,
                                  'value_type': 'float',
                                  'units': 'N',
                                  'slope': 'both',
                                  'format': '%f',
                                  'description': 'Queue_Metric',
                                  'groups': 'rabbitmq,queue'})
                log.debug(d1)
                descriptors.append(d1)

    def buildNodeDescriptors():
        for metric in NODE_METRICS:
            name = "{1}{0}total{0}-".format(METRIC_TOKEN_SEPARATOR, metric)
            log.debug(name)
            d2 = create_desc({'name': name.encode('ascii', 'ignore'),
                              'call_back': getNodeSumStat,
                              'value_type': 'float',
                              'units': 'N',
                              'slope': 'both',
                              'format': '%f',
                              'description': 'Node_Metric',
                              'groups': 'rabbitmq,node'})
            log.debug(d2)
            descriptors.append(d2)
            for node in list_nodes():
                name = "{1}{0}{2}{0}-".format(METRIC_TOKEN_SEPARATOR, metric, node)
                log.debug(name)
                d2 = create_desc({'name': name.encode('ascii', 'ignore'),
                                  'call_back': getNodeStat,
                                  'value_type': 'float',
                                  'units': 'N',
                                  'slope': 'both',
                                  'format': '%f',
                                  'description': 'Node_Metric',
                                  'groups': 'rabbitmq,node'})
                log.debug(d2)
                descriptors.append(d2)

    def buildExchangeDescriptors():
        for vhost, metric in product(vhosts, EXCHANGE_METRICS):
            exchanges = list_exchanges(vhost)
            for exchange in exchanges:
                name = "{1}{0}{2}{0}{3}".format(METRIC_TOKEN_SEPARATOR, metric, exchange, vhost.replace('/', '-'))
                log.debug(name)
                d1 = create_desc({'name': name.encode('ascii', 'ignore'),
                                  'call_back': getExchangeStat,
                                  'value_type': 'float',
                                  'units': 'N',
                                  'slope': 'both',
                                  'format': '%f',
                                  'description': 'Exchange_Metric',
                                  'groups': 'rabbitmq,exchange'})
                log.debug(d1)
                descriptors.append(d1)

    def buildOverviewDescriptors():
        for vhost, metric in product(vhosts, OVERVIEW_METRICS):
            name = "{1}{0}{2}".format(METRIC_TOKEN_SEPARATOR, metric, vhost.replace('/', '-'))
            log.debug(name)
            d1 = create_desc({'name': name.encode('ascii', 'ignore'),
                              'call_back': getOverviewStat,
                              'value_type': 'float',
                              'units': 'N',
                              'slope': 'both',
                              'format': '%f',
                              'description': 'Overview_Metric',
                              'groups': 'rabbitmq,overview'})
            log.debug(d1)
            descriptors.append(d1)

    if 'queues' in STATS:
        buildQueueDescriptors()
    if 'nodes' in STATS:
        buildNodeDescriptors()
    if 'exchanges' in STATS:
        buildExchangeDescriptors()
    if 'overview' in STATS:
        buildOverviewDescriptors()
    # buildTestNodeStat()

    return descriptors


def metric_cleanup():
    logging.shutdown()


def setup_logging(handlers, facility, level):
    global log

    log = logging.getLogger('gmond_python_rabbitmq')
    formatter = logging.Formatter(' | '.join(['%(asctime)s', '%(name)s', '%(levelname)s', '%(message)s']))
    if handlers in ['syslog', 'both']:
        sh = logging.handlers.SysLogHandler(address='/dev/log', facility=facility)
        sh.setFormatter(formatter)
        log.addHandler(sh)
    if handlers in ['stderr', 'both']:
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        log.addHandler(ch)
    lmap = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
        'NOTSET': logging.NOTSET}
    log.setLevel(lmap[level])


def parse_args(argv):
    parser = optparse.OptionParser()
    parser.add_option('--username',
                      action='store', dest='username', default='username',
                      help='')
    parser.add_option('--password',
                      action='store', dest='password', default='password',
                      help='')
    parser.add_option('--admin-host',
                      action='store', dest='admin_host', default='localhost',
                      help='')
    parser.add_option('--admin-port',
                      action='store', dest='admin_port', default=15672,
                      help='')
    parser.add_option('--stats',
                      action='store', dest='stats', default='nodes,queues,exchanges,overview',
                      help='csv of which stats to emit, choies: nodes, queues, exchanges, overview')
    parser.add_option('--vhosts',
                      action='store', dest='vhosts', default='/',
                      help='csv of vhosts')
    parser.add_option('--list-only',
                      action='store_true', dest='list_only', default='defualt',
                      help='List known queues etc instead of printing values in a loop')
    parser.add_option('--log',
                      action='store', dest='log', default='stderr', choices=['stderr', 'syslog', 'both'],
                      help='log to stderr and/or syslog')
    parser.add_option('--log-level',
                      action='store', dest='log_level', default='WARNING',
                      choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'],
                      help='log to stderr and/or syslog')
    parser.add_option('--log-facility',
                      action='store', dest='log_facility', default='user',
                      help='facility to use when using syslog')

    return parser.parse_args(argv)


def main(argv):
    """ used for testing """
    (opts, args) = parse_args(argv)
    setup_logging(opts.log, opts.log_facility, opts.log_level)
    # in config files we use '/' in vhosts names but we should convert '/' to '-' when calculating a metric
    parameters = {"vhost": "/", "username": opts.username, "password": opts.password, "metric_group": "rabbitmq",
                  "zero_rates_when_idle": "yes",
                  "host": opts.admin_host, "port": opts.admin_port,
                  "stats": opts.stats.split(','),
                  "vhosts": opts.vhosts.split(',')}
    descriptors = metric_init(parameters)
    result = refreshStats(stats=parameters['stats'], vhosts=parameters['vhosts'])
    print '***' * 20
    if opts.list_only is True:
        print 'nodes:'
        pprint.pprint(list_nodes())
        print 'exchanges:'
        for vhost in parameters['vhosts']:
            print 'vhost: %s' % vhost
            pprint.pprint(list_exchanges(vhost))
        print 'queues:'
        for vhost in parameters['vhosts']:
            print 'vhost: %s' % vhost
            pprint.pprint(list_queues(vhost))
        return
    try:
        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                if v is None:
                    print 'got None for %s' % d['name']
                else:
                    print 'value for %s is %r' % (d['name'], v)
            time.sleep(5)
            print '----------------------------'
    except KeyboardInterrupt:
        log.debug('KeyboardInterrupt, shutting down...')
        metric_cleanup()

if __name__ == "__main__":
    main(sys.argv[1:])

