import psycopg2
import psycopg2.extras
import syslog
import functools
import time

# Cache for postgres query values, this prevents opening db connections for each metric_handler callback
class Cache(object):
    def __init__(self, expiry):
        self.expiry = expiry
        self.curr_time = 0
        self.last_time = 0
        self.last_value = None

    def __call__(self, func):
        @functools.wraps(func)
        def deco(*args, **kwds):
            self.curr_time = time.time()
            if self.curr_time - self.last_time > self.expiry:
                self.last_value = func(*args, **kwds)
                self.last_time = self.curr_time
            return self.last_value
        return deco

# Queries update the pg_metrics dict with their values based on cache interval
@Cache(60)
def pg_metrics_queries():
    pg_metrics = {}
    db_conn = psycopg2.connect(pgdsn)
    db_curs = db_conn.cursor()

    # single session state query avoids multiple scans of pg_stat_activity
    # state is a different column name in postgres 9.2, previous versions will have to update this query accordingly
    db_curs.execute(
        'select state, waiting, \
        extract(epoch from current_timestamp - xact_start)::int, \
        extract(epoch from current_timestamp - query_start)::int from pg_stat_activity;')
    results = db_curs.fetchall()
    active = 0
    idle = 0
    idleintxn = 0
    waiting = 0
    active_results = []
    for state, waiting, xact_start_sec, query_start_sec in results:
        if state == 'active':
            active = int(active + 1)
            # build a list of query start times where query is active
            active_results.append(query_start_sec)
        if state == 'idle':
            idle = int(idle + 1)
        if state == 'idle in transaction':
            idleintxn = int(idleintxn + 1)
        if waiting == True:
            waitingtrue = int(waitingtrue + 1)

    # determine longest transaction in seconds
    sorted_by_xact = sorted(results, key=lambda tup: tup[2], reverse=True)
    longest_xact_in_sec = (sorted_by_xact[0])[2]
    
    # determine longest active query in seconds
    sorted_by_query = sorted(active_results, reverse=True)
    longest_query_in_sec = sorted_by_query[0]

    pg_metrics.update(
        {'Pypg_idle_sessions':idle,
        'Pypg_active_sessions':active,
        'Pypg_waiting_sessions':waiting,
        'Pypg_idle_in_transaction_sessions':idleintxn,
        'Pypg_longest_xact':longest_xact_in_sec,
        'Pypg_longest_query':longest_query_in_sec})
    
    # locks query
    db_curs.execute('select mode, locktype from pg_locks;')
    results = db_curs.fetchall()
    accessexclusive = 0
    otherexclusive = 0
    shared = 0
    for mode, locktype in results:
        if (mode == 'AccessExclusiveLock' and locktype != 'virtualxid'):
            accessexclusive = int(accessexclusive + 1)
        if (mode != 'AccessExclusiveLock' and locktype != 'virtualxid'):
            if 'Exclusive' in mode:
                otherexclusive = int(otherexclusive + 1)
        if ('Share' in mode and locktype != 'virtualxid'):
            shared = int(shared + 1) 
    pg_metrics.update(
        {'Pypg_locks_accessexclusive':accessexclusive,
        'Pypg_locks_otherexclusive':otherexclusive,
        'Pypg_locks_shared':shared})

    # background writer query returns one row that needs to be parsed
    db_curs.execute(
        'select checkpoints_timed, checkpoints_req, checkpoint_write_time, \
        checkpoint_sync_time, buffers_checkpoint, buffers_clean, \
        buffers_backend, buffers_alloc from pg_stat_bgwriter;')
    results = db_curs.fetchall()
    bgwriter_values = results[0]
    checkpoints_timed = int(bgwriter_values[0])
    checkpoints_req = int(bgwriter_values[1])
    checkpoint_write_time = int(bgwriter_values[2])
    checkpoint_sync_time = int(bgwriter_values[3])
    buffers_checkpoint = int(bgwriter_values[4])
    buffers_clean = int(bgwriter_values[5])
    buffers_backend = int(bgwriter_values[6])
    buffers_alloc = int(bgwriter_values[7])
    pg_metrics.update(
        {'Pypg_bgwriter_checkpoints_timed':checkpoints_timed,
        'Pypg_bgwriter_checkpoints_req':checkpoints_req,
        'Pypg_bgwriter_checkpoint_write_time':checkpoint_write_time,
        'Pypg_bgwriter_checkpoint_sync_time':checkpoint_sync_time,
        'Pypg_bgwriter_buffers_checkpoint':buffers_checkpoint,
        'Pypg_bgwriter_buffers_clean':buffers_clean,
        'Pypg_bgwriter_buffers_backend':buffers_backend,
        'Pypg_bgwriter_buffers_alloc':buffers_alloc})

    # database statistics returns one row that needs to be parsed
    db_curs.execute(
        'select (sum(xact_commit) + sum(xact_rollback)), sum(tup_inserted), \
        sum(tup_updated), sum(tup_deleted), (sum(tup_returned) + sum(tup_fetched)), \
        sum(blks_read), sum(blks_hit) from pg_stat_database;')
    results = db_curs.fetchall()
    pg_stat_db_values = results[0]
    transactions = int(pg_stat_db_values[0])
    inserts = int(pg_stat_db_values[1])
    updates = int(pg_stat_db_values[2])
    deletes = int(pg_stat_db_values[3])
    reads = int(pg_stat_db_values[4])
    blksdisk = int(pg_stat_db_values[5])
    blksmem = int(pg_stat_db_values[6])
    pg_metrics.update(
        {'Pypg_transactions':transactions,
        'Pypg_inserts':inserts,
        'Pypg_updates':updates,
        'Pypg_deletes':deletes,
        'Pypg_reads':reads,
        'Pypg_blks_diskread':blksdisk,
        'Pypg_blks_memread':blksmem})

    # table statistics returns one row that needs to be parsed
    db_curs.execute(
        'select sum(seq_tup_read), sum(idx_tup_fetch), \
        extract(epoch from now() - min(last_vacuum))::int/60/60, \
        extract(epoch from now() - min(last_analyze))::int/60/60 \
        from pg_stat_all_tables;')
    results = db_curs.fetchall()
    pg_stat_table_values = results[0]
    seqscan = int(pg_stat_table_values[0])
    idxfetch = int(pg_stat_table_values[1])
    hours_since_vacuum = int(pg_stat_table_values[2]) if pg_stat_table_values[2] != None else None
    hours_since_analyze = int(pg_stat_table_values[3]) if pg_stat_table_values[3] != None else None
    pg_metrics.update(
        {'Pypg_tup_seqscan':seqscan,
        'Pypg_tup_idxfetch':idxfetch,
        'Pypg_hours_since_last_vacuum':hours_since_vacuum,
        'Pypg_hours_since_last_analyze':hours_since_analyze})

    db_curs.close()
    return pg_metrics

