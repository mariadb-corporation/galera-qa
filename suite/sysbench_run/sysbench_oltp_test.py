#!/usr/bin/env python3
import os
import sys
import argparse
import time
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from config import *
from util import galera_startup
from util import db_connection
from util import sysbench_run
from util import utility
from util import table_checksum

# Read argument
parser = argparse.ArgumentParser(prog='Galera sysbench oltp test', usage='%(prog)s [options]')
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


class SysbenchOLTPTest:
    def start_server(self, socket, node):
        if SERVER == "mdg":
            my_extra = "--innodb_buffer_pool_size=8G --innodb_log_file_size=1G"
            utility_cmd.start_galera(parent_dir, WORKDIR, BASEDIR, node, socket, USER, encryption, my_extra)
        elif SERVER == "md":
            my_extra = "--innodb_buffer_pool_size=8G --innodb_log_file_size=1G"
            utility_cmd.start_md(parent_dir, WORKDIR, BASEDIR, node, socket, USER, encryption, my_extra)

    def sysbench_run(self, socket, db):
        # Sysbench OLTP Test
        threads = [32, 64, 128]
        sysbench = sysbench_run.SysbenchRun(BASEDIR, WORKDIR,
                                            socket, debug)
        for thread in threads:
            result = sysbench.sanity_check(db)
            utility_cmd.check_testcase(result, "Sysbench run sanity check")
            sysbench.sysbench_custom_oltp_load(db, 5, thread, SYSBENCH_OLTP_TEST_TABLE_SIZE)
            time.sleep(5)
            result = utility_cmd.check_table_count(BASEDIR, db, socket, WORKDIR + '/node2/mysql.sock')
            utility_cmd.check_testcase(result, "Checksum run for DB: " + db)


print("---------------------------")
print("\nGalera sysbench oltp test")
print("---------------------------")
sysbench_loadtest = SysbenchOLTPTest()
if SERVER == "mdg":
    sysbench_loadtest.start_server(WORKDIR + '/node1/mysql.sock', NODE)
    sysbench_loadtest.sysbench_run(WORKDIR + '/node1/mysql.sock', 'test')
    utility_cmd.stop_galera(WORKDIR, BASEDIR, NODE)
elif SERVER == "md":
    sysbench_loadtest.start_server(MD1_SOCKET, 1)
    sysbench_loadtest.sysbench_run(MD1_SOCKET, 'test')
    utility_cmd.stop_md(WORKDIR, BASEDIR, 1)

