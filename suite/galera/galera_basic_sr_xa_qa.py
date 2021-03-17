#!/usr/bin/env python3
import os
import sys
import argparse
import itertools
import time
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from config import *
from util import sysbench_run
from util import utility
from util import table_checksum

# Read argument
parser = argparse.ArgumentParser(prog='Galera streaming replication XA test', usage='%(prog)s [options]')
parser.add_argument('-e', '--encryption-run', action='store_true',
                    help='This option will enable encryption options')
parser.add_argument('-d', '--debug', action='store_true',
                    help='This option will enable debug logging')
args = parser.parse_args()
if args.encryption_run is True:
    encryption = 'YES'
else:
    encryption = 'NO'
if args.debug is True:
    debug = 'YES'
else:
    debug = 'NO'

utility_cmd = utility.Utility(debug)
utility_cmd.check_python_version()


class StreamingReplicationXA:
    def start_server(self, node):
        my_extra = "--innodb_buffer_pool_size=2G --innodb_log_file_size=1G"
        utility_cmd.start_galera(parent_dir, WORKDIR, BASEDIR, node,
                                 WORKDIR + '/node1/mysql.sock', USER, encryption, my_extra)

    def sysbench_run(self, socket, db):
        # Sysbench data load
        sysbench = sysbench_run.SysbenchRun(BASEDIR, WORKDIR, socket, debug)
        result = sysbench.sanity_check(db)
        utility_cmd.check_testcase(result, "Sysbench run sanity check")
        result = sysbench.sysbench_load(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS, SYSBENCH_LOAD_TEST_TABLE_SIZE)
        utility_cmd.check_testcase(result, "Sysbench data load (threads : " + str(SYSBENCH_THREADS) + ")")

    def streaming_replication_qa(self, socket, db):
        # Streaming Replication QA
        # Create data insert procedure
        create_procedure = BASEDIR + "/bin/mysql --user=root --socket=" + socket + \
            ' ' + db + ' -Bse"source ' + cwd + '/sr_xa_procedure.sql " 2>&1'
        if debug == 'YES':
            print(create_procedure)
        result = os.system(create_procedure)
        utility_cmd.check_testcase(result, "Creating streaming replication XA data insert procedure")
        wsrep_trx_fragment_unit = ['bytes', 'rows']
        wsrep_trx_fragment_size = [1, 2, 4, 8, 16, 64, 128, 256, 512, 1024]
        row_count = [100, 1000, 10000, 100000]
        for trx_fragment_unit, trx_fragment_size, rows in \
                itertools.product(wsrep_trx_fragment_unit, wsrep_trx_fragment_size, row_count):
            sr_procedure = BASEDIR + "/bin/mysql --user=root --socket=" + socket + \
                ' -Bse"call ' + db + '.sr_xa_procedure(' + str(rows) + \
                ",'" + trx_fragment_unit + "'," + str(trx_fragment_size) + ');" 2>&1'
            if debug == 'YES':
                print(sr_procedure)
            result = os.system(sr_procedure)
            sr_combination = "DML row count " + str(rows) + ", fragment_unit : " + \
                             trx_fragment_unit + ", fragment_size : " + \
                             str(trx_fragment_size)
            utility_cmd.check_testcase(result, "SR testcase( " + sr_combination + " )")
            if trx_fragment_unit == 'bytes':
                delete_rows = BASEDIR + "/bin/mysql --user=root --socket=" + socket + \
                                   ' ' + db + ' -Bse"delete from sbtest1 limit ' + str(rows) + ';" 2>&1'
                if debug == 'YES':
                    print(delete_rows)
                os.system(delete_rows)


print("-------------------------------------------")
print("\nGalera Streaming Replication with XA test")
print("-------------------------------------------")
sr_xa = StreamingReplicationXA()
sr_xa.start_server(NODE)
sr_xa.sysbench_run(WORKDIR + '/node1/mysql.sock', 'test')
sr_xa.streaming_replication_qa(WORKDIR + '/node1/mysql.sock', 'test')
utility_cmd.stop_galera(WORKDIR, BASEDIR, NODE)
