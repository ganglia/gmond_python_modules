#! /usr/bin/python

try:
    import simplejson as json
    assert json  # silence pyflakes
except ImportError:
    import json

import logging
import urllib
import re
from functools import partial

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s\t Thread-%(thread)d - %(message)s",
)
logging.debug('starting up')

# short name to full path for stats
# pylint: disable=invalid-name
keyToPath = dict()

# INDICES METRICS #

# CACHE
keyToPath['es_cache_field_eviction'] = "nodes.%s.indices.cache.field_evictions"
keyToPath['es_cache_field_size'] = "nodes.%s.indices.cache.field_size_in_bytes"
keyToPath['es_cache_filter_count'] = "nodes.%s.indices.cache.filter_count"
keyToPath[
    'es_cache_filter_evictions'] = "nodes.%s.indices.cache.filter_evictions"
keyToPath[
    'es_cache_filter_size'] = "nodes.%s.indices.cache.filter_size_in_bytes"

# DOCS
keyToPath['es_docs_count'] = "nodes.%s.indices.docs.count"
keyToPath['es_docs_deleted'] = "nodes.%s.indices.docs.deleted"

# FLUSH
keyToPath['es_flush_total'] = "nodes.%s.indices.flush.total"
keyToPath['es_flush_time'] = "nodes.%s.indices.flush.total_time_in_millis"

# GET
keyToPath['es_get_exists_time'] = "nodes.%s.indices.get.exists_time_in_millis"
keyToPath['es_get_exists_total'] = "nodes.%s.indices.get.exists_total"
keyToPath['es_get_time'] = "nodes.%s.indices.get.time_in_millis"
keyToPath['es_get_total'] = "nodes.%s.indices.get.total"
keyToPath[
    'es_get_missing_time'] = "nodes.%s.indices.get.missing_time_in_millis"
keyToPath['es_get_missing_total'] = "nodes.%s.indices.get.missing_total"

# INDEXING
keyToPath['es_indexing_delete_time'] = \
    "nodes.%s.indices.indexing.delete_time_in_millis"
keyToPath[
    'es_indexing_delete_total'] = "nodes.%s.indices.indexing.delete_total"
keyToPath['es_indexing_index_time'] = \
    "nodes.%s.indices.indexing.index_time_in_millis"
keyToPath['es_indexing_index_total'] = "nodes.%s.indices.indexing.index_total"

# MERGES
keyToPath['es_merges_current'] = "nodes.%s.indices.merges.current"
keyToPath['es_merges_current_docs'] = "nodes.%s.indices.merges.current_docs"
keyToPath['es_merges_current_size'] = \
    "nodes.%s.indices.merges.current_size_in_bytes"
keyToPath['es_merges_total'] = "nodes.%s.indices.merges.total"
keyToPath['es_merges_total_docs'] = "nodes.%s.indices.merges.total_docs"
keyToPath[
    'es_merges_total_size'] = "nodes.%s.indices.merges.total_size_in_bytes"
keyToPath['es_merges_time'] = "nodes.%s.indices.merges.total_time_in_millis"

# REFRESH
keyToPath['es_refresh_total'] = "nodes.%s.indices.refresh.total"
keyToPath['es_refresh_time'] = "nodes.%s.indices.refresh.total_time_in_millis"

# SEARCH
keyToPath['es_query_current'] = "nodes.%s.indices.search.query_current"
keyToPath['es_query_total'] = "nodes.%s.indices.search.query_total"
keyToPath['es_query_time'] = "nodes.%s.indices.search.query_time_in_millis"
keyToPath['es_fetch_current'] = "nodes.%s.indices.search.fetch_current"
keyToPath['es_fetch_total'] = "nodes.%s.indices.search.fetch_total"
keyToPath['es_fetch_time'] = "nodes.%s.indices.search.fetch_time_in_millis"

# STORE
keyToPath['es_indices_size'] = "nodes.%s.indices.store.size_in_bytes"

# JVM METRICS #
# MEM
keyToPath['es_heap_committed'] = "nodes.%s.jvm.mem.heap_committed_in_bytes"
keyToPath['es_heap_used'] = "nodes.%s.jvm.mem.heap_used_in_bytes"
keyToPath[
    'es_non_heap_committed'] = "nodes.%s.jvm.mem.non_heap_committed_in_bytes"
keyToPath['es_non_heap_used'] = "nodes.%s.jvm.mem.non_heap_used_in_bytes"

# THREADS
keyToPath['es_threads'] = "nodes.%s.jvm.threads.count"
keyToPath['es_threads_peak'] = "nodes.%s.jvm.threads.peak_count"

# GC
keyToPath['es_gc_time'] = "nodes.%s.jvm.gc.collection_time_in_millis"
keyToPath['es_gc_count'] = "nodes.%s.jvm.gc.collection_count"

