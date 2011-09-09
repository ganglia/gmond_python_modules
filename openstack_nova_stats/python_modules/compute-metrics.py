# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
Ganglia module for getting latest instance count
"""

import os
import time
import threading
import traceback

from nova import flags
from nova import log as logging
from nova import utils
from nova.compute import manager as compute_manager

__worker__ = None
__lock__ = threading.Lock()


class UpdateComputeNodeStatusThread(threading.Thread):
    """Updates compute node status."""

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.manager          = compute_manager.ComputeManager()
        self.running          = False
        self.shuttingdown     = False
        self.refresh_rate     = int(params['refresh_rate'])
        self.status           = {}

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        self.running = True

        while not self.shuttingdown:
            __lock__.acquire()
            self.update_status()
            __lock__.release()

            time.sleep(self.refresh_rate)

        self.running = False

    def update_status(self):
        try:
            self.status['c_instance_count'] = self.manager.get_instance_count()
        except:
            traceback.print_exc()

    def status_of(self, name):
        val = 0
        if name in self.status:
            __lock__.acquire()
            val = self.status[name]
            __lock__.release()
        return val


def status_of(name):
    return __worker__.status_of(name)

def metric_init(params):
    global __worker__

    if not 'refresh_rate' in params:
        params['refresh_rate'] = 60

    __worker__ = UpdateComputeNodeStatusThread(params)
    __worker__.start()

    d1 = {'name': 'c_instance_count',
          'call_back': status_of,
          'time_max': 90,
          'value_type': 'uint',
          'units': '',
          'slope': 'both',
          'format': '%d',
          'description': 'Instance Count'}
    return [d1]

def metric_cleanup():
    """Clean up the metric module."""
    __worker__.shutdown()


if __name__ == '__main__':
    try:
        metric_init({})
        k = 'c_instance_count'
        v = status_of(k)
        print 'value for %s is %u' % (k, v)
    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    finally:
        metric_cleanup()

