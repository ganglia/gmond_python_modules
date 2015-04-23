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
    level=logging.INFO,
    format='%(asctime)s - %(levelname)5s - %(message)s',
)


STAT_DESCRIPTIONS = [
    {
        'name': 'es_heap_committed',
        'units': 'Bytes',
        'format': '%.0f',
        'description': 'Java Heap Committed (Bytes)',
        'value_type': 'double',
    },
    {
        'name': 'es_heap_used',
        'units': 'Bytes',
        'format': '%.0f',
        'description': 'Java Heap Used (Bytes)',
        'value_type': 'double',
    },
    {
        'name': 'es_non_heap_committed',
        'units': 'Bytes',
        'format': '%.0f',
        'description': 'Java Non Heap Committed (Bytes)',
        'value_type': 'double',
    },
    {
        'name': 'es_non_heap_used',
        'units': 'Bytes',
        'format': '%.0f',
        'description': 'Java Non Heap Used (Bytes)',
        'value_type': 'double',
    },
    {
        'name': 'es_threads',
        'units': 'threads',
        'format': '%d',
        'description': 'Threads (open)',
    },
    {
        'name': 'es_threads_peak',
        'units': 'threads',
        'format': '%d',
        'description': 'Threads Peak (open)',
    },
    {
        'name': 'es_gc_time',
        'units': 'ms',
        'format': '%d',
        'slope': 'positive',
        'description': 'Java GC Time (ms)',
    },
    {
        'name': 'es_gc_young_time',
        'units': 'ms',
        'format': '%d',
        'slope': 'positive',
        'description': 'Java GC Young Time (ms)',
    },
    {
        'name': 'es_gc_old_time',
        'units': 'ms',
        'format': '%d',
        'slope': 'positive',
        'description': 'Java GC Old Time (ms)'
    },
    {
        'name': 'es_transport_open',
        'units': 'sockets',
        'format': '%d',
        'description': 'Transport Open (sockets)',
    },
    {
        'name': 'es_transport_rx_count',
        'units': 'rx',
        'format': '%d',
        'slope': 'positive',
        'description': 'RX Count',
    },
    {
        'name': 'es_transport_rx_size',
        'units': 'Bytes',
        'format': '%.0f',
        'slope': 'positive',
        'description': 'RX (Bytes)',
        'value_type': 'double',
    },
    {
        'name': 'es_transport_tx_count',
        'units': 'tx',
        'format': '%d',
        'slope': 'positive',
        'description': 'TX Count',
    },
    {
        'name': 'es_transport_tx_size',
        'units': 'Bytes',
        'format': '%.0f',
        'slope': 'positive',
        'description': 'TX (Bytes)',
    },
    {
        'name': 'es_http_current_open',
        'units': 'sockets',
        'format': '%d',
        'description': 'HTTP Open (sockets)',
    },
    {
        'name': 'es_http_total_open',
        'units': 'sockets',
        'format': '%d',
        'description': 'HTTP Open (sockets)',
    },
    {
        'name': 'es_indices_size',
        'units': 'Bytes',
        'format': '%.0f',
        'description': 'Index Size (Bytes)',
        'value_type': 'double',
    },
    {
        'name': 'es_gc_count',
        'format': '%d',
        'slope': 'positive',
        'description': 'Java GC Count',
    },
    {
        'name': 'es_gc_young_count',
        'format': '%d',
        'slope': 'positive',
        'description': 'Java GC Young Count',
    },
    {
        'name': 'es_gc_old_count',
        'format': '%d',
        'slope': 'positive',
        'description': 'Java GC Old Count',
    },
    {
        'name': 'es_merges_current',
        'format': '%d',
        'description': 'Merges (current)',
    },
    {
        'name': 'es_merges_current_docs',
        'format': '%d',
        'description': 'Merges (docs)',
    },
    {
        'name': 'es_merges_total',
        'format': '%d',
        'slope': 'positive',
        'description': 'Merges (total)',
    },
    {
        'name': 'es_merges_total_docs',
        'format': '%d',
        'slope': 'positive',
        'description': 'Merges (total docs)',
    },
    {
        'name': 'es_merges_current_size',
        'units': 'Bytes',
        'format': '%.0f',
        'description': 'Merges size (current)',
    },
    {
        'name': 'es_merges_total_size',
        'units': 'Bytes',
        'format': '%.0f',
        'slope': 'positive',
        'description': 'Merges size (total)',
        'value_type': 'double',
    },
    {
        'name': 'es_merges_time',
        'units': 'ms',
        'format': '%d',
        'slope': 'positive',
        'description': 'Merges Time (ms)',
    },
    {
        'name': 'es_refresh_total',
        'units': 'refreshes',
        'format': '%d',
        'slope': 'positive',
        'description': 'Total Refresh',
    },
    {
        'name': 'es_refresh_time',
        'units': 'ms',
        'format': '%d',
        'slope': 'positive',
        'description': 'Total Refresh Time',
    },
    {
        'name': 'es_docs_count',
        'units': 'docs',
        'format': '%.0f',
        'description': 'Number of Documents',
        'value_type': 'double',
    },
    {
        'name': 'es_docs_deleted',
        'units': 'docs',
        'format': '%.0f',
        'description': 'Number of Documents Deleted',
        'value_type': 'double',
    },
    {
        'name': 'es_open_file_descriptors',
        'units': 'files',
        'format': '%d',
        'description': 'Open File Descriptors',
    },
    {
        'name': 'es_cache_field_eviction',
        'units': 'units',
        'format': '%d',
        'slope': 'positive',
        'description': 'Field Cache Evictions',
    },
    {
        'name': 'es_cache_field_size',
        'units': 'Bytes',
        'format': '%.0f',
        'description': 'Field Cache Size',
        'value_type': 'double',
    },
    {
        'name': 'es_cache_fielddata_evictions',
        'units': 'units',
        'format': '%d',
        'slope': 'positive',
        'description': 'Field Data Cache Evictions',
    },
    {
        'name': 'es_cache_fielddata_size',
        'units': 'Bytes',
        'format': '%.0f',
        'description': 'Field Data Cache Size',
        'value_type': 'double',
    },
    {
        'name': 'es_cache_filter_count',
        'format': '%d',
        'description': 'Filter Cache Count',
    },
    {
        'name': 'es_cache_filter_evictions',
        'format': '%d',
        'slope': 'positive',
        'description': 'Filter Cache Evictions',
    },
    {
        'name': 'es_cache_filter_size',
        'units': 'Bytes',
        'format': '%.0f',
        'description': 'Filter Cache Size',
        'value_type': 'double',
    },
    {
        'name': 'es_query_current',
        'units': 'Queries',
        'format': '%d',
        'description': 'Current Queries',
    },
    {
        'name': 'es_query_time',
        'units': 'ms',
        'format': '%d',
        'slope': 'positive',
        'description': 'Total Query Time',
    },
    {
        'name': 'es_fetch_current',
        'units': 'fetches',
        'format': '%d',
        'description': 'Current Fetches',
    },
    {
        'name': 'es_fetch_total',
        'units': 'fetches',
        'format': '%d',
        'slope': 'positive',
        'description': 'Total Fetches',
    },
    {
        'name': 'es_fetch_time',
        'units': 'ms',
        'format': '%d',
        'slope': 'positive',
        'description': 'Total Fetch Time',
    },
    {
        'name': 'es_flush_total',
        'units': 'flushes',
        'format': '%d',
        'description': 'Total Flushes',
    },
    {
        'name': 'es_flush_time',
        'units': 'ms',
        'format': '%d',
        'slope': 'positive',
        'description': 'Total Flush Time',
    },
    {
        'name': 'es_get_exists_time',
        'units': 'ms',
        'format': '%d',
        'slope': 'positive',
        'description': 'Exists Time',
    },
    {
        'name': 'es_get_exists_total',
        'units': 'total',
        'format': '%d',
        'description': 'Exists Total',
    },
    {
        'name': 'es_get_time',
        'units': 'ms',
        'format': '%d',
        'slope': 'positive',
        'description': 'Get Time',
    },
    {
        'name': 'es_get_total',
        'units': 'total',
        'format': '%d',
        'description': 'Get Total',
    },
    {
        'name': 'es_get_missing_time',
        'units': 'ms',
        'format': '%d',
        'slope': 'positive',
        'description': 'Missing Time',
    },
    {
        'name': 'es_get_missing_total',
        'units': 'total',
        'format': '%d',
        'description': 'Missing Total',
    },
    {
        'name': 'es_indexing_delete_time',
        'units': 'ms',
        'format': '%d',
        'slope': 'positive',
        'description': 'Delete Time',
    },
    {
        'name': 'es_indexing_delete_total',
        'units': 'docs',
        'format': '%d',
        'slope': 'positive',
        'description': 'Delete Total',
    },
    {
        'name': 'es_indexing_index_time',
        'units': 'ms',
        'format': '%d',
        'slope': 'positive',
        'description': 'Indexing Time',
    },
    {
        'name': 'es_indexing_index_total',
        'units': 'docs',
        'format': '%d',
        'slope': 'positive',
        'description': 'Indexing Documents Total',
    },
    {
        'name': 'es_query_total',
        'units': 'Queries',
        'format': '%d',
        'slope': 'positive',
        'description': 'Total Queries',
    },
]