# TRANSPORT METRICS #
keyToPath['es_transport_open'] = "nodes.%s.transport.server_open"
keyToPath['es_transport_rx_count'] = "nodes.%s.transport.rx_count"
keyToPath['es_transport_rx_size'] = "nodes.%s.transport.rx_size_in_bytes"
keyToPath['es_transport_tx_count'] = "nodes.%s.transport.tx_count"
keyToPath['es_transport_tx_size'] = "nodes.%s.transport.tx_size_in_bytes"

# HTTP METRICS #
keyToPath['es_http_current_open'] = "nodes.%s.http.current_open"
keyToPath['es_http_total_open'] = "nodes.%s.http.total_opened"

# PROCESS METRICS #
keyToPath[
    'es_open_file_descriptors'] = "nodes.%s.process.open_file_descriptors"


def dig_it_up(obj, path):
    try:
        path = path.split('.')
        return reduce(lambda x, y: x[y], path, obj)
    except Exception:
        return False


def update_result(result, url):
    logging.debug('[elasticsearch] Fetching ' + url)
    result = json.load(urllib.urlopen(url))
    return result


def get_stat_index(result, url, path, _name):
    result = update_result(result, url)
    val = dig_it_up(result, path)

    if not isinstance(val, bool):
        return int(val)
    else:
        return None


def get_stat(result, url, name):
    result = update_result(result, url)

    node = result['nodes'].keys()[0]
    val = dig_it_up(result, keyToPath[name] % node)

    # Check to make sure we have a valid result
    # JsonPath returns False if no match found
    if not isinstance(val, bool):
        return int(val)
    else:
        return None


def create_desc(skel, prop):
    description = skel.copy()
    description.update(prop)
    return description


def get_indices_descriptors(index, skel, result, url):
    metric_tpl = 'es_index_{0}_{{0}}'.format(index)
    callback = partial(get_stat_index, result, url)
    get_doc_count = \
        partial(callback, '_all.primaries.docs.count'),
    get_store_size = \
        partial(callback, '_all.primaries.store.size_in_bytes'),
    _create_desc = partial(create_desc, skel)

    descriptors = [
        _create_desc({
            'call_back': get_doc_count,
            'name': metric_tpl.format('docs_count'),
            'description': 'document count for index {0}'.format(index),
        }),
        _create_desc({
            'call_back': get_store_size,
            'name': metric_tpl.format('size'),
            'description': 'size in bytes for index {0}'.format(index),
            'units': 'Bytes',
            'format': '%.0f',
            'value_type': 'double'
        })
    ]

    return descriptors


