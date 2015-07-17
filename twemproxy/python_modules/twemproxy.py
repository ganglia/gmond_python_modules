
# The MIT License (MIT)

# Copyright (c) 2015 The Enthusiast Network

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Author: Tony Baltazar <abaltazar@enthusiastnetwork.com>



import socket
import sys

try:
    import json
except ImportError:
    import simplejson as json



NAME_PREFIX = 'twemproxy_'

descriptors = list()
Desc_Skel = {}

_Twemproxy_Connection = None

class Twemproxy():
    
    def __init__(self, params, name_prefix):
        self.stats_addr = params["stats_addr"]
        self.stats_port = int(params["stats_port"])
        self.name_prefix = name_prefix

        if "exclude" in params:
            self.exclude = [ exclude.strip() for exclude in params["exclude"].split(",") ]
        else:
            self.exclude = []

        self.metrics = self.__twemproxy_metrics()
 
    def __twemproxy_metrics(self):
        metric_hash = {}
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.stats_addr, self.stats_port))

            file = s.makefile('r')
            data = file.readline()
            s.close()

            response = json.loads(data)
        except:
            print("Unable to connect to %s:%i" % (self.stats_addr, self.stats_port))
            sys.exit(1)

        for pool, pool_info in response.items():
            if pool in self.exclude:
                continue

            if hasattr(pool_info, 'items'):
                metric_hash[str(pool)] = {}
                for server, server_info in pool_info.items():
                    if hasattr(server_info, 'items'):
                        #print("Server: ", server)
                        metric_hash[str(server)] = {}
                        for stat in server_info:
                            #print("Key: ", stat,  " Value: ", server_info[stat])
                            metric_hash[server][stat] = server_info[stat]
                    else:
                        metric_hash[pool][server] = server_info

        return metric_hash

    def __refresh_metrics(self):
        self.metrics = self.__twemproxy_metrics()
        return

    def get_pools(self):
        '''Returns pool names'''
        pools = [k for k in self.metrics.keys() if self.metrics[k].get("client_eof") != None] 
        return pools

    def get_nodes(self):
        '''Returns nodes (server) names'''
        nodes = [k for k in self.metrics.keys() if self.metrics[k].get("client_eof") == None]
        return nodes

    # Main metric handler
    def get_value(self, name):
        '''Return callback value for the requested metric'''
        metric_name_value = name[len(self.name_prefix):].split('-')
        
        metric_name = metric_name_value[0]
        metric_value = metric_name_value[1]

        result = self.metrics[metric_name][metric_value]

        self.__refresh_metrics()

        return result


def create_desc(prop):
    d = Desc_Skel.copy()
    for k, v in prop.iteritems():
        d[k] = v
    return d


def metric_init(params):
    global descriptors, Desc_Skel, _Twemproxy_Connection
    #print("twmeproxy received the following parameters")
    #print(params)

    _Twemproxy_Connection = Twemproxy(params, NAME_PREFIX)

    Desc_Skel = {
            'name'        : 'XXX',
            'call_back'   : get_value,
            'time_max'    : 60,
            'value_type'  : 'float',
            'units'       : 'connections',
            'slope'       : 'both',
            'format'      : '%.0f',
            'description' : 'XXX',
            'groups'      : 'twemproxy',
    }

    # Pools
    for pool in _Twemproxy_Connection.get_pools():
        descriptors.append(create_desc({
            "name"       :  NAME_PREFIX + pool + "-client_eof",
            "description": "# eof on client connections"
            }))

        descriptors.append(create_desc({
            "name"       :  NAME_PREFIX + pool + "-client_err",
            "description": "# errors on client connections"
            }))

        descriptors.append(create_desc({
            "name"       :  NAME_PREFIX + pool + "-client_connections",
            "description": "# active client connections"
            }))

        descriptors.append(create_desc({
            "name"       :  NAME_PREFIX + pool + "-server_ejects",
            "description": "# times backend server was ejected",
            "units"      : "Count"
            }))

        descriptors.append(create_desc({
            "name"       : NAME_PREFIX + pool + "-forward_error",
            "description": "# times we encountered a forwarding error",
            "units"      : "Count"
            }))

        descriptors.append(create_desc({
            "name"       : NAME_PREFIX + pool + "-fragments",
            "description": "# fragments created from a multi-vector request",
            "units"      : "Count"
            }))

    # Nodes (servers)
    for node in _Twemproxy_Connection.get_nodes():
        descriptors.append(create_desc({
            "name"       : NAME_PREFIX + node + "-server_eof",
            "description": "# eof on server connections"
            }))

        descriptors.append(create_desc({
            "name"       : NAME_PREFIX + node + "-server_err",
            "description": "# errors on server connections"
            }))

        descriptors.append(create_desc({
            "name"       : NAME_PREFIX + node + "-server_timedout",
            "description": "# timeouts on server connections"
            }))

        descriptors.append(create_desc({
            "name"       : NAME_PREFIX + node + "-server_connections",
            "description": "# active server connections"
            }))

        descriptors.append(create_desc({
            "name"       : NAME_PREFIX + node + "-requests",
            "description": "# requests",
            "units"      : "Requests"
            }))

        descriptors.append(create_desc({
            "name"       : NAME_PREFIX + node + "-request_bytes",
            "description": "total request bytes",
            "units"      : "Bytes"
            }))

        descriptors.append(create_desc({
            "name"       : NAME_PREFIX + node + "-responses",
            "description": "# respones",
            "units"      : "Count"
            }))

        descriptors.append(create_desc({
            "name"       : NAME_PREFIX + node + "-response_bytes",
            "description": "total response bytes",
            "units"      : "Bytes"
            }))

        descriptors.append(create_desc({
            "name"       : NAME_PREFIX + node + "-in_queue",
            "description": "# requests in incoming queue",
            "units"      : "Requests"
            }))

        descriptors.append(create_desc({
            "name"       : NAME_PREFIX + node + "-in_queue_bytes",
            "description": "current request bytes in incoming queue",
            "units"      : "Bytes"
            }))

        descriptors.append(create_desc({
            "name"       : NAME_PREFIX + node + "-out_queue",
            "description": "# requests in outgoing queue",
            "units"      : "Requests"
            }))

        descriptors.append(create_desc({
            "name"       : NAME_PREFIX + node + "-out_queue_bytes",
            "description": "current request bytes in outgoing queue",
            "units"      : "Bytes"
            }))

    return descriptors


def get_value(name):
    global _Twemproxy_Connection
    return _Twemproxy_Connection.get_value(name)
    
def metric_cleanup():
    pass



if __name__ == '__main__':
    params = {
            'stats_addr': 'localhost',
            'stats_port': '22222'
            }
    metric_init(params)
    for d in descriptors:
        v = d['call_back'](d['name'])
        print 'value for %s is %.0f' % (d['name'], v)
