#!/usr/bin/env python3
import os
import sys
import argparse
import time
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from config import *
from util import sysbench_run
from util import utility
from util import table_checksum

# Read argument
parser = argparse.ArgumentParser(prog='Galera sysbench load test', usage='%(prog)s [options]')
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


class SysbenchLoadTest:
    def start_server(self, socket, node):
        if SERVER == "pxc":
            my_extra = "--innodb_buffer_pool_size=8G --innodb_log_file_size=1G"
            utility_cmd.start_galera(parent_dir, WORKDIR, BASEDIR, node, socket, USER, encryption, my_extra)
        elif SERVER == "ps":
            my_extra = "--innodb_buffer_pool_size=8G --innodb_log_file_size=1G"
            utility_cmd.start_md(parent_dir, WORKDIR, BASEDIR, node, socket, USER, encryption, my_extra)

    def sysbench_run(self, socket, db):
        # Sysbench load test
        threads = [32, 64, 128, 256, 1024]
        for thread in threads:
            sysbench = sysbench_run.SysbenchRun(BASEDIR, WORKDIR,
                                                socket, debug)
            if thread == 32:
                result = sysbench.sanity_check(db)
                utility_cmd.check_testcase(result, "Sysbench run sanity check")
            result = sysbench.sysbench_cleanup(db, thread, thread, SYSBENCH_LOAD_TEST_TABLE_SIZE)
            utility_cmd.check_testcase(result, "Sysbench data cleanup (threads : " + str(thread) + ")")
            result = sysbench.sysbench_load(db, thread, thread, SYSBENCH_LOAD_TEST_TABLE_SIZE)
            utility_cmd.check_testcase(result, "Sysbench data load (threads : " + str(thread) + ")")
            time.sleep(5)
            result = utility_cmd.check_table_count(BASEDIR, db, socket, WORKDIR + '/node2/mysql.sock')
            utility_cmd.check_testcase(result, "Checksum run for DB: test")


print("---------------------------")
print("\nGalera sysbench load test")
print("---------------------------")
sysbench_loadtest = SysbenchLoadTest()
if SERVER == "mdg":
    sysbench_loadtest.start_server(WORKDIR + '/node1/mysql.sock', NODE)
    sysbench_loadtest.sysbench_run(WORKDIR + '/node1/mysql.sock', 'test')
    utility_cmd.stop_galera(WORKDIR, BASEDIR, NODE)
elif SERVER == "md":
    sysbench_loadtest.start_server(MD1_SOCKET, 1)
    sysbench_loadtest.sysbench_run(MD1_SOCKET, 'test')
    utility_cmd.stop_md(WORKDIR, BASEDIR, 1)