def misc_path(string):
    return 'nodes.%s.' + string


def gc_path(string):
    return 'nodes.%s.jvm.gc.' + string


def indices_path(string):
    return 'nodes.%s.indices.' + string


COMMON_STATS = {
    'es_docs_count': indices_path('docs.count'),
    'es_docs_deleted': indices_path('docs.deleted'),
    'es_flush_total': indices_path('flush.total'),
    'es_flush_time': indices_path('flush.total_time_in_millis'),
    'es_get_exists_time': indices_path('get.exists_time_in_millis'),
    'es_get_exists_total': indices_path('get.exists_total'),
    'es_get_time': indices_path('get.time_in_millis'),
    'es_get_total': indices_path('get.total'),
    'es_get_missing_time': indices_path('get.missing_time_in_millis'),
    'es_get_missing_total': indices_path('get.missing_total'),
    'es_indexing_delete_time': indices_path('indexing.delete_time_in_millis'),
    'es_indexing_delete_total': indices_path('indexing.delete_total'),
    'es_indexing_index_time': indices_path('indexing.index_time_in_millis'),
    'es_indexing_index_total': indices_path('indexing.index_total'),
    'es_merges_current': indices_path('merges.current'),
    'es_merges_current_docs': indices_path('merges.current_docs'),
    'es_merges_current_size': indices_path('merges.current_size_in_bytes'),
    'es_merges_total': indices_path('merges.total'),
    'es_merges_total_docs': indices_path('merges.total_docs'),
    'es_merges_total_size': indices_path('merges.total_size_in_bytes'),
    'es_merges_time': indices_path('merges.total_time_in_millis'),
    'es_refresh_total': indices_path('refresh.total'),
    'es_refresh_time': indices_path('refresh.total_time_in_millis'),
    'es_query_current': indices_path('search.query_current'),
    'es_query_total': indices_path('search.query_total'),
    'es_query_time': indices_path('search.query_time_in_millis'),
    'es_fetch_current': indices_path('search.fetch_current'),
    'es_fetch_total': indices_path('search.fetch_total'),
    'es_fetch_time': indices_path('search.fetch_time_in_millis'),
    'es_indices_size': indices_path('store.size_in_bytes'),
    'es_heap_committed': misc_path('jvm.mem.heap_committed_in_bytes'),
    'es_heap_used': misc_path('jvm.mem.heap_used_in_bytes'),
    'es_non_heap_committed': misc_path('jvm.mem.non_heap_committed_in_bytes'),
    'es_non_heap_used': misc_path('jvm.mem.non_heap_used_in_bytes'),
    'es_threads': misc_path('jvm.threads.count'),
    'es_threads_peak': misc_path('jvm.threads.peak_count'),
    'es_transport_open': misc_path('transport.server_open'),
    'es_transport_rx_count': misc_path('transport.rx_count'),
    'es_transport_rx_size': misc_path('transport.rx_size_in_bytes'),
    'es_transport_tx_count': misc_path('transport.tx_count'),
    'es_transport_tx_size': misc_path('transport.tx_size_in_bytes'),
    'es_http_current_open': misc_path('http.current_open'),
    'es_http_total_open': misc_path('http.total_opened'),
    'es_open_file_descriptors': misc_path('process.open_file_descriptors'),
}


