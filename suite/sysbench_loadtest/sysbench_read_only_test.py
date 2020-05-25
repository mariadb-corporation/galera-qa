#!/usr/bin/env python3
import os
import sys
import argparse
import time
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from config import *
from util import pxc_startup
from util import db_connection
from util import sysbench_run
from util import utility
from util import table_checksum
utility_cmd = utility.Utility()
utility_cmd.check_python_version()

# Read argument
parser = argparse.ArgumentParser(prog='PXC sysbench read only test', usage='%(prog)s [options]')
parser.add_argument('-e', '--encryption-run', action='store_true',
                    help='This option will enable encryption options')
args = parser.parse_args()
if args.encryption_run is True:
    encryption = 'YES'
else:
    encryption = 'NO'


class SysbenchReadOnlyTest:
    def start_server(self, socket, node):
        if SERVER == "pxc":
            my_extra = "--innodb_buffer_pool_size=8G --innodb_log_file_size=1G"
            utility_cmd.start_pxc(parent_dir, WORKDIR, BASEDIR, node, socket, USER, encryption, my_extra)
        elif SERVER == "ps":
            my_extra = "--innodb_buffer_pool_size=8G --innodb_log_file_size=1G"
            utility_cmd.start_ps(parent_dir, WORKDIR, BASEDIR, node, socket, USER, encryption, my_extra)

    def sysbench_run(self, socket, db):
        # Sysbench load test
        threads = [32, 64, 128]
        version = utility_cmd.version_check(BASEDIR)
        if int(version) < int("080000"):
            checksum = table_checksum.TableChecksum(PT_BASEDIR, BASEDIR, WORKDIR, NODE, socket)
            checksum.sanity_check()
        sysbench = sysbench_run.SysbenchRun(BASEDIR, WORKDIR,
                                            socket)
        for thread in threads:
            result = sysbench.sanity_check(db)
            utility_cmd.check_testcase(result, "Sysbench run sanity check")
            sysbench.sysbench_custom_read_qa(db, 5, thread, SYSBENCH_READ_QA_TABLE_SIZE)
            time.sleep(5)
#           if int(version) < int("080000"):
#               checksum.data_consistency(db)
#           else:
            result = utility_cmd.check_table_count(BASEDIR, db, socket, WORKDIR + '/node2/mysql.sock')
            utility_cmd.check_testcase(result, "Checksum run for DB: " + db)


print("-----------------------------")
print("\nPXC sysbench read only test")
print("-----------------------------")
sysbench_loadtest = SysbenchReadOnlyTest()
if SERVER == "pxc":
    sysbench_loadtest.start_server(WORKDIR + '/node1/mysql.sock', NODE)
    sysbench_loadtest.sysbench_run(WORKDIR + '/node1/mysql.sock', 'test')
    utility_cmd.stop_pxc(WORKDIR, BASEDIR, NODE)
elif SERVER == "ps":
    sysbench_loadtest.start_server(PS1_SOCKET, 1)
    sysbench_loadtest.sysbench_run(PS1_SOCKET, 'test')
    utility_cmd.stop_pxc(WORKDIR, BASEDIR, 1)
