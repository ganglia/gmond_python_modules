#
# net_latency - A simple Ganglia module that
# measures network latency.
#
# Created by Giorgos Kappes <contact@giorgoskappes.com>
#
import subprocess
import os
import time
import threading

# The worker thread.
worker = None

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
    
class PingerThread(threading.Thread):
    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running = False
        self.stopping = False
        self.refresh_rate = int(params['refresh_rate'])
        self.target = params['target']
        if not self.target:
            # We choose the host's gateway as the default target.
            self.target = "$(ip route show | grep default | awk '{ print $3 }')"

        self.latency = 0
        self.lock = threading.Lock()

    def shutdown(self):
        self.stopping = True
        if not self.running:
            return
        self.join()

    def run(self):
        self.running = True
        while not self.stopping:
            time.sleep(self.refresh_rate)
            self.refresh_metrics()

        self.running = False
      
    def measure_latency(self):
        try:
            command = "ping -c 5 -W 2 "+self.target+" | tail -1| awk -F '/' '{print $5}'"
            f = os.popen(command)
            res = f.read()
            if is_number(res) == False:
                return 0
        except IOError:
            return 0
        
        return int(float(res) * 1000)

    def refresh_metrics(self):
        self.lock.acquire()
        self.latency = self.measure_latency()
        self.lock.release()
        
    def get_latency(self, name):
        self.lock.acquire()
        l = self.latency
        self.lock.release()
        return l

def create_descriptors(params):
    global descriptors

    d1 = {'name': 'net_latency',
          'call_back': get_latency,
          'value_type': 'uint',
          'units': 'microseconds',
          'slope': 'both',
          'format': '%u',
          'description': 'Network Latency',
          'groups': 'network' }
    
    descriptors = [d1]
    return descriptors

def metric_init(params):
    descriptors = create_descriptors(params)
    global worker
    if worker is not None:
        raise Exception('Worker thread exists')
        
    worker = PingerThread(params)
    worker.refresh_metrics()
    worker.start()
    return descriptors

def get_latency(name):
    global worker
    return worker.get_latency(name)
    
def metric_cleanup():
    global worker
    if worker is not None:
        worker.shutdown()

    pass
    
