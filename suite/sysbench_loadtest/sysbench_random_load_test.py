#!/usr/bin/env python3
import os
import time
import sys
import argparse
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from config import *
from util import sysbench_run
from util import utility
from util import table_checksum


# Read argument
parser = argparse.ArgumentParser(prog='PXC sysbench random load test', usage='%(prog)s [options]')
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


class SysbenchRandomLoadTest:
    def start_server(self, socket, node):
        if SERVER == "pxc":
            my_extra = "--innodb_buffer_pool_size=8G --innodb_log_file_size=1G"
            utility_cmd.start_pxc(parent_dir, WORKDIR, BASEDIR, node, socket, USER, encryption, my_extra)
        elif SERVER == "ps":
            my_extra = "--innodb_buffer_pool_size=8G --innodb_log_file_size=1G"
            utility_cmd.start_ps(parent_dir, WORKDIR, BASEDIR, node, socket, USER, encryption, my_extra)

    def sysbench_run(self, socket, db):
        checksum = ""
        # Sysbench load test
        tables = [50, 100, 300, 600, 1000]
        threads = [32, 64, 128, 256, 512, 1024]
        version = utility_cmd.version_check(BASEDIR)
        if int(version) < int("080000"):
            checksum = table_checksum.TableChecksum(PT_BASEDIR, BASEDIR, WORKDIR, NODE, socket, debug)
            checksum.sanity_check()
        sysbench = sysbench_run.SysbenchRun(BASEDIR, WORKDIR,
                                            socket, debug)
        result = sysbench.sanity_check(db)
        for table_count in tables:
            utility_cmd.check_testcase(result, "Sysbench run sanity check")
            result = sysbench.sysbench_cleanup(db, table_count, table_count, SYSBENCH_RANDOM_LOAD_TABLE_SIZE)
            utility_cmd.check_testcase(result, "Sysbench data cleanup (threads : " + str(table_count) + ")")
            result = sysbench.sysbench_load(db, table_count, table_count, SYSBENCH_RANDOM_LOAD_TABLE_SIZE)
            utility_cmd.check_testcase(result, "Sysbench data load (threads : " + str(table_count) + ")")
            for thread in threads:
                sysbench.sysbench_oltp_read_write(db, table_count, thread,
                                                  SYSBENCH_RANDOM_LOAD_TABLE_SIZE, SYSBENCH_RANDOM_LOAD_RUN_TIME)
                time.sleep(5)
                result = utility_cmd.check_table_count(BASEDIR, db, socket, WORKDIR + '/node2/mysql.sock')
                utility_cmd.check_testcase(result, "Checksum run for DB: " + db)


print("-------------------------------")
print("\nPXC sysbench random load test")
print("-------------------------------")
sysbench_random_loadtest = SysbenchRandomLoadTest()
if SERVER == "pxc":
    sysbench_random_loadtest.start_server(WORKDIR + '/node1/mysql.sock', NODE)
    sysbench_random_loadtest.sysbench_run(WORKDIR + '/node1/mysql.sock', 'test')
    utility_cmd.stop_pxc(WORKDIR, BASEDIR, NODE)
elif SERVER == "ps":
    sysbench_random_loadtest.start_server(PS1_SOCKET, 1)
    sysbench_random_loadtest.sysbench_run(PS1_SOCKET, 'test')
    utility_cmd.stop_ps(WORKDIR, BASEDIR, 1)
