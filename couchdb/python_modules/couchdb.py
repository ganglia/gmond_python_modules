###  This script reports couchdb metrics to ganglia.

###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt
import logging
import os
import subprocess
import sys
import threading
import time
import traceback
import urllib2
import json

logging.basicConfig(level=logging.ERROR)

_Worker_Thread = None

class UpdateCouchdbThread(threading.Thread):

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running = False
        self.shuttingdown = False
        self.refresh_rate = int(params['refresh_rate'])
        self.metrics = {}
        self.settings = {}
        self.stats_url = params['stats_url']
        self._metrics_lock = threading.Lock()
        self._settings_lock = threading.Lock()

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        global _Lock

        self.running = True

        while not self.shuttingdown:
            time.sleep(self.refresh_rate)
            self.refresh_metrics()

        self.running = False

    @staticmethod
    def _get_couchdb_stats(url, refresh_rate):
        if refresh_rate == 60 or refresh_rate == 300 or refresh_rate == 900:
            url += '?range=' + str(refresh_rate)
        else:
            logging.warning('The specified refresh_rate of %d is invalid and has been substituted with 60!' % refresh_rate)
            url += '?range=60'

        # Set time out for urlopen to 2 seconds otherwise we run into the possibility of hosing gmond
        c = urllib2.urlopen(url, None, 2)
        json_data = c.read()
        c.close()

        data = json.loads(json_data)
        couchdb = data['couchdb']
        httpd = data['httpd']
        request_methods = data['httpd_request_methods']
        status_codes = data['httpd_status_codes']

        result = {}
        for first_level_key in data:
            for second_level_key in data[first_level_key]:
                value = data[first_level_key][second_level_key]['current']
                if value is None:
                    value = 0
                else:
                    if second_level_key in ['open_databases', 'open_os_files', 'clients_requesting_changes']:
                        print second_level_key + ': ' + str(value)
                        value = int(value)
                    else:
                        # We need to devide by the range as couchdb provides no per second values
                        value = float(value) / refresh_rate
                result['couchdb_' + first_level_key + '_' + second_level_key ] = value

        return result

    def refresh_metrics(self):
        logging.debug('refresh metrics')

        try:
            logging.debug(' opening URL: ' + str(self.stats_url))
            data = UpdateCouchdbThread._get_couchdb_stats(self.stats_url, self.refresh_rate)
        except:
            logging.warning('error refreshing metrics')
            logging.warning(traceback.print_exc(file=sys.stdout))

        try:
            self._metrics_lock.acquire()
            self.metrics = {}
            for k, v in data.items():
                self.metrics[k] = v
        except:
            logging.warning('error refreshing metrics')
            logging.warning(traceback.print_exc(file=sys.stdout))
            return False

        finally:
            self._metrics_lock.release()

        if not self.metrics:
            logging.warning('error refreshing metrics')
            return False

        logging.debug('success refreshing metrics')
        logging.debug('metrics: ' + str(self.metrics))

        return True

    def metric_of(self, name):
        logging.debug('getting metric: ' + name)

        try:
            if name in self.metrics:
                try:
                    self._metrics_lock.acquire()
                    logging.debug('metric: %s = %s' % (name, self.metrics[name]))
                    return self.metrics[name]
                finally:
                    self._metrics_lock.release()
        except:
            logging.warning('failed to fetch ' + name)
            return 0

    def setting_of(self, name):
        logging.debug('getting setting: ' + name)

        try:
            if name in self.settings:
                try:
                    self._settings_lock.acquire()
                    logging.debug('setting: %s = %s' % (name, self.settings[name]))
                    return self.settings[name]
                finally:
                    self._settings_lock.release()
        except:
            logging.warning('failed to fetch ' + name)
            return 0

