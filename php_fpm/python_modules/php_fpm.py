###  This script reports php_fpm status metrics to ganglia.
###
###  This module can monitor multiple php-fpm pools by
###  passing in multiple ports separated by commas into
###  the ports parameter.

###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt

from StringIO import StringIO
from copy import copy
from flup.client.fcgi_app import Record, FCGI_BEGIN_REQUEST, struct, \
    FCGI_BeginRequestBody, FCGI_RESPONDER, FCGI_BeginRequestBody_LEN, FCGI_STDIN, \
    FCGI_DATA, FCGI_STDOUT, FCGI_STDERR, FCGI_END_REQUEST
from pprint import pprint
import flup.client.fcgi_app
import json
import logging
import os
import re
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib2

logging.basicConfig(level=logging.ERROR)

class FCGIApp(flup.client.fcgi_app.FCGIApp):
    ### HACK: reduce the timeout to 2 seconds
    def _getConnection(self):
        if self._connect is not None:
            # The simple case. Create a socket and connect to the
            # application.
            if type(self._connect) is str:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect(self._connect)
            return sock

    ### HACK: workaround for a php-fpm bug: http://bugs.php.net/bug.php?id=53618
    def __call__(self, environ, start_response):
        # For sanity's sake, we don't care about FCGI_MPXS_CONN
        # (connection multiplexing). For every request, we obtain a new
        # transport socket, perform the request, then discard the socket.
        # This is, I believe, how mod_fastcgi does things...

        sock = self._getConnection()

        # Since this is going to be the only request on this connection,
        # set the request ID to 1.
        requestId = 1

        # Begin the request
        rec = Record(FCGI_BEGIN_REQUEST, requestId)
        rec.contentData = struct.pack(FCGI_BeginRequestBody, FCGI_RESPONDER, 0)
        rec.contentLength = FCGI_BeginRequestBody_LEN
        rec.write(sock)

        # Filter WSGI environ and send it as FCGI_PARAMS
        if self._filterEnviron:
            params = self._defaultFilterEnviron(environ)
        else:
            params = self._lightFilterEnviron(environ)
        # TODO: Anything not from environ that needs to be sent also?
        self._fcgiParams(sock, requestId, params)
        self._fcgiParams(sock, requestId, {})

        # Transfer wsgi.input to FCGI_STDIN
        content_length = int(environ.get('CONTENT_LENGTH') or 0)
        while True:
            chunk_size = min(content_length, 4096)
            s = environ['wsgi.input'].read(chunk_size)
            content_length -= len(s)
            rec = Record(FCGI_STDIN, requestId)
            rec.contentData = s
            rec.contentLength = len(s)
            rec.write(sock)

            if not s: break

        # Empty FCGI_DATA stream
        rec = Record(FCGI_DATA, requestId)
        rec.write(sock)

        # Main loop. Process FCGI_STDOUT, FCGI_STDERR, FCGI_END_REQUEST
        # records from the application.
        result = []
        while True:
            inrec = Record()
            inrec.read(sock)
            if inrec.type == FCGI_STDOUT:
                if inrec.contentData:
                    result.append(inrec.contentData)
                else:
                    # TODO: Should probably be pedantic and no longer
                    # accept FCGI_STDOUT records?
                    pass
            elif inrec.type == FCGI_STDERR:
                # Simply forward to wsgi.errors
                environ['wsgi.errors'].write(inrec.contentData)
            elif inrec.type == FCGI_END_REQUEST:
                # TODO: Process appStatus/protocolStatus fields?
                break

        # Done with this transport socket, close it. (FCGI_KEEP_CONN was not
        # set in the FCGI_BEGIN_REQUEST record we sent above. So the
        # application is expected to do the same.)
        sock.close()

        result = ''.join(result)

        # Parse response headers from FCGI_STDOUT
        status = '200 OK'
        headers = []
        pos = 0
        while True:
            eolpos = result.find('\n', pos)
            if eolpos < 0: break
            line = result[pos:eolpos - 1]
            pos = eolpos + 1

            # strip in case of CR. NB: This will also strip other
            # whitespace...
            line = line.strip()

            # Empty line signifies end of headers
            if not line: break

            # TODO: Better error handling
            if  ':' not in line:
                continue

            header, value = line.split(':', 1)
            header = header.strip().lower()
            value = value.strip()

            if header == 'status':
                # Special handling of Status header
                status = value
                if status.find(' ') < 0:
                    # Append a dummy reason phrase if one was not provided
                    status += ' FCGIApp'
            else:
                headers.append((header, value))

        result = result[pos:]

        # Set WSGI status, headers, and return result.
        start_response(status, headers)
        return [result]

