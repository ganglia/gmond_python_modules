#!/usr/bin/env python


import sys
import traceback
import os
import time
import socket
import select


descriptors = list()
PARAMS = {
    'host': '127.0.0.1',
    'port': 22133,
    'timeout': 2,
}
METRICS = {
    'time' : 0,
    'data' : {}
}
METRICS_CACHE_MAX = 5

def get_metrics():
    global METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        msg  = ''

        try:
            sock.connect((PARAMS['host'], int(PARAMS['port'])))
            sock.send('stats\r\n')

            while True:
                rfd, wfd, xfd = select.select([sock], [], [], PARAMS['timeout'])
                if not rfd:
                    print >>sys.stderr, 'ERROR: select timeout'
                    break

                for fd in rfd:
                    if fd == sock:
                        data = fd.recv(8192)
                        msg += data

                if msg.find('END') != -1:
                    break

            sock.close()
        except socket.error, e:
            print >>sys.stderr, 'ERROR: %s' % e

        _metrics = {}
        for m in msg.split('\r\n'):
            d = m.split(' ')
            if len(d) == 3 and d[0] == 'STAT':
                new_value = d[2]
                try:
                    new_value = int(d[2])
                except ValueError:
                    pass
                _metrics[PARAMS['metrix_prefix'] + '_' + d[1]] = new_value

        METRICS = {
            'time': time.time(),
            'data': _metrics
        }

    return METRICS

def metric_of(name):
    curr_metrics = get_metrics()
    if name in curr_metrics['data']:
        return curr_metrics['data'][name]
    return 0

def metric_init(lparams):
    global descriptors, PARAMS

    for key in lparams:
        PARAMS[key] = lparams[key]

    # initialize skeleton of descriptors
    skeleton = {
        'name': 'XXX',
        'call_back': metric_of,
        'time_max': 60,
        'value_type': 'uint',
        'format': '%u',
        'units': 'XXX',
        'slope': 'both', # zero|positive|negative|both
        'description': 'XXX',
        'groups': PARAMS['type'],
    }

    mp = PARAMS['metrix_prefix']
    queues = list()

    if 'queues' in PARAMS:
        queues = PARAMS['queues'].split(',')

    def create_desc(skel, prop):
        d = skel.copy()
        for k,v in prop.iteritems():
            d[k] = v
        return d

    def create_queue_descriptors(skeleton, mp, name):
        return [
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_items',
                'units': 'items',
                'description': 'current items'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_bytes',
                'units': 'bytes',
                'description': 'current bytes'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_total_items',
                'units': 'items',
                'slope': 'positive',
                'description': 'total items'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_logsize',
                'units': 'bytes',
                'description': 'size of journal file'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_expired_items',
                'units': 'items',
                'slope': 'positive',
                'description': 'total expired items'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_mem_items',
                'units': 'items',
                'description': 'current items in memory'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_mem_bytes',
                'units': 'bytes',
                'description': 'current size of items in memory'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_age',
                'units': 'milliseconds',
                'description': 'time last item was waiting'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_discarded',
                'units': 'items',
                'slope': 'positive',
                'description': 'total items discarded'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_waiters',
                'units': 'waiters',
                'description': 'total waiters'
            }),
        ]

    descriptors.append(create_desc(skeleton, {
        'name': mp + '_uptime',
        'units': 'seconds',
        'slope': 'positive',
        'description': 'current uptime',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_curr_items',
        'units': 'items',
        'description': 'current items stored',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_total_items',
        'units': 'items',
        'slope': 'positive',
        'description': 'total items stored',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_bytes',
        'units': 'bytes',
        'description': 'total bytes of all items waiting in queues',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_curr_connections',
        'units': 'connections',
        'description': 'current open connections',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_total_connections',
        'units': 'connections',
        'slow': 'positive',
        'description': 'total open connections',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_cmd_get',
        'units': 'commands',
        'slope': 'positive',
        'description': 'total get reqs',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_cmd_set',
        'units': 'commands',
        'slope': 'positive',
        'description': 'total set reqs',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_cmd_peek',
        'units': 'commands',
        'slope': 'positive',
        'description': 'total peek reqs',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_get_hits',
        'units': 'requests',
        'slope': 'positive',
        'description': 'total hits',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_get_misses',
        'units': 'requests',
        'slope': 'positive',
        'description': 'total misses',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_bytes_read',
        'units': 'bytes',
        'slope': 'positive',
        'description': 'total bytes read from clients',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_bytes_written',
        'units': 'bytes',
        'slope': 'positive',
        'description': 'total bytes written to clients',
    }))

    for queue in queues:
        for _qd in create_queue_descriptors(skeleton, mp, queue):
            descriptors.append(_qd)

    return descriptors

def metric_cleanup():
    pass

if __name__ == '__main__':
    try:
        params = {
            'host': '127.0.0.1',
            'port': 22133,
            'debug': True,
            'type': 'kestrel',
            'metrix_prefix': 'ks',
            'queues': 'my_queue01'
        }
        metric_init(params)

        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is '+d['format']) % (d['name'],  v)
            time.sleep(5)
    except KeyboardInterrupt:
        os._exit(1)
    except:
        traceback.print_exc()
        os._exit(1)