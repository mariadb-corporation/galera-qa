#!/usr/bin/env python3
import os
import sys
import configparser
import argparse
import random
import time
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
node = '6'
user = config['config']['user']
socket = config['config']['node1_socket']
pt_basedir = config['config']['pt_basedir']
sysbench_user = config['sysbench']['sysbench_user']
sysbench_pass = config['sysbench']['sysbench_pass']
sysbench_db = config['sysbench']['sysbench_db']
sysbench_threads = 10
sysbench_table_size = 1000
sysbench_run_time = 1000

class ChaosMonkeyQA:
    def startup(self):
        # Start PXC cluster for ChaosMonkey test
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
        result = server_startup.start_cluster()
        utility_cmd.check_testcase(result, "Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "Database connection")

    def sysbench_run(self, socket, db):
        # Sysbench dataload for consistency test
        sysbench = sysbench_run.SysbenchRun(basedir, workdir,
                                            sysbench_user, sysbench_pass,
                                            socket, sysbench_threads,
                                            sysbench_table_size, db,
                                            sysbench_threads, sysbench_run_time)

        result = sysbench.sanity_check()
        utility_cmd.check_testcase(result, "Sysbench run sanity check")
        result = sysbench.sysbench_load()
        utility_cmd.check_testcase(result, "Sysbench data load")
        result = sysbench.sysbench_oltp_read_write()
        utility_cmd.check_testcase(result, "Initiated sysbench oltp run")

    def multi_recovery_test(self):
        """ This method will kill 2 random nodes from
            6 node cluster while sysbench is in progress
            and check data consistency after restart.
        """
        nodes = [2, 3, 4, 5, 6]
        rand_nodes = random.choices(nodes, k=2)
        self.sysbench_run(socket, 'test')
        query = 'pidof sysbench'
        sysbench_pid = os.popen(query).read().rstrip()
        for j in rand_nodes:
            query = 'cat `' + basedir + \
                    '/bin/mysql  --user=root --socket=/tmp/node' +  \
                    str(j) + '.sock -Bse"select @@pid_file"  2>&1`'
            time.sleep(1)
            pid = os.popen(query).read().rstrip()
            result = os.system('kill -9 ' + pid)
            utility_cmd.check_testcase(result, "Killed Cluster Node" + str(j) + " for ChaosMonkey QA")

        kill_sysbench = "kill -9 " + sysbench_pid
        result = os.system(kill_sysbench)
        utility_cmd.check_testcase(result, "Killed sysbench oltp run")
        time.sleep(10)

        for j in rand_nodes:
            query = 'bash ' + workdir + \
                    '/log/startup' + str(j) + '.sh'
            result = os.system(query)
            utility_cmd.check_testcase(result, "Restarting Cluster Node" + str(j))
            time.sleep(5)


print("\nPXC ChaosMonkey Style test")
print("----------------------------")
checksum = table_checksum.TableChecksum(pt_basedir, basedir, workdir, node, socket)
chaosmonkey_qa = ChaosMonkeyQA()
chaosmonkey_qa.startup()
chaosmonkey_qa.multi_recovery_test()
checksum.sanity_check()
checksum.data_consistency('test')