LEGACY_STATS = {
    'es_cache_field_eviction': indices_path('cache.field_evictions'),
    'es_cache_field_size': indices_path('cache.field_size_in_bytes'),
    'es_cache_filter_count': indices_path('cache.filter_count'),
    'es_cache_filter_evictions': indices_path('cache.filter_evictions'),
    'es_cache_filter_size': indices_path('cache.filter_size_in_bytes'),
    'es_gc_time': gc_path('collection_time_in_millis'),
    'es_gc_count': gc_path('collection_count'),
}

CURRENT_STATS = {
    'es_cache_fielddata_evictions': indices_path('fielddata.evictions'),
    'es_cache_fielddata_size': indices_path('fielddata.memory_size_in_bytes'),
    'es_cache_filter_evictions': indices_path('filter_cache.evictions'),
    'es_cache_filter_size': indices_path('filter_cache.memory_size_in_bytes'),
    'es_gc_young_time': gc_path('collectors.young.collection_time_in_millis'),
    'es_gc_young_count': gc_path('collectors.young.collection_count'),
    'es_gc_old_time': gc_path('collectors.old.collection_time_in_millis'),
    'es_gc_old_count': gc_path('collectors.old.collection_count'),
}


def log(string, level=logging.DEBUG):
    logging.log(level, '[Elasticsearch] ' + string)