_Worker_Thread = None

class UpdatePhpFpmThread(threading.Thread):

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running = False
        self.shuttingdown = False
        self.refresh_rate = int(params['refresh_rate'])
        self.metrics = {}
        self.settings = {}
        self.status_path = str(params['status_path'])
        self.php_fpm_bin = str(params['php_fpm_bin'])
        self.host = str(params['host'])
        self.ports = [ int(p) for p in params['ports'].split(',') ]
        self.prefix = str(params['prefix'])
        self._metrics_lock = threading.Lock()
        self._settings_lock = threading.Lock()

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        self.running = True

        while not self.shuttingdown:
            time.sleep(self.refresh_rate)
            self.refresh_metrics()

        self.running = False

    @staticmethod
    def _get_php_fpm_status_response(status_path, host, port):
        def noop(sc, h): pass

        stat = FCGIApp(connect=(host, port), filterEnviron=False)

        env = {
            'QUERY_STRING': 'json',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_FILENAME': status_path,
            'SCRIPT_NAME': status_path,
            'wsgi.input': StringIO()
        }

        try:
            result = stat(environ=env, start_response=noop)
            logging.debug('status response: ' + str(result))
        except:
            logging.warning(traceback.print_exc(file=sys.stdout))
            raise Exception('Unable to get php_fpm status response from %s:%s %s' % (host, port, status_path))

        if len(result) <= 0:
            raise Exception('php_fpm status response is empty')

        try:
            return json.loads(result[0])
        except ValueError:
            logging.error('Could not deserialize json: ' + str(result))
            raise Exception('Could not deserialize json: ' + str(result))

    def refresh_metrics(self):
        logging.debug('refresh metrics')

        responses = {}

        for port in self.ports:
            try:
                logging.debug('opening URL: %s, host: %s, ports %s' % (self.status_path, self.host, port))
                responses[port] = UpdatePhpFpmThread._get_php_fpm_status_response(self.status_path, self.host, port)
            except:
                logging.warning('error refreshing stats for port ' + str(port))
                logging.warning(traceback.print_exc(file=sys.stdout))

        try:
            self._metrics_lock.acquire()
            self.metrics = {}
            for port, response in responses.iteritems():
                try:
                    prefix = self.prefix + (str(port) + "_" if len(self.ports) > 1 else "")

                    for k, v in response.iteritems():
                        if k == 'accepted conn':
                            self.metrics[prefix + 'accepted_connections'] = int(v)
                        elif k == 'pool':
                            self.metrics[prefix + 'pool_name'] = str(v)
                        elif k == 'process manager':
                            self.metrics[prefix + 'process_manager'] = str(v)
                        elif k == 'idle processes':
                            self.metrics[prefix + 'idle_processes'] = int(v)
                        elif k == 'active processes':
                            self.metrics[prefix + 'active_processes'] = int(v)
                        elif k == 'total processes':
                            self.metrics[prefix + 'total_processes'] = int(v)
                        else:
                            logging.warning('skipped metric: %s = %s' % (k, v))

                    logging.debug('success refreshing stats for port ' + str(port))
                    logging.debug('metrics(' + str(port) + '): ' + str(self.metrics))
                except:
                    logging.warning('error refreshing metrics for port ' + str(port))
                    logging.warning(traceback.print_exc(file=sys.stdout))
        finally:
            self._metrics_lock.release()

        if not self.metrics:
            logging.error('self.metrics is empty or invalid')
            return False

        logging.debug('success refreshing metrics')
        logging.debug('metrics: ' + str(self.metrics))

        return True

    def refresh_settings(self):
        logging.debug(' refreshing server settings')

        try:
            p = subprocess.Popen(executable=self.php_fpm_bin, args=[self.php_fpm_bin, '-v'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()

            self._settings_lock.acquire()
            self.settings = {}
            for line in out.split('\n'):
                if line.startswith('PHP '):
                    key = self.prefix + 'server_version'
                else:
                    continue

                logging.debug('  line: ' + str(line))

                self.settings[key] = line
        except:
            logging.warning('error refreshing settings')
            return False
        finally:
            self._settings_lock.release()

        logging.debug('success refreshing server settings')
        logging.debug('server_settings: ' + str(self.settings))

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

def _create_descriptors(params):
    METRIC_DEFAULTS = {
        'time_max': 60,
        'units': 'processes',
        'groups': 'php_fpm',
        'slope': 'both',
        'value_type': 'uint',
        'format': '%d',
        'description': '',
        'call_back': metric_of
    }

    descriptions = dict(
        pool_name={
            'value_type': 'string',
            'format': '%s',
            'slope': 'zero',
            'units': '',
            'description': 'Pool name'},

        process_manager={
            'value_type': 'string',
            'format': '%s',
            'slope': 'zero',
            'units': '',
            'description': 'Process Manager Type'},

        accepted_connections={
            'units': 'connections',
            'slope': 'positive',
            'description': 'Total number of accepted connections'},

        active_processes={
            'description': 'Current active worker processes'},

        idle_processes={
            'description': 'Current idle worker processes'},

        total_processes={
            'description': 'Total worker processes'})

    prefix = str(params['prefix'])
    ports = params['ports'].split(',')

    descriptors = []
    for port in ports:
        for name, desc in descriptions.iteritems():
            d = copy(desc)

            # include the port as part of the prefix only if there are multiple ports
            d['name'] = prefix + (str(port) + "_" if len(ports) > 1 else "") + str(name)

            [ d.setdefault(key, METRIC_DEFAULTS[key]) for key in METRIC_DEFAULTS.iterkeys() ]
            descriptors.append(d)

    # shared settings between all ports
    descriptors.append({
        'name': prefix + "server_version",
        'value_type': 'string',
        'format': '%s',
        'slope': 'zero',
        'units': '',
        'call_back': setting_of,
        'time_max': 60,
        'groups': 'php_fpm',
        'description': 'PHP-FPM version number'})

    return descriptors

def metric_init(params):
    logging.debug('init: ' + str(params))
    global _Worker_Thread

    if _Worker_Thread is not None:
        raise Exception('Worker thread already exists')

    descriptors = _create_descriptors(params)

    _Worker_Thread = UpdatePhpFpmThread(params)
    _Worker_Thread.refresh_metrics()
    _Worker_Thread.refresh_settings()
    _Worker_Thread.start()

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
    # pass

if __name__ == '__main__':
    from optparse import OptionParser

    try:

        logging.debug('running from cmd line')
        parser = OptionParser()
        parser.add_option('-p', '--path', dest='status_path', default='/status', help='URL for PHP-FPM status stub path')
        parser.add_option('-H', '--host', dest='host', default='localhost', help='PHP-FPM host (comma separated list)')
        parser.add_option('-P', '--ports', dest='ports', default='9000', help='PHP-FPM ports')
        parser.add_option('--php-fpm-bin', dest='php_fpm_bin', default='/usr/sbin/php5-fpm', help='path to PHP-FPM binary')
        parser.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False)
        parser.add_option('-r', '--refresh-rate', dest='refresh_rate', default=15)
        parser.add_option('--prefix', dest='prefix', default='php_fpm_')
        parser.add_option('-d', '--debug', dest='debug', action='store_true', default=False)

        (options, args) = parser.parse_args()

        descriptors = metric_init({
            'status_path': options.status_path,
            'php_fpm_bin': options.php_fpm_bin,
            'refresh_rate': options.refresh_rate,
            'host': options.host,
            'ports': options.ports,
            'prefix': options.prefix
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
