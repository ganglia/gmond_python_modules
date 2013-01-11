#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
  ZeroMQ PUB Monitor for Ganglia
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  This is a gmond metric-gathering module which reports a cumulative
  count of messages published by ZeroMQ publishers.

  To test, invoke with one or more pairs of (endpoint name, endpoint
  URI) pairs specifying ZMQ publishers to poll. For example:

    $ python zpubmon.py system-events tcp://localhost:8006

  See README for more details.

  :copyright: (c) 2012 by Ori Livneh <ori@wikimedia.org>
  :license: GNU General Public Licence 2.0 or later

"""
import errno
import logging
import sys
import threading
import time

import zmq


logging.basicConfig(format='[ZMQ] %(asctime)s %(message)s', level=logging.INFO)


def zmq_pub_mon(endpoints, counter):
    """
    Measure throughput of ZeroMQ publishers.

    *endpoints* is a dict that maps human-readable endpoint names to
    endpoint URIs. The names are used as metric names in Ganglia and
    as the ZMQ_IDENTITY of the underlying socket.

    """
    ctx = zmq.Context.instance()
    poller = zmq.Poller()

    for name, uri in endpoints.iteritems():
        logging.info('Registering %s (%s).', name, uri)
        sock = ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.IDENTITY, name)
        sock.connect(uri)
        sock.setsockopt(zmq.SUBSCRIBE, '')
        poller.register(sock, zmq.POLLIN)

    while 1:
        try:
            for socket, _ in poller.poll():
                socket.recv(zmq.NOBLOCK)
                name = socket.getsockopt(zmq.IDENTITY)
                counter[name] += 1
        except zmq.ZMQError as e:
            # Calls interrupted by EINTR should be re-tried.
            if e.errno == errno.EINTR:
                continue
            raise


def metric_init(params):
    """
    Initialize metrics.

    Gmond invokes this method with a dict of arguments specified in
    zpubmon.py. If *params* contains a `groups` key, its value is used
    as the group name in Ganglia (in lieu of the default 'ZeroMQ').
    Other items are interpreted as (name: URI) pairs of ZeroMQ endpoints
    to monitor.

    `metric_init` spawns a worker thread to monitor these endpoints and
    returns a list of metric descriptors.

    """
    groups = params.pop('groups', 'ZeroMQ')
    counter = {name: 0 for name in params}

    thread = threading.Thread(target=zmq_pub_mon, args=(params, counter))
    thread.daemon = True
    thread.start()

    return [{
        'name': name,
        'value_type': 'uint',
        'format': '%d',
        'units': 'events',
        'slope': 'positive',
        'time_max': 20,
        'description': 'messages published',
        'groups': groups,
        'call_back': counter.get,
    } for name in params]


def metric_cleanup():
    """
    Clean-up handler

    Terminates any lingering threads. Gmond calls this function when
    it is shutting down.

    """
    logging.debug('Shutting down.')
    for thread in threading.enumerate():
        if thread.isAlive():
            thread._Thread__stop()  # pylint: disable=W0212


def self_test():
    """
    Perform self-test.

    Parses *argv* as a collection of (name, URI) pairs specifying ZeroMQ
    publishers to be monitored. Message counts are polled and outputted
    every five seconds.

    """
    params = dict(zip(sys.argv[1::2], sys.argv[2::2]))
    if not params:
        print 'Usage: %s NAME URI [NAME URI, ...]' % sys.argv[0]
        print 'Example: %s my-zmq-stream tcp://localhost:8006' % sys.argv[0]
        sys.exit(1)

    descriptors = metric_init(params)

    while 1:
        for descriptor in descriptors:
            name = descriptor['name']
            call_back = descriptor['call_back']
            logging.info('%s: %s', name, call_back(name))
        time.sleep(5)


if __name__ == '__main__':
    self_test()
