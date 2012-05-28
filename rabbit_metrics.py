#!/usr/bin/python
from subprocess import Popen, PIPE


GMETRIC="/usr/bin/gmetric"
RABBITMQCTL="/usr/sbin/rabbitmqctl"


def run_gmetric(vhost, queue, qtype, value, prefix="rabbit", vtype="uint32"):
    cmd = [GMETRIC,
           '-t', vtype,
           '-u', 'messages',
           '-n', "%s_%s_%s_%s" % (prefix, vhost, queue, qtype),
           '-v', "%d" % value]
    Popen(cmd).communicate()

def get_vhost_stats(vhost, qtypes):
    data = {}
    VALID_TYPES = ['messages_ready', 'messages_unacknowledged']
    qtypes = [t for t in qtypes if t in VALID_TYPES]
    cmd = [RABBITMQCTL,
           'list_queues',
           '-p', vhost, 'name']
    cmd.extend(qtypes)
    stdout, stderr = Popen(cmd, stdout=PIPE, stderr=PIPE).communicate()
    for l in stdout.split("\n")[1:-2]:
        l = l.split()
        name = l.pop(0)
        data[name] = {}
        for i, t in enumerate(qtypes):
            data[name][t] = int(l[i])

    return data

def graph(vhost, queues):
    stats = get_vhost_stats(vhost, ('messages_ready', 'messages_unacknowledged') )
    for q in queues:
        qstats = stats[q]
        for qtype, value in qstats.iteritems():
            run_gmetric(vhost, q, qtype, value)
             

graph('/', ['clientlog'])
