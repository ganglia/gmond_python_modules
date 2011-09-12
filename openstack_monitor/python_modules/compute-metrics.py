# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 GridDynamics
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
import sys

from nova import flags

from nova import db
from nova import context
from nova import log as logging
from nova import utils
from nova import version
from nova.compute import manager as compute_manager

__worker__ = None
__lock__ = threading.Lock()

FLAGS = flags.FLAGS
args = ['compute-metrics']
utils.default_flagfile(args=args)
print args
flags.FLAGS(args)
print FLAGS.sql_connection


class UpdateComputeNodeStatusThread(threading.Thread):
    """Updates compute node status."""

    def __init__(self, params):
        print 'starting init'
        threading.Thread.__init__(self)
        self.manager          = compute_manager.ComputeManager()
        self.running          = False
        self.shuttingdown     = False
        self.refresh_rate     = int(params['refresh_rate'])
        self.status           = {}
        self._update_hypervisor()
        print 'finished init'

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
        print 'starting update'
        for updater in (self._update_count, self._update_status):
            try:
                print 'updating using %s' % updater
                updater()
            except:
                traceback.print_exc()
        print 'end update: %s' % self.status

    def status_of(self, name):
        val = None
        if name in self.status:
            __lock__.acquire()
            val = self.status[name]
            __lock__.release()
        return val

    def _update_count(self):
        print 'updating instances'
        self.status['nova_compute_instance_count'] = \
                len(self.manager.driver.list_instances())

    def _update_status(self):
        ctxt = context.get_admin_context()
        services = db.service_get_all_by_host(ctxt, FLAGS.host)
        up_count = 0
        compute_alive = False
        for svc in services:
            now = utils.utcnow()
            delta = now - (svc['updated_at'] or svc['created_at'])
            alive = (delta.seconds <= 15)
            compute_alive = compute_alive or svc['topic'] == 'compute'
            up_count += alive
        self.status['nova_registered_services'] = len(services)
        self.status['nova_compute_is_running'] = compute_alive and 'OK' or 'NO'
        self.status['nova_running_services'] = up_count

    def _update_hypervisor(self):
        status = type(self.manager.driver).__name__
        try:
            hyperv = self.manager.driver.get_hypervisor_type()
            status += ' with %s' % (hyperv)
        except:
            pass
        self.status['nova_compute_driver'] = status


def version_handler(name):
    return version.canonical_version_string()


def hypervisor_getter(worker):
    global _hypervisor_name
    return _hypervisor_name

def metric_init(params):
    global __worker__

    if not 'refresh_rate' in params:
        params['refresh_rate'] = 60

    __worker__ = UpdateComputeNodeStatusThread(params)
    __worker__.start()
    status_of = __worker__.status_of

    instances = {'name': 'nova_compute_instance_count',
                 'call_back': status_of,
                 'time_max': 90,
                 'value_type': 'uint',
                 'units': '',
                 'slope': 'both',
                 'format': '%d',
                 'description': 'Openstack Instance Count',
                 'groups': 'openstack-compute'}

    version = {'name': 'openstack_version',
               'call_back': version_handler,
               'time_max': 90,
               'value_type': 'string',
               'units': '',
               'slope': 'zero',
               'format': '%s',
               'description': 'Openstack Version',
               'groups': 'openstack-compute'}

    compute  = {'name': 'nova_compute_is_running',
               'call_back': status_of,
               'time_max': 90,
               'value_type': 'string',
               'units': '',
               'slope': 'zero',
               'format': '%s',
               'description': 'Openstack Nova compute is running',
               'groups': 'openstack-compute'}

    hypervisor  = {'name': 'nova_compute_driver',
               'call_back': status_of,
               'time_max': 90,
               'value_type': 'string',
               'units': '',
               'slope': 'zero',
               'format': '%s',
               'description': 'Openstack Nova compute driver',
               'groups': 'openstack-compute'}

    run_services = {'name': 'nova_running_services',
                 'call_back': status_of,
                 'time_max': 90,
                 'value_type': 'uint',
                 'units': '',
                 'slope': 'both',
                 'format': '%d',
                 'description': 'Openstack Nova running services',
                 'groups': 'openstack-compute'}

    reg_services = {'name': 'nova_registered_services',
                 'call_back': status_of,
                 'time_max': 90,
                 'value_type': 'uint',
                 'units': '',
                 'slope': 'both',
                 'format': '%d',
                 'description': 'Openstacl Nova Registered services',
                 'groups': 'openstack-compute'}

    return [instances, version, compute, hypervisor,
            run_services, reg_services]

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

