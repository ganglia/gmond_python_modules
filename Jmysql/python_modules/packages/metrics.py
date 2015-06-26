# -*- coding:utf-8 -*-
# author:jianqiao.ms

throughput_metrics = dict(
    mysql_Com_change_db_per_second          = {"name":"mysql_Com_change_db_per_second",
                                               "value_type":"float",
                                               "units":"N/s",
                                               "format":"%f"},
    mysql_Com_select_per_second             = {"name":"mysql_Com_select_per_second",
                                               "value_type":"float",
                                               "units":"N/s",
                                               "format":"%f"},
    mysql_Com_insert_per_second             = {"name":"mysql_Com_insert_per_second",
                                               "value_type":"float",
                                               "units":"N/s",
                                               "format":"%f"},
    mysql_Com_update_per_second             = {"name":"mysql_Com_update_per_second",
                                               "value_type":"float",
                                               "units":"N/s",
                                               "format":"%f"},
    mysql_Com_delete_per_second             = {"name":"mysql_Com_delete_per_second",
                                               "value_type":"float",
                                               "units":"N/s",
                                               "format":"%f"},
    mysql_connections_per_second            = {"name":"mysql_connections_per_second",
                                               "value_type":"float",
                                               "units":"N/s",
                                               "format":"%f"},
    mysql_aborted_connects_per_second       = {"name":"mysql_aborted_connects_per_second",
                                               "value_type":"float",
                                               "units":"N/s",
                                               "format":"%f"},
    mysql_bytes_received_per_second         = {"name":"mysql_bytes_received_per_second",
                                               "value_type":"float",
                                               "units":"Bytes/s",
                                               "format":"%f"},
    mysql_bytes_sent_per_second             = {"name":"mysql_bytes_sent_per_second",
                                               "value_type":"float",
                                               "units":"Bytes/s",
                                               "format":"%f"},
    mysql_table_locks_immediate_per_second  = {"name":"mysql_table_locks_immediate_per_second",
                                               "value_type":"float",
                                               "units":"N/s",
                                               "format":"%f"},
    mysql_table_locks_waited_per_second     = {"name":"mysql_table_locks_waited_per_second",
                                               "value_type":"float",
                                               "units":"N/s",
                                               "format":"%f"},
    tokudb_txn_commits_per_second           = {"name":"tokudb_txn_commits_per_second",
                                               "value_type":"float",
                                               "units":"N/s",
                                               "format":"%f"},
    tokudb_txn_aborts_per_second            = {"name":"tokudb_txn_aborts_per_second",
                                               "value_type":"float",
                                               "units":"N/s",
                                               "format":"%f"}
)

count_metrics = dict(
    mysql_threads_connected                 = {"name":"mysql_threads_connected"},
    mysql_threads_running                   = {"name":"mysql_threads_running"},
    mysql_threads_cached                    = {"name":"mysql_threads_cached"},
    tokudb_locktree_memory_size             = {"name":"tokudb_locktree_memory_size"},
    tokudb_locktree_long_wait_count         = {"name":"tokudb_locktree_long_wait_count"},
    tokudb_locktree_timeout_count           = {"name":"tokudb_locktree_timeout_count"},
    mysql_max_used_connections              = {"name":"mysql_max_used_connections"},

)

static_metrics = dict(
    mysql_max_connections                   = {"name":"mysql_max_connections"},
    tokudb_locktree_memory_size_limit       = {"name":"tokudb_locktree_memory_size_limit"}
)

test_metrics = dict(
    test_metric0                            = {"name":"test_metric0"}
)

almost_real_metrics = dict(
    mysql_Com_select_per_second             = {"name":"mysql_Com_select_per_second",
                                               "value_type":"float",
                                               "units":"N/s"}
)