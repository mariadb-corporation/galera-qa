#!/usr/bin/env python3
import os
import sys
import argparse
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
parser = argparse.ArgumentParser(prog='PXC replication test', usage='%(prog)s [options]')
parser.add_argument('-e', '--encryption-run', action='store_true',
                    help='This option will enable encryption options')
args = parser.parse_args()
if args.encryption_run is True:
    encryption = 'YES'
else:
    encryption = 'NO'


class SysbenchLoadTest:
    def start_pxc(self):
        my_extra = ""
        utility_cmd.start_pxc(parent_dir, WORKDIR, BASEDIR, NODE, NODE1_SOCKET, USER, encryption, my_extra)

    def sysbench_run(self, node1_socket, db):
        # Sysbench load test
        threads = [32, 64, 128]
        version = utility_cmd.version_check(BASEDIR)
        if int(version) < int("080000"):
            checksum = table_checksum.TableChecksum(PT_BASEDIR, BASEDIR, WORKDIR, NODE, NODE1_SOCKET)
            checksum.sanity_check()
        sysbench = sysbench_run.SysbenchRun(BASEDIR, WORKDIR,
                                            node1_socket)
        result = sysbench.sanity_check(db)
        utility_cmd.check_testcase(result, "Sysbench run sanity check")
        result = sysbench.sysbench_custom_table(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS,
                                                SYSBENCH_CUSTOMIZED_DATALOAD_TABLE_SIZE)
        utility_cmd.check_testcase(result, "Sysbench data load")


print("----------------------------------------")
print("\nPXC sysbench customized data load test")
print("----------------------------------------")
sysbench_loadtest = SysbenchLoadTest()
sysbench_loadtest.start_pxc()
sysbench_loadtest.sysbench_run(NODE1_SOCKET, 'test')
