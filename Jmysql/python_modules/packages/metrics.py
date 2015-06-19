# -*- coding:utf-8 -*-
# author:jianqiao.ms

throughput_metrics = dict(
    mysql_Com_change_db_per_second              = {"descrition":"mysql_change_db_per_second",
                                               "value_type":"float",
                                               "units":"N/s"},
    mysql_Com_select_per_second                 = {"descrition":"mysql_select_per_second",
                                               "value_type":"float",
                                               "units":"N/s"},
    mysql_Com_insert_per_second                 = {"descrition":"mysql_insert_per_second",
                                               "value_type":"float",
                                               "units":"N/s"},
    mysql_Com_update_per_second                 = {"descrition":"mysql_update_per_second",
                                               "value_type":"float",
                                               "units":"N/s"},
    mysql_Com_delete_per_second                 = {"descrition":"mysql_Com_delete_per_second",
                                               "value_type":"float",
                                               "units":"N/s"},
    mysql_connections_per_second            = {"descrition":"mysql_connections_per_second",
                                               "value_type":"float",
                                               "units":"N/s"},
    mysql_aborted_connects_per_second        = {"descrition":"mysql_abortd_connects_per_second",
                                               "value_type":"float",
                                               "units":"N/s"},
    mysql_bytes_received_per_second         = {"descrition":"mysql_bytes_received_per_second",
                                               "value_type":"float",
                                               "units":"Bytes/s"},
    mysql_bytes_sent_per_second             = {"descrition":"mysql_bytes_sent_per_second",
                                               "value_type":"float",
                                               "units":"Bytes/s"},
    mysql_table_locks_immediate_per_second  = {"descrition":"mysql_table_locks_immediate_per_second",
                                               "value_type":"float",
                                               "units":"N/s"},
    mysql_table_locks_waited_per_second     = {"descrition":"mysql_table_locks_waited_per_second",
                                               "value_type":"float",
                                               "units":"N/s"},
    tokudb_txn_commits_per_second     = {"descrition":"tokudb_txn_commits_per_second",
                                               "value_type":"float",
                                               "units":"N/s"},
    tokudb_txn_aborts_per_second      = {"descrition":"mysql_tokudb_txn_aborts_per_second",
                                               "value_type":"float",
                                               "units":"N/s"})

count_metrics = dict(
    mysql_threads_connected                 = {"descrition":"mysql_threads_connected",
                                               "value_type":"uint",
                                               "units":"N"},
    mysql_threads_running                   = {"descrition":"mysql_threads_running",
                                               "value_type":"uint",
                                               "units":"N"},
    mysql_threads_cached                    = {"descrition":"mysql_threads_cached",
                                               "value_type":"uint",
                                               "units":"N"},
    tokudb_locktree_memory_size             = {"descrition":"tokudb_locktree_memory_size",
                                               "value_type":"uint",
                                               "units":"N"},
    tokudb_locktree_long_wait_count         = {"descrition":"tokudb_locktree_long_wait_count",
                                               "value_type":"uint",
                                               "units":"N"},
    tokudb_locktree_timeout_count           = {"descrition":"tokudb_locktree_timeout_count",
                                               "value_type":"uint",
                                               "units":"N"},
    mysql_max_used_connections              = {"descrition":"tokudb_max_used_connections",
                                               "value_type":"uint",
                                               "units":"N"},
    tokudb_locktree_memory_size_limit       = {"descrition":"tokudb_locktree_memory_size_limit",
                                               "value_type":"uint",
                                               "units":"Byte"})

static_metrics = dict(
    mysql_max_connections                   = {"descrition":"mysql_max_used_connections",
                                               "value_type":"uint",
                                               "units":"N"})