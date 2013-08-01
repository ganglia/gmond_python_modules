###  This script reports jenkins metrics to ganglia.

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
import base64

logging.basicConfig(level=logging.ERROR)

_Worker_Thread = None

class UpdateJenkinsThread(threading.Thread):

  def __init__(self, params):
    threading.Thread.__init__(self)
    self.running = False
    self.shuttingdown = False
    self.metrics = {}
    self.settings = {}
    self.refresh_rate = 60
    self.base_url = params['base_url']
    self.username = params['username']
    self.apitoken = params['apitoken']
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
  def _get_jenkins_statistics(url, username, apitoken):

    url += '/api/json'
    url += '?tree=jobs[color],overallLoad[busyExecutors[min[latest]],queueLength[min[latest]],totalExecutors[min[latest]]]'


    if username and apitoken:
      url += '&token=' + apitoken
      request = urllib2.Request(url)
      base64string = base64.encodestring('%s:%s' % (username, apitoken)).replace('\n','')
      request.add_header("Authorization", "Basic %s" % base64string)
      c = urllib2.urlopen(request, None, 2)
    else:
      c = urllib2.urlopen(url, None, 2)

    json_data = c.read()
    c.close()

    data = json.loads(json_data)

    result = {}
    result['jenkins_overallload_busy_executors'] = data['overallLoad']['busyExecutors']['min']['latest']
    result['jenkins_overallload_queue_length'] = data['overallLoad']['queueLength']['min']['latest']
    result['jenkins_overallload_total_executors'] = data['overallLoad']['totalExecutors']['min']['latest']
    result['jenkins_jobs_total'] = len(data['jobs'])
    result['jenkins_jobs_red'] = result['jenkins_jobs_yellow'] = result['jenkins_jobs_grey'] = result['jenkins_jobs_disabled'] = result['jenkins_jobs_aborted'] = result['jenkins_jobs_notbuilt'] = result['jenkins_jobs_blue'] = 0

    # Possible values: http://javadoc.jenkins-ci.org/hudson/model/BallColor.html
    colors = ['red', 'yellow', 'grey', 'disabled', 'aborted', 'notbuilt', 'blue']
    for color in colors:
      result['jenkins_jobs_' + color] = 0
    for job in data['jobs']:
      color = job['color']
      for c in colors:
        if color == c or color == c + '_anime':
          result['jenkins_jobs_' + c] += 1
    return result

  def refresh_metrics(self):
    logging.debug('refresh metrics')

    try:
      logging.debug(' opening URL: ' + str(self.base_url))
      data = UpdateJenkinsThread._get_jenkins_statistics(self.base_url, self.username, self.apitoken)
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
    'units': 'jobs',
    'groups': 'jenkins',
    'slope': 'both',
    'value_type': 'uint',
    'format': '%d',
    'description': '',
    'call_back': metric_of
  }

  descriptions = dict(
    jenkins_overallload_busy_executors = {
      'value_type': 'float',
      'format': '%.3f',
      'units': 'executors',
      'description': 'Number of busy executors (master and slaves)'},
    jenkins_overallload_queue_length = {
      'value_type': 'float',
      'format': '%.3f',
      'units': 'queued items',
      'description': 'Length of the queue (master and slaves)'},
    jenkins_overallload_total_executors = {
      'value_type': 'float',
      'format': '%.3f',
      'units': 'executors',
      'description': 'Number of executors (master and slaves)'},
    jenkins_jobs_total = {
      'description': 'Total number of jobs'},
    jenkins_jobs_blue = {
      'description': 'Blue jobs'},
    jenkins_jobs_red = {
      'description': 'Red jobs'},
    jenkins_jobs_yellow = {
      'description': 'Yellow jobs'},
    jenkins_jobs_grey = {
      'description': 'Grey jobs'},
    jenkins_jobs_disabled = {
      'description': 'Disabled jobs'},
    jenkins_jobs_aborted = {
      'description': 'Aborted jobs'},
    jenkins_jobs_notbuilt = {
      'description': 'Not-built jobs'})

  if _Worker_Thread is not None:
    raise Exception('Worker thread already exists')

  _Worker_Thread = UpdateJenkinsThread(params)
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
    parser.add_option('-u', '--URL', dest='base_url', default='http://127.0.0.1:8080', help='Base-URL for jenkins api (default: http://127.0.0.1:8080)')
    parser.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False)
    parser.add_option('-d', '--debug', dest='debug', action='store_true', default=False)
    parser.add_option('-n', '--username', dest='username', default='', help='Your Jenkins username (default: empty)')
    parser.add_option('-a', '--apitoken', dest='apitoken', default='', help='Your API token (default: empty)')

    (options, args) = parser.parse_args()

    descriptors = metric_init({
      'base_url': options.base_url,
      'username': options.username,
      'apitoken': options.apitoken,
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
