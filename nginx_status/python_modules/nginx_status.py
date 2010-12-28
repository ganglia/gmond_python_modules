###  This script reports nginx status stub metrics to ganglia.

###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt
import logging
import os
import re
import subprocess
import sys
import threading
import time
import traceback
import urllib2

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/gmond.log', filemode='w')
logging.debug('starting up')

_Worker_Thread = None
_Lock = threading.Lock() # synchronization lock

class UpdateNginxThread(threading.Thread):

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running = False
        self.shuttingdown = False
        self.refresh_rate = int(params['refresh_rate'])
        self.metrics = {}
        self.status_url = params['status_url']
        self.nginx_bin = params['nginx_bin']

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        global _Lock

        self.running = True

        while not self.shuttingdown:
            _Lock.acquire()
            self.refresh_metrics()
            _Lock.release()
            time.sleep(self.refresh_rate)

        self.running = False

    def get_nginx_status_stub_response(self, url):
        c = urllib2.urlopen(url)
        data = c.read()
        c.close()

        matchActive = re.search(r'Active connections:\s+(\d+)', data)
        matchHistory = re.search(r'\s*(\d+)\s+(\d+)\s+(\d+)', data)
        matchCurrent = re.search(r'Reading:\s*(\d+)\s*Writing:\s*(\d+)\s*'
            'Waiting:\s*(\d+)', data)

        if not matchActive or not matchHistory or not matchCurrent:
            raise Exception('Unable to parse {0}' . format(url))

        result = {}
        result['nginx_active_connections'] = int(matchActive.group(1))

        result['nginx_accepts'] = int(matchHistory.group(1))
        result['nginx_handled'] = int(matchHistory.group(2))
        result['nginx_requests'] = int(matchHistory.group(3))

        result['nginx_reading'] = int(matchCurrent.group(1))
        result['nginx_writing'] = int(matchCurrent.group(2))
        result['nginx_waiting'] = int(matchCurrent.group(3))

        return result

    def refresh_metrics(self):
        logging.debug('refresh metrics')

        try:
            self.metrics = {}
            logging.debug(' opening URL: ' + str(self.status_url))

            data = self.get_nginx_status_stub_response(self.status_url)

            for k, v in data.items():
                self.metrics[k] = v
        except:
            logging.warning('error refreshing stats')
            logging.warning(traceback.print_exc(file=sys.stdout))
            return False

        if not self.metrics:
            logging.warning('error refreshing stats')
            return False

        logging.debug('success refreshing stats')
        logging.debug('metrics: ' + str(self.metrics))

        return True

    def refresh_server_settings(self):
        logging.debug(' refreshing nginx_server_version')

        try:
            p = subprocess.Popen(executable=self.nginx_bin, args=[self.nginx_bin, '-v'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()

            for line in err.split('\n'):
                if 'nginx version:' in line:
                    key = 'nginx_server_version'
                else:
                    continue

                line = line.split(': ')
                logging.debug('  line: ' + str(line))

                if len(line) == 2:
                    self.metrics[key] = line[1]
        except:
            logging.warning('error refreshing stats (server_version)')
            return False

        logging.debug('success refreshing server stats')
        logging.debug('server_settings: ' + str(self.metrics))

        return True

    def metric_of(self, name):
        logging.debug('getting stat: ' + name)
        global _Lock

        if name in self.metrics:
            try:
                _Lock.acquire()
                return self.metrics[name]
            except:
                logging.warning('failed to fetch ' + name)
                return 0
            finally:
                _Lock.release()

def metric_init(params):
    logging.debug('init: ' + str(params))
    global _Worker_Thread

    METRIC_DEFAULTS = {
        'time_max': 60,
        'units': 'connections',
        'groups': 'nginx',
        'slope': 'both',
        'value_type': 'uint',
        'format': '%d',
        'description': '',
        'call_back': metric_of
    }

    descriptions = dict(
        nginx_server_version={
            'value_type': 'string',
            'units': '',
            'format': '%s',
            'slope': 'zero',
            'description': 'Nginx version number'},

        nginx_active_connections={
            'description': 'Total number of active connections'},

        nginx_accepts={
            'slope': 'positive',
            'description': 'Total number of accepted connections'},

        nginx_handled={
            'slope': 'positive',
            'description': 'Total number of handled connections'},

        nginx_requests={
            'slope': 'positive',
            'units': 'requests',
            'description': 'Total number of requests'},

        nginx_reading={
            'description': 'Current connection in the reading state'},

        nginx_writing={
            'description': 'Current connection in the writing state'},

        nginx_waiting={
            'description': 'Current connection in the waiting state'})

    if _Worker_Thread is not None:
        raise Exception('Worker thread already exists')

    _Worker_Thread = UpdateNginxThread(params)
    _Worker_Thread.start()
    _Worker_Thread.refresh_metrics()
    _Worker_Thread.refresh_server_settings()

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

def metric_cleanup():
    global _Worker_Thread
    if _Worker_Thread is not None:
        _Worker_Thread.shutdown()
    logging.shutdown()
    # pass

if __name__ == '__main__':
    from optparse import OptionParser

    try:

        logging.debug('running from cmd line')
        parser = OptionParser()
        parser.add_option('-u', '--URL', dest='status_url', default='http://localhost/nginx_status', help='URL for Nginx status stub page')
        parser.add_option('--nginx-bin', dest='nginx_bin', default='/usr/sbin/nginx', help='path to nginx')
        parser.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False)
        parser.add_option('-r', '--refresh-rate', dest='refresh_rate', default=15)
        parser.add_option('-d', '--debug', dest='debug', action='store_true', default=False)

        (options, args) = parser.parse_args()

        descriptors = metric_init({
            'status_url': options.status_url,
            'nginx_bin': options.nginx_bin,
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