def metric_init(params):
    # pylint: disable=too-many-statements
    descriptors = []

    logging.debug('[elasticsearch] Received the following parameters')
    logging.debug(params)

    host = params.get('host', 'http://localhost:9200/')

    version = params.get('version', '1.2')

    match = re.match(r'(?P<major>\d+)\.(?P<minor>(\d+(\.\d+)*))', version)

    if match and match.group('major') == '0':
        url_cluster = '{0}_cluster/nodes/_local/stats?all=true'.format(host)
    else:
        url_cluster = '{0}_cluster/state/nodes'.format(host)

    # First iteration - Grab statistics
    logging.debug('[elasticsearch] Fetching ' + url_cluster)
    result = json.load(urllib.urlopen(url_cluster))

    metric_group = params.get('metric_group', 'elasticsearch')

    description_skeleton = {
        'name': 'XXX',
        'call_back': partial(get_stat, result, url_cluster),
        'time_max': 60,
        'value_type': 'uint',
        'units': 'units',
        'slope': 'both',
        'format': '%d',
        'description': 'XXX',
        'groups': metric_group,
    }

    indices = params.get('indices', '*').split()
    for index in indices:
        url_indices = '{0}{1}/_stats'.format(host, index)
        logging.debug('[elasticsearch] Fetching ' + url_indices)

        r_indices = json.load(urllib.urlopen(url_indices))
        descriptors += get_indices_descriptors(index,
                                               description_skeleton,
                                               r_indices,
                                               url_indices)

    _create_desc = partial(create_desc, description_skeleton)

    descriptors.append(
        _create_desc({
            'name': 'es_heap_committed',
            'units': 'Bytes',
            'format': '%.0f',
            'description': 'Java Heap Committed (Bytes)',
            'value_type': 'double'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_heap_used',
            'units': 'Bytes',
            'format': '%.0f',
            'description': 'Java Heap Used (Bytes)',
            'value_type': 'double'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_non_heap_committed',
            'units': 'Bytes',
            'format': '%.0f',
            'description': 'Java Non Heap Committed (Bytes)',
            'value_type': 'double'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_non_heap_used',
            'units': 'Bytes',
            'format': '%.0f',
            'description': 'Java Non Heap Used (Bytes)',
            'value_type': 'double'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_threads',
            'units': 'threads',
            'format': '%d',
            'description': 'Threads (open)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_threads_peak',
            'units': 'threads',
            'format': '%d',
            'description': 'Threads Peak (open)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_gc_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Java GC Time (ms)'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_transport_open',
            'units': 'sockets',
            'format': '%d',
            'description': 'Transport Open (sockets)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_transport_rx_count',
            'units': 'rx',
            'format': '%d',
            'slope': 'positive',
            'description': 'RX Count'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_transport_rx_size',
            'units': 'Bytes',
            'format': '%.0f',
            'slope': 'positive',
            'description': 'RX (Bytes)',
            'value_type': 'double',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_transport_tx_count',
            'units': 'tx',
            'format': '%d',
            'slope': 'positive',
            'description': 'TX Count'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_transport_tx_size',
            'units': 'Bytes',
            'format': '%.0f',
            'slope': 'positive',
            'description': 'TX (Bytes)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_http_current_open',
            'units': 'sockets',
            'format': '%d',
            'description': 'HTTP Open (sockets)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_http_total_open',
            'units': 'sockets',
            'format': '%d',
            'description': 'HTTP Open (sockets)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_indices_size',
            'units': 'Bytes',
            'format': '%.0f',
            'description': 'Index Size (Bytes)',
            'value_type': 'double',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_gc_count',
            'format': '%d',
            'slope': 'positive',
            'description': 'Java GC Count',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_merges_current',
            'format': '%d',
            'description': 'Merges (current)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_merges_current_docs',
            'format': '%d',
            'description': 'Merges (docs)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_merges_total',
            'format': '%d',
            'slope': 'positive',
            'description': 'Merges (total)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_merges_total_docs',
            'format': '%d',
            'slope': 'positive',
            'description': 'Merges (total docs)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_merges_current_size',
            'units': 'Bytes',
            'format': '%.0f',
            'description': 'Merges size (current)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_merges_total_size',
            'units': 'Bytes',
            'format': '%.0f',
            'slope': 'positive',
            'description': 'Merges size (total)',
            'value_type': 'double',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_merges_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Merges Time (ms)'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_refresh_total',
            'units': 'refreshes',
            'format': '%d',
            'slope': 'positive',
            'description': 'Total Refresh'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_refresh_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Total Refresh Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_docs_count',
            'units': 'docs',
            'format': '%.0f',
            'description': 'Number of Documents',
            'value_type': 'double'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_docs_deleted',
            'units': 'docs',
            'format': '%.0f',
            'description': 'Number of Documents Deleted',
            'value_type': 'double'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_open_file_descriptors',
            'units': 'files',
            'format': '%d',
            'description': 'Open File Descriptors',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_cache_field_eviction',
            'units': 'units',
            'format': '%d',
            'slope': 'positive',
            'description': 'Field Cache Evictions',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_cache_field_size',
            'units': 'Bytes',
            'format': '%.0f',
            'description': 'Field Cache Size',
            'value_type': 'double',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_cache_filter_count',
            'format': '%d',
            'description': 'Filter Cache Count',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_cache_filter_evictions',
            'format': '%d',
            'slope': 'positive',
            'description': 'Filter Cache Evictions',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_cache_filter_size',
            'units': 'Bytes',
            'format': '%.0f',
            'description': 'Filter Cache Size',
            'value_type': 'double'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_query_current',
            'units': 'Queries',
            'format': '%d',
            'description': 'Current Queries',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_query_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Total Query Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_fetch_current',
            'units': 'fetches',
            'format': '%d',
            'description': 'Current Fetches',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_fetch_total',
            'units': 'fetches',
            'format': '%d',
            'slope': 'positive',
            'description': 'Total Fetches'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_fetch_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Total Fetch Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_flush_total',
            'units': 'flushes',
            'format': '%d',
            'description': 'Total Flushes',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_flush_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Total Flush Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_get_exists_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Exists Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_get_exists_total',
            'units': 'total',
            'format': '%d',
            'description': 'Exists Total',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_get_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Get Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_get_total',
            'units': 'total',
            'format': '%d',
            'description': 'Get Total',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_get_missing_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Missing Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_get_missing_total',
            'units': 'total',
            'format': '%d',
            'description': 'Missing Total',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_indexing_delete_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Delete Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_indexing_delete_total',
            'units': 'docs',
            'format': '%d',
            'slope': 'positive',
            'description': 'Delete Total'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_indexing_index_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Indexing Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_indexing_index_total',
            'units': 'docs',
            'format': '%d',
            'slope': 'positive',
            'description': 'Indexing Documents Total'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_query_total',
            'units': 'Queries',
            'format': '%d',
            'slope': 'positive',
            'description': 'Total Queries'
        })
    )
    return descriptors


def metric_cleanup():
    pass


def main():
    params = {
        'indices': '*',
        'host': 'http://localhost:9200/',
        'version': '1.2',
        'metric_group': 'elasticsearch',
    }
    descriptors = metric_init(params)
    for descriptor in descriptors:
        value = descriptor['call_back'](descriptor['name'])
        logging.debug('Value for %s is %s', descriptor['name'], str(value))


# This code is for debugging and unit testing
if __name__ == '__main__':
    main()
