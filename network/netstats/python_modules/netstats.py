import sys
import re
import time

PARAMS = {}

NAME_PREFIX = 'tcpext_'

METRICS = {
    'time' : 0,
    'data' : {}
}
LAST_METRICS = dict(METRICS)
METRICS_CACHE_MAX = 5

tcpext_stats_pos = {
  'syncookiessent' : 1,
  'syncookiesrecv' : 2,
  'syncookiesfailed' : 3,
  'embryonicrsts' : 4,
  'prunecalled' : 5,
  'rcvpruned' : 6,
  'ofopruned' : 7,
  'outofwindowicmps' : 8,
  'lockdroppedicmps' : 9,
  'arpfilter' : 10,
  'tw' : 11,
  'twrecycled' : 12,
  'twkilled' : 13,
  'pawspassive' : 14,
  'pawsactive' : 15,
  'pawsestab' : 16,
  'delayedacks' : 17,
  'delayedacklocked' : 18,
  'delayedacklost' : 19,
  'listenoverflows' : 20,
  'listendrops' : 21,
  'tcpprequeued' : 22,
  'tcpdirectcopyfrombacklog' : 23,
  'tcpdirectcopyfromprequeue' : 24,
  'tcpprequeuedropped' : 25,
  'tcphphits' : 26,
  'tcphphitstouser' : 27,
  'tcppureacks' : 28,
  'tcphpacks' : 29,
  'tcprenorecovery' : 30,
  'tcpsackrecovery' : 31,
  'tcpsackreneging' : 32,
  'tcpfackreorder' : 33,
  'tcpsackreorder' : 34,
  'tcprenoreorder' : 35,
  'tcptsreorder' : 36,
  'tcpfullundo' : 37,
  'tcppartialundo' : 38,
  'tcpdsackundo' : 39,
  'tcplossundo' : 40,
  'tcploss' : 41,
  'tcplostretransmit' : 42,
  'tcprenofailures' : 43,
  'tcpsackfailures' : 44,
  'tcplossfailures' : 45,
  'tcpfastretrans' : 46,
  'tcpforwardretrans' : 47,
  'tcpslowstartretrans' : 48,
  'tcptimeouts' : 49,
  'tcprenorecoveryfail' : 50,
  'tcpsackrecoveryfail' : 51,
  'tcpschedulerfailed' : 52,
  'tcprcvcollapsed' : 53,
  'tcpdsackoldsent' : 54,
  'tcpdsackofosent' : 55,
  'tcpdsackrecv' : 56,
  'tcpdsackoforecv' : 57,
  'tcpabortonsyn' : 58,
  'tcpabortondata' : 59,
  'tcpabortonclose' : 60,
  'tcpabortonmemory' : 61,
  'tcpabortontimeout' : 62,
  'tcpabortonlinger' : 63,
  'tcpabortfailed' : 64,
  'tcpmemorypressures' : 65,
  'tcpsackdiscard' : 66,
  'tcpdsackignoredold' : 67,
  'tcpdsackignorednoundo' : 68,
  'tcpspuriousrtos' : 69,
  'tcpmd5notfound' : 70,
  'tcpmd5unexpected' : 71,
  'tcpsackshifted' : 72,
  'tcpsackmerged' : 73,
  'tcpsackshiftfallback' : 74,
  'tcpbacklogdrop' : 75,
  'tcpminttldrop' : 76,
  'tcpdeferacceptdrop' : 77
    }


###############################################################################
# Explanation of metrics in /proc/meminfo can be found here
#
# http://www.redhat.com/advice/tips/meminfo.html
# and
# http://unixfoo.blogspot.com/2008/02/know-about-procmeminfo.html
# and
# http://www.centos.org/docs/5/html/5.2/Deployment_Guide/s2-proc-meminfo.html
###############################################################################
tcpext_file = "/proc/net/netstat"


def get_metrics():
    """Return all metrics"""

    global METRICS, LAST_METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

	try:
	    file = open(tcpext_file, 'r')
    
	except IOError:
	    return 0

        # convert to dict
        metrics = {}
        for line in file:
	    if re.match("TcpExt: [0-9]", line):
		print line
                metrics = re.split("\s+", line)

        # update cache
        LAST_METRICS = dict(METRICS)
        METRICS = {
            'time': time.time(),
            'data': metrics
        }

    return [METRICS, LAST_METRICS]

def get_value(name):
    """Return a value for the requested metric"""

    metrics = get_metrics()[0]

    name = name[len(NAME_PREFIX):] # remove prefix from name

    try:
        result = metrics['data'][name]
    except StandardError:
        result = 0

    return result


def get_delta(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    name = name[len(NAME_PREFIX):] # remove prefix from name
    index = tcpext_stats_pos[name]

    try:
      delta = (float(curr_metrics['data'][index]) - float(last_metrics['data'][index])) /(curr_metrics['time'] - last_metrics['time'])
      if delta < 0:
	print name + " is less 0"
	delta = 0
    except KeyError:
      delta = 0.0      

    return delta


def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_init(params):
    global descriptors, metric_map, Desc_Skel

    descriptors = []

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_delta,
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%.4f',
        'units'       : 'count/s',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'tcp_extended',
        }

    for item in tcpext_stats_pos:
        descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + item,
                "description": item,
                }))

    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    descriptors = metric_init(PARAMS)
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print '%s = %s' % (d['name'],  v)
        print 'Sleeping 15 seconds'
        time.sleep(15)