def dig_it_up(obj, path):
    try:
        value = reduce(lambda x, y: x[y], path.split('.'), obj)
        log('Value for %s is %s' % (path, value), logging.INFO)
        return int(value)
    except TypeError:
        log('Value for %s has the wrong type' % path, logging.ERROR)
        return None
    except Exception:
        log('Could not get value for %s' % path, logging.ERROR)
        return None


def fetch(url):
    log('Fetching ' + url)
    result = json.load(urllib.urlopen(url))
    log('Got %s' % json.dumps(result))
    return result


def get_stat(url, get_path_function, name):
    json_object = fetch(url)
    return dig_it_up(json_object, get_path_function(json_object, name))


def create_description(skel, prop):
    description = skel.copy()
    description.update(prop)
    return description


def get_doc_count_path(*_args, **_kwargs):
    return '_all.primaries.docs.count'


def get_store_size_path(*_args, **_kwargs):
    return '_all.primaries.store.size_in_bytes'


def get_indices_descriptors(url, index, create_description_function):
    descriptors = [
        create_description_function({
            'call_back': partial(get_stat, url, get_doc_count_path),
            'name': 'es_index_{0}_docs_count'.format(index),
            'description': 'document count for index {0}'.format(index),
        }),
        create_description_function({
            'call_back': partial(get_stat, url, get_store_size_path),
            'name': 'es_index_{0}_size'.format(index),
            'description': 'size in bytes for index {0}'.format(index),
            'units': 'Bytes',
            'format': '%.0f',
            'value_type': 'double'
        })
    ]

    return descriptors


def get_elasticsearch_version(params):
    version = params['version']
    match = re.match(r'(?P<major>\d+)\.(?P<minor>(\d+(\.\d+)*))', version)
    return int(match.group('major')), int(match.group('minor'))


def get_url_path(major, minor):
    if major == 0:
        return '_cluster/nodes/_local/stats?all=true'
    else:
        if minor < 3:
            return '_cluster/state/nodes'
        else:
            return '_nodes/_local/stats'


def get_key_to_path(major, minor):
    result = COMMON_STATS.copy()
    if major == 1 and minor > 2:
        differences = CURRENT_STATS
    else:
        differences = LEGACY_STATS
    result.update(differences)
    return result


def get_path(key_to_path, json_object, name):
    return key_to_path[name] % json_object['nodes'].keys()[0]


def metric_init(params):
    log('Received the following parameters %s' % params)

    major, minor = get_elasticsearch_version(params)
    url = params['host'] + get_url_path(major, minor)
    key_to_path = get_key_to_path(major, minor)

    log('Number of keys : %s' % len(key_to_path))

    description_skeleton = {
        'name': 'XXX',
        'call_back': partial(get_stat, url, partial(get_path, key_to_path)),
        'time_max': 60,
        'value_type': 'uint',
        'units': 'units',
        'slope': 'both',
        'format': '%d',
        'description': 'XXX',
        'groups': params['metric_group'],
    }

    _create_description = partial(create_description, description_skeleton)

    descriptors = [
        _create_description(description)
        for description in STAT_DESCRIPTIONS
        if description['name'] in key_to_path
    ]

    for index in params['indices'].split():
        url = params['host'] + index + '/_stats'
        descriptors += get_indices_descriptors(url, index, _create_description)

    log('Number of descriptors : %s' % len(descriptors))

    return descriptors


def metric_cleanup():
    pass


def main():
    params = {
        'indices': '*',
        'host': 'http://localhost:9200/',
        'version': '1.4',
        'metric_group': 'elasticsearch',
    }
    descriptors = metric_init(params)
    for descriptor in descriptors:
        descriptor['call_back'](descriptor['name'])


# This code is for debugging and unit testing
if __name__ == '__main__':
    main()
