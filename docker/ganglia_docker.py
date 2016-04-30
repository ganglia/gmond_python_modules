#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Docker monitoring plugin for Ganglia
# Sayamindu Dasgupta <sayamindu@media.mit.edu>
# April 2015

import copy
import json
import os
import time
import traceback

from docker import Client

descriptors = list()
global_old_stats = dict()
stats_generators = dict()


def get_container_stats(container_id, metric_name, first_time=False):
    global global_old_stats
    global stats_generators

    stats_generator = stats_generators[container_id]
    stats = json.loads(stats_generator.next())
    stats['timestamp'] = time.time()

    if first_time:
        old_stats = {}
        global_old_stats[metric_name] = {}
    else:
        old_stats = global_old_stats[metric_name][container_id]
        global_old_stats[metric_name][container_id] = copy.deepcopy(stats)

    return old_stats, stats


# https://github.com/dockermeetupsinbordeaux/docker-zabbix-sender/blob/master/docker_zabbix_sender/collector.py
def get_container_cpu_stats(name):
    global descriptors

    user_cpu_percent = 0.0
    kernel_cpu_percent = 0.0

    for i in range(0, len(descriptors)):
        if descriptors[i]['name'] == name:
            break

    old_stats, stats = get_container_stats(descriptors[i]['container_id'], name)

    user_cpu_delta = float(stats['cpu_stats']['cpu_usage']['usage_in_usermode']) - float(old_stats['cpu_stats']['cpu_usage']['usage_in_usermode'])
    kernel_cpu_delta  = float(stats['cpu_stats']['cpu_usage']['usage_in_kernelmode']) - float(old_stats['cpu_stats']['cpu_usage']['usage_in_kernelmode'])
    system_delta = float(stats['cpu_stats']['system_cpu_usage']) - float(old_stats['cpu_stats']['system_cpu_usage'])

    if system_delta > 0.0:
        if user_cpu_delta > 0.0:
            try:
                user_cpu_percent = (user_cpu_delta / system_delta) * float(len(stats['cpu_stats']['cpu_usage']['percpu_usage'])) * 100.0
            except Exception as e:
                traceback.print_exc()
                pass
        if kernel_cpu_delta > 0.0:
            try:
                kernel_cpu_percent = (kernel_cpu_delta / system_delta) * float(len(stats['cpu_stats']['cpu_usage']['percpu_usage'])) * 100.0
            except Exception as e:
                traceback.print_exc()
                pass

    value = user_cpu_percent + kernel_cpu_percent

    if value < 0:
        value = 0.0

    return value


def get_container_memory_stats(name):
    global descriptors

    for i in range(0, len(descriptors)):
        if descriptors[i]['name'] == name:
            break
    old_stats, stats = get_container_stats(descriptors[i]['container_id'], name)

    return float(stats['memory_stats']['usage'])


def get_container_net_rx_bytes_stats(name):
    global descriptors

    for i in range(0, len(descriptors)):
        if descriptors[i]['name'] == name:
            break
    old_stats, stats = get_container_stats(descriptors[i]['container_id'], name)

    value = 0.0
    try:
        value = ((stats['network']['rx_bytes'] - old_stats['network']['rx_bytes']) * 1.0e-6)/(stats['timestamp'] - old_stats['timestamp'])
    except Exception as e:
        traceback.print_exc()
        pass

    if value < 0:
        value = 0.0

    return value


def get_container_net_tx_bytes_stats(name):
    global descriptors

    for i in range(0, len(descriptors)):
        if descriptors[i]['name'] == name:
            break
    old_stats, stats = get_container_stats(descriptors[i]['container_id'], name)

    value = 0.0
    try:
        value = ((stats['network']['tx_bytes'] - old_stats['network']['tx_bytes']))/(stats['timestamp'] - old_stats['timestamp'])
    except Exception as e:
        traceback.print_exc()
        pass

    if value < 0:
        value = 0.0

    return value


def metric_init(params):
    global descriptors
    global global_old_stats
    global stats_generators

    if 'metrics_prefix' not in params:
      params['metrics_prefix'] = 'docker'

    if 'docker_url' not in params:
        params['docker_url'] = 'unix://var/run/docker.sock',
    docker_url = params['docker_url']

    docker_client = Client(base_url=docker_url, version="1.18")
    for container in docker_client.containers():
        stats_generators[container['Id']] = docker_client.stats(container['Id'])

        # CPU Usage
        name = '{0}_{1}_cpu'.format(params["metrics_prefix"], container['Names'][0][1:])
        descriptors.append({
            'name': name,
            'call_back': get_container_cpu_stats,
            'time_max': 90,
            'format': '%f',
            'units': 'percent',
            'value_type': 'float',
            'slope': 'both',
            'description': 'CPU usage of container {0}'.format(container['Names'][0][1:]),
            'groups': 'docker',
            #  The following are module-private data stored in a public variable
            'container_id': container['Id']
        })
        stats, global_old_stats[name][container['Id']] = get_container_stats(container['Id'], name, first_time=True)
        global_old_stats[name][container['Id']]['timestamp'] = time.time()

        # Memory
        name = '{0}_{1}_memory'.format(params["metrics_prefix"], container['Names'][0][1:])
        descriptors.append({
            'name': name,
            'call_back': get_container_memory_stats,
            'time_max': 90,
            'format': '%f',
            'units': 'bytes',
            'value_type': 'float',
            'slope': 'both',
            'description': 'Memory usage of container {0}'.format(container['Names'][0][1:]),
            'groups': 'docker',
            #  The following are module-private data stored in a public variable
            'container_id': container['Id']
        })
        stats, global_old_stats[name][container['Id']] = get_container_stats(container['Id'], name, first_time=True)
        global_old_stats[name][container['Id']]['timestamp'] = time.time()

        # Network
        name = '{0}_{1}_net_rx_bytes'.format(params["metrics_prefix"], container['Names'][0][1:])
        descriptors.append({
            'name': name,
            'call_back': get_container_net_rx_bytes_stats,
            'time_max': 90,
            'format': '%f',
            'units': 'bytes/s',
            'value_type': 'float',
            'slope': 'both',
            'description': 'Network RX rate of container {0}'.format(container['Names'][0][1:]),
            'groups': 'docker',
            #  The following are module-private data stored in a public variable
            'container_id': container['Id']
        })
        stats, global_old_stats[name][container['Id']] = get_container_stats(container['Id'], name, first_time=True)
        global_old_stats[name][container['Id']]['timestamp'] = time.time()

        name = '{0}_{1}_net_tx_bytes'.format(params["metrics_prefix"], container['Names'][0][1:])
        descriptors.append({
            'name': name,
            'call_back': get_container_net_tx_bytes_stats,
            'time_max': 90,
            'format': '%f',
            'units': 'bytes/s',
            'value_type': 'float',
            'slope': 'both',
            'description': 'Network TX rate of container {0}'.format(container['Names'][0][1:]),
            'groups': 'docker',
            #  The following are module-private data stored in a public variable
            'container_id': container['Id']
        })
        stats, global_old_stats[name][container['Id']] = get_container_stats(container['Id'], name, first_time=True)
        global_old_stats[name][container['Id']]['timestamp'] = time.time()

        # TODO: Network Errors, I/O

    return descriptors


# Testing
if __name__ == '__main__':
    try:
        params = {
            "docker_url" : 'unix://var/run/docker.sock',
            }
        metric_init(params)

        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is '+d['format']) % (d['name'],  v)
            time.sleep(5)
    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except:
        traceback.print_exc()
        os._exit(1)