def metric_init(params):
    logging.debug('init: ' + str(params))
    global _Worker_Thread

    METRIC_DEFAULTS = {
        'units': 'requests/s',
        'groups': 'couchdb',
        'slope': 'both',
        'value_type': 'float',
        'format': '%.3f',
        'description': '',
        'call_back': metric_of
    }

    descriptions = dict(
        couchdb_couchdb_auth_cache_hits={
            'units': 'hits/s',
            'description': 'Number of authentication cache hits'},
        couchdb_couchdb_auth_cache_misses={
            'units': 'misses/s',
            'description': 'Number of authentication cache misses'},
        couchdb_couchdb_database_reads={
            'units': 'reads/s',
            'description': 'Number of times a document was read from a database'},
        couchdb_couchdb_database_writes={
            'units': 'writes/s',
            'description': 'Number of times a document was changed'},
        couchdb_couchdb_open_databases={
            'value_type': 'uint',
            'format': '%d',
            'units': 'databases',
            'description': 'Number of open databases'},
        couchdb_couchdb_open_os_files={
            'value_type': 'uint',
            'format': '%d',
            'units': 'files',
            'description': 'Number of file descriptors CouchDB has open'},
        couchdb_couchdb_request_time={
            'units': 'ms',
            'description': 'Request time'},
        couchdb_httpd_bulk_requests={
            'description': 'Number of bulk requests'},
        couchdb_httpd_clients_requesting_changes={
            'value_type': 'uint',
            'format': '%d',
            'units': 'clients',
            'description': 'Number of clients for continuous _changes'},
        couchdb_httpd_requests={
            'description': 'Number of HTTP requests'},
        couchdb_httpd_temporary_view_reads={
            'units': 'reads',
            'description': 'Number of temporary view reads'},
        couchdb_httpd_view_reads={
            'description': 'Number of view reads'},
        couchdb_httpd_request_methods_COPY={
            'description': 'Number of HTTP COPY requests'},
        couchdb_httpd_request_methods_DELETE={
            'description': 'Number of HTTP DELETE requests'},
        couchdb_httpd_request_methods_GET={
            'description': 'Number of HTTP GET requests'},
        couchdb_httpd_request_methods_HEAD={
            'description': 'Number of HTTP HEAD requests'},
        couchdb_httpd_request_methods_POST={
            'description': 'Number of HTTP POST requests'},
        couchdb_httpd_request_methods_PUT={
            'description': 'Number of HTTP PUT requests'},
        couchdb_httpd_status_codes_200={
            'units': 'responses/s',
            'description': 'Number of HTTP 200 OK responses'},
        couchdb_httpd_status_codes_201={
            'units': 'responses/s',
            'description': 'Number of HTTP 201 Created responses'},
        couchdb_httpd_status_codes_202={
            'units': 'responses/s',
            'description': 'Number of HTTP 202 Accepted responses'},
        couchdb_httpd_status_codes_301={
            'units': 'responses/s',
            'description': 'Number of HTTP 301 Moved Permanently responses'},
        couchdb_httpd_status_codes_304={
            'units': 'responses/s',
            'description': 'Number of HTTP 304 Not Modified responses'},
        couchdb_httpd_status_codes_400={
            'units': 'responses/s',
            'description': 'Number of HTTP 400 Bad Request responses'},
        couchdb_httpd_status_codes_401={
            'units': 'responses/s',
            'description': 'Number of HTTP 401 Unauthorized responses'},
        couchdb_httpd_status_codes_403={
            'units': 'responses/s',
            'description': 'Number of HTTP 403 Forbidden responses'},
        couchdb_httpd_status_codes_404={
            'units': 'responses/s',
            'description': 'Number of HTTP 404 Not Found responses'},
        couchdb_httpd_status_codes_405={
            'units': 'responses/s',
            'description': 'Number of HTTP 405 Method Not Allowed responses'},
        couchdb_httpd_status_codes_409={
            'units': 'responses/s',
            'description': 'Number of HTTP 409 Conflict responses'},
        couchdb_httpd_status_codes_412={
            'units': 'responses/s',
            'description': 'Number of HTTP 412 Precondition Failed responses'},
        couchdb_httpd_status_codes_500={
            'units': 'responses/s',
            'description': 'Number of HTTP 500 Internal Server Error responses'})

    if _Worker_Thread is not None:
        raise Exception('Worker thread already exists')

    _Worker_Thread = UpdateCouchdbThread(params)
    _Worker_Thread.refresh_metrics()
    _Worker_Thread.start()

    descriptors = []

    for name, desc in descriptions.iteritems():
        d = desc.copy()
        d['name'] = str(name)
        [ d.setdefault(key, METRIC_DEFAULTS[key]) for key in METRIC_DEFAULTS.iterkeys() ]
        descriptors.append(d)

    return descriptors

def metric_of(name):
    global _Worker_Thread
    return _Worker_Thread.metric_of(name)

def setting_of(name):
    global _Worker_Thread
    return _Worker_Thread.setting_of(name)

def metric_cleanup():
    global _Worker_Thread
    if _Worker_Thread is not None:
        _Worker_Thread.shutdown()
    logging.shutdown()
    pass

if __name__ == '__main__':
    from optparse import OptionParser

    try:
        logging.debug('running from the cmd line')
        parser = OptionParser()
        parser.add_option('-u', '--URL', dest='stats_url', default='http://127.0.0.1:5984/_stats', help='URL for couchdb stats page')
        parser.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False)
        parser.add_option('-r', '--refresh-rate', dest='refresh_rate', default=60)
        parser.add_option('-d', '--debug', dest='debug', action='store_true', default=False)

        (options, args) = parser.parse_args()

        descriptors = metric_init({
            'stats_url': options.stats_url,
            'refresh_rate': options.refresh_rate
        })

        if options.debug:
            from pprint import pprint
            pprint(descriptors)

        for d in descriptors:
            v = d['call_back'](d['name'])

            if not options.quiet:
                print ' {0}: {1} {2} [{3}]' . format(d['name'], v, d['units'], d['description'])

        os._exit(1)

    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except StandardError:
        traceback.print_exc()
        os._exit(1)
    finally:
        metric_cleanup()
