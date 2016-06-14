from influxdb import InfluxDBClient
import functools, time, re, logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s\t - %(message)s")
logging.debug('Process starting up..')

# Cache for influxdb query values, this prevents opening db connections for each metric_handler callback
class Cache(object):
    def __init__(self, expiry):
        self.expiry = expiry
        self.curr_time = 0
        self.last_time = 0
        self.last_value = None

    def __call__(self, func):
        @functools.wraps(func)
        def deco(*args, **kwds):
            self.curr_time = time.time()
            if self.curr_time - self.last_time > self.expiry:
                self.last_value = func(*args, **kwds)
                self.last_time = self.curr_time
            return self.last_value
        return deco

# Queries update the influx_metrics dict with their values based on cache interval
@Cache(60)
def influx_metrics_queries():
    influx_metrics = {}
    mapping = {}

    global client
    result = client.query("SHOW STATS;")
    items = result.items()
    for item in items:
        group = item[0][0]
        for point in list(item[1]):
            for key in point:
                mapping['influx'+'/'+group+'/'+key] = point[key]

    influx_metrics.update(
        mapping
    )
    return influx_metrics

# Metric handler uses dictionary influx_metrics keys to return values from queries based on metric name
def metric_handler(name):
    influx_metrics = influx_metrics_queries()
    return int(influx_metrics[name])

def parse_influx_version(version):
    match = re.match(r'(?P<major>\d+)\.(?P<minor>(\d+))\.(?P<patch>(\d+))(\.\d+)*', version)
    return int(match.group('major')), int(match.group('minor')), int(match.group('patch'))

# Metric descriptors are initialized here
def metric_init(params):
    HOST = str(params.get('host'))
    PORT = str(params.get('port'))
    USER = str(params.get('username'))
    PASSWORD = str(params.get('password'))

    global client
    client = InfluxDBClient(HOST, PORT, USER, PASSWORD)

    result = client.query("SHOW DIAGNOSTICS;")
    try:
        version = list(result[("build", None)])[0]["Version"]
    except:
        logging.info("Version information is not available..")
        return []

    major, minor, patch = parse_influx_version(version)
    if not ((major > 0)
            or (major == 0 and minor > 9)
            or (major == 0 and minor == 9 and patch >= 4)):
        logging.info("This plugin is only supported for version 0.9.4+")
        return []

    descriptors = [
        {'name':'influx/httpd/authFail', 'units':'Count', 'slope':'positive', 'description':''},
        {'name':'influx/httpd/pingReq', 'units':'Count', 'slope':'positive', 'description':''},
        {'name':'influx/httpd/queryReq', 'units':'Count', 'slope':'positive', 'description':'Number of queries received'},
        {'name':'influx/httpd/queryRespBytes', 'units':'Bytes', 'slope':'positive', 'description':'Number of bytes returned'},
        {'name':'influx/httpd/req', 'units':'Count', 'slope':'positive', 'description':''},
        {'name':'influx/shard/fieldsCreate', 'units':'Count', 'slope':'positive', 'description':''},
        {'name':'influx/shard/seriesCreate', 'units':'Count', 'slope':'positive', 'description':''},
        {'name':'influx/shard/writePointsOk', 'units':'Count', 'slope':'positive', 'description':''},
        {'name':'influx/shard/writeReq', 'units':'Count', 'slope':'positive', 'description':''},
        {'name':'influx/subscriber/pointsWritten', 'units':'Count', 'slope':'positive', 'description':''},
        {'name':'influx/write/pointReq', 'units':'Count', 'slope':'positive', 'description':''},
        {'name':'influx/write/pointReqLocal', 'units':'Count', 'slope':'positive', 'description':''},
        {'name':'influx/write/req', 'units':'Count', 'slope':'positive', 'description':''},
        {'name':'influx/write/subWriteOk', 'units':'Count', 'slope':'positive', 'description':''},
        {'name':'influx/write/writeOk', 'units':'Count', 'slope':'positive', 'description':''},
        {'name':'influx/runtime/Alloc', 'units':'Bytes', 'slope':'both', 'description':'Bytes allocated and not yet freed'},
        {'name':'influx/runtime/Frees', 'units':'Count', 'slope':'positive', 'description':'Number of frees'},
        {'name':'influx/runtime/HeapAlloc', 'units':'Bytes', 'slope':'both', 'description':'Bytes allocated and not yet freed'},
        {'name':'influx/runtime/HeapIdle', 'units':'Bytes', 'slope':'both', 'description':'Bytes in idle spans'},
        {'name':'influx/runtime/HeapInUse', 'units':'Bytes', 'slope':'both', 'description':'Bytes in non-idle span'},
        {'name':'influx/runtime/HeapObjects', 'units':'total', 'slope':'both', 'description':'Total number of allocated objects'},
        {'name':'influx/runtime/HeapReleased', 'units':'Bytes', 'slope':'both', 'description':'Bytes released to the OS'},
        {'name':'influx/runtime/HeapSys', 'units':'Bytes', 'slope':'both', 'description':'Bytes obtained from system'},
        {'name':'influx/runtime/Lookups', 'units':'Count', 'slope':'positive', 'description':'Number of pointer lookups'},
        {'name':'influx/runtime/Mallocs', 'units':'Count', 'slope':'positive', 'description':'Number of mallocs'},
        {'name':'influx/runtime/NumGC', 'units':'Count', 'slope':'positive', 'description':'The number of garbage collector'},
        {'name':'influx/runtime/NumGoroutine', 'units':'Count', 'slope':'both', 'description':'The number of goroutines that currently exist'},
        {'name':'influx/runtime/PauseTotalNs', 'units':'total', 'slope':'positive', 'description':''},
        {'name':'influx/runtime/Sys', 'units':'Bytes', 'slope':'positive', 'description':'Bytes obtained from system'},
        {'name':'influx/runtime/TotalAlloc', 'units':'Bytes', 'slope':'positive', 'description':'Bytes allocated (even if freed)'},
    ]

    for d in descriptors:
        # Add default values to dictionary
        d.update({'call_back': metric_handler, 'time_max': 90, 'value_type': 'uint', 'format': '%d', 'groups': 'InfluxDB'})

    return descriptors

# ganglia requires metric cleanup
def metric_cleanup():
    '''Clean up the metric module.'''
    pass

# this code is for debugging and unit testing
if __name__ == '__main__':
    descriptors = metric_init({})
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print 'value for %s is %u' % (d['name'],  v)
        time.sleep(60)

