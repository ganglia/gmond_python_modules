#!/usr/bin/env python
# -*- coding: utf-8 -*-

descriptors = [ {
        "slope": "both",
        "time_max": 60,
        "description": "Current number of items stored by this instance",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "curr_items"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Total number of items stored during the life of this instance",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "total_items"
    },
    {
        "slope": "both",
        "time_max": 60,
        "description": "Current number of bytes used by this server to store items",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "bytes"
    },
    {
        "slope": "both",
        "time_max": 60,
        "description": "Current number of open connections",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "curr_connections"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Total number of connections opened since the server started running",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "total_connections"
    },
    {
        "slope": "both",
        "time_max": 60,
        "description": "Number of connection structures allocated by the server",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "connection_structures"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Total number of retrieval requests (get operations)",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "cmd_get"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Total number of storage requests (set operations)",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "cmd_set"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of keys that have been requested and found present",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "get_hits"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of items that have been requested and not found",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "get_misses"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of keys that have been deleted and found present",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "delete_hits"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of items that have been delete and not found",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "delete_misses"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of keys that have been incremented and found present",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "incr_hits"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of items that have been incremented and not found",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "incr_misses"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of keys that have been decremented and found present",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "decr_hits"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of items that have been decremented and not found",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "decr_misses"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of keys that have been compared and swapped and found present",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "cas_hits"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of items that have been compared and swapped and not found",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "cas_misses"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of valid items removed from cache to free memory for new items",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "evictions"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Total number of bytes read by this server from network",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "bytes_read"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Total number of bytes sent by this server to network",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "bytes_written"
    },
    {
        "slope": "zero",
        "time_max": 60,
        "description": "Number of bytes this server is permitted to use for storage",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "limit_maxbytes"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of worker threads requested",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "threads"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of yields for connections",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "conn_yields"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Age of the oldest item within slabs (mean)",
        "format": "%.2f",
        "value_type": "float",
        "groups": "memcached",
        "units": "items",
        "name": "age_mean"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Age of the oldest item within slabs (median)",
        "format": "%.2f",
        "value_type": "float",
        "groups": "memcached",
        "units": "items",
        "name": "age_median"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Age of the oldest item within slabs (min)",
        "format": "%.2f",
        "value_type": "float",
        "groups": "memcached",
        "units": "items",
        "name": "age_min"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "The age of the oldest item within slabs (max)",
        "format": "%.2f",
        "value_type": "float",
        "groups": "memcached",
        "units": "items",
        "name": "age_max"
    }
]