# Metric handler uses dictionary pg_metrics keys to return values from queries based on metric name
def metric_handler(name):
    pg_metrics = pg_metrics_queries()
    return int(pg_metrics[name])     

# Metric descriptors are initialized here 
def metric_init(params):
    HOST = str(params.get('host'))
    PORT = str(params.get('port'))
    DB = str(params.get('dbname'))
    USER = str(params.get('username'))
    PASSWORD = str(params.get('password'))
    
    global pgdsn
    pgdsn = "dbname=" + DB + " host=" + HOST + " user=" + USER + " port=" + PORT + " password=" + PASSWORD

    descriptors = [
        {'name':'Pypg_idle_sessions','units':'Sessions','slope':'both','description':'PG Idle Sessions'},
        {'name':'Pypg_active_sessions','units':'Sessions','slope':'both','description':'PG Active Sessions'},
        {'name':'Pypg_idle_in_transaction_sessions','units':'Sessions','slope':'both','description':'PG Idle In Transaction Sessions'},
        {'name':'Pypg_waiting_sessions','units':'Sessions','slope':'both','description':'PG Waiting Sessions Blocked'},
        {'name':'Pypg_longest_xact','units':'Seconds','slope':'both','description':'PG Longest Transaction in Seconds'},
        {'name':'Pypg_longest_query','units':'Seconds','slope':'both','description':'PG Longest Query in Seconds'},
        {'name':'Pypg_locks_accessexclusive','units':'Locks','slope':'both','description':'PG AccessExclusive Locks read write blocking'},
        {'name':'Pypg_locks_otherexclusive','units':'Locks','slope':'both','description':'PG Exclusive Locks write blocking'},
        {'name':'Pypg_locks_shared','units':'Locks','slope':'both','description':'PG Shared Locks NON blocking'},
        {'name':'Pypg_bgwriter_checkpoints_timed','units':'checkpoints','slope':'positive','description':'PG scheduled checkpoints'},
        {'name':'Pypg_bgwriter_checkpoints_req','units':'checkpoints','slope':'positive','description':'PG unscheduled checkpoints'},
        {'name':'Pypg_bgwriter_checkpoint_write_time','units':'ms','slope':'positive','description':'PG time to write checkpoints to disk'},
        {'name':'Pypg_bgwriter_checkpoint_sync_time','units':'checkpoints','slope':'positive','description':'PG time to sync checkpoints to disk'},
        {'name':'Pypg_bgwriter_buffers_checkpoint','units':'buffers','slope':'positive','description':'PG number of buffers written during checkpoint'},
        {'name':'Pypg_bgwriter_buffers_clean','units':'buffers','slope':'positive','description':'PG number of buffers written by the background writer'},
        {'name':'Pypg_bgwriter_buffers_backend','units':'buffers','slope':'positive','description':'PG number of buffers written directly by a backend'},
        {'name':'Pypg_bgwriter_buffers_alloc','units':'buffers','slope':'positive','description':'PG number of buffers allocated'},
        {'name':'Pypg_transactions','units':'xacts','slope':'positive','description':'PG Transactions'},
        {'name':'Pypg_inserts','units':'tuples','slope':'positive','description':'PG Inserts'},
        {'name':'Pypg_updates','units':'tuples','slope':'positive','description':'PG Updates'},
        {'name':'Pypg_deletes','units':'tuples','slope':'positive','description':'PG Deletes'},
        {'name':'Pypg_reads','units':'tuples','slope':'positive','description':'PG Reads'},
        {'name':'Pypg_blks_diskread','units':'blocks','slope':'positive','description':'PG Blocks Read from Disk'},
        {'name':'Pypg_blks_memread','units':'blocks','slope':'positive','description':'PG Blocks Read from Memory'},
        {'name':'Pypg_tup_seqscan','units':'tuples','slope':'positive','description':'PG Tuples sequentially scanned'},
        {'name':'Pypg_tup_idxfetch','units':'tuples','slope':'positive','description':'PG Tuples fetched from indexes'},
        {'name':'Pypg_hours_since_last_vacuum','units':'hours','slope':'both','description':'PG hours since last vacuum'},
        {'name':'Pypg_hours_since_last_analyze','units':'hours','slope':'both','description':'PG hours since last analyze'}]

    for d in descriptors:
        # Add default values to dictionary
        d.update({'call_back': metric_handler, 'time_max': 90, 'value_type': 'uint', 'format': '%d', 'groups': 'Postgres'})

    return descriptors

# ganglia requires metric cleanup
def metric_cleanup():
    '''Clean up the metric module.'''
    pass

# this code is for debugging and unit testing    
if __name__ == '__main__':
    descriptors = metric_init({"host":"hostname_goes_here","port":"port_goes_here","dbname":"database_name_goes_here","username":"username_goes_here","password":"password_goes_here"})
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print 'value for %s is %u' % (d['name'],  v)
        time.sleep(5)

