#!/usr/bin/env python3
import os
import sys
import configparser
import argparse
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
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

# Reading initial configuration
config = configparser.ConfigParser()
config.read(parent_dir + '/config.ini')
workdir = config['config']['workdir']
basedir = config['config']['basedir']
node = config['config']['node']
user = config['config']['user']
socket = config['config']['node1_socket']
pt_basedir = config['config']['pt_basedir']
sysbench_user = config['sysbench']['sysbench_user']
sysbench_pass = config['sysbench']['sysbench_pass']
sysbench_db = config['sysbench']['sysbench_db']
sysbench_table_size = 100000
sysbench_run_time = 1000


class SysbenchLoadTest:
    def start_pxc(self):
        # Start PXC cluster for sysbench load test
        dbconnection_check = db_connection.DbConnection(user, '/tmp/node1.sock')
        server_startup = pxc_startup.StartCluster(parent_dir, workdir, basedir, int(node))
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "Startup sanity check")
        if encryption == 'YES':
            result = utility_cmd.create_ssl_certificate(workdir)
            utility_cmd.check_testcase(result, "SSL Configuration")
            result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "Configuration file creation")
        else:
            result = server_startup.create_config('none')
            utility_cmd.check_testcase(result, "Configuration file creation")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "Initializing cluster")
        result = server_startup.start_cluster('--max-connections=1500')
        utility_cmd.check_testcase(result, "Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "Database connection")

    def sysbench_run(self, socket, db):
        # Sysbench load test
        threads = [32, 64, 128, 256, 1024]
        checksum = table_checksum.TableChecksum(pt_basedir, basedir, workdir, node, socket)
        checksum.sanity_check()
        for thread in threads:
            sysbench = sysbench_run.SysbenchRun(basedir, workdir,
                                                sysbench_user, sysbench_pass,
                                                socket, thread,
                                                sysbench_table_size, db,
                                                thread, sysbench_run_time)
            if thread == 32:
                result = sysbench.sanity_check()
                utility_cmd.check_testcase(result, "Sysbench run sanity check")
            result = sysbench.sysbench_cleanup()
            utility_cmd.check_testcase(result, "Sysbench data cleanup (threads : " + str(thread) + ")")
            result = sysbench.sysbench_load()
            utility_cmd.check_testcase(result, "Sysbench data load (threads : " + str(thread) + ")")
            checksum.data_consistency('test')


print("\nPXC sysbench load test")
print("------------------------")
sysbench_loadtest = SysbenchLoadTest()
sysbench_loadtest.start_pxc()
sysbench_loadtest.sysbench_run(socket, 'test')
