#!/usr/bin/env python3
import os
import sys
import configparser
import argparse
import time
import subprocess
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
sysbench_threads = 10
sysbench_table_size = 1000
sysbench_run_time = 1000


class ClusterInteraction:
    def __init__(self, basedir, workdir, user, socket, pt_basedir, node):
        self.workdir = workdir
        self.basedir = basedir
        self.user = user
        self.socket = socket
        self.pt_basedir = pt_basedir
        self.node = node

    def run_query(self, query):
        query_status = os.system(query)
        if int(query_status) != 0:
            print("ERROR! Query execution failed: " + query)
            return 1
        return 0

    def start_pxc(self):
        # Start PXC cluster for replication test
        dbconnection_check = db_connection.DbConnection(user, '/tmp/node1.sock')
        server_startup = pxc_startup.StartCluster(parent_dir, workdir, basedir, int(self.node))
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

    def startup_check(self, cluster_node):
        """ This method will check the node recovery
            startup status.
        """
        recovery_startup = "bash " + self.workdir + \
                           '/log/startup' + str(cluster_node) + '.sh'
        os.system(recovery_startup)
        ping_query = self.basedir + '/bin/mysqladmin --user=root --socket=/tmp/node' + cluster_node + \
            '.sock ping > /dev/null 2>&1'
        for startup_timer in range(120):
            time.sleep(1)
            ping_check = subprocess.call(ping_query, shell=True, stderr=subprocess.DEVNULL)
            ping_status = ("{}".format(ping_check))
            if int(ping_status) == 0:
                utility_cmd.check_testcase(int(ping_status), "Cluster recovery is successful")
                break  # break the loop if mysqld is running

    def flow_control_qa(self):
        """ This method will help us to test cluster
            interaction using following test methods.
            1) Flow control
        """
        self.sysbench_run(self.socket, 'test')
        query = 'pidof sysbench'
        sysbench_pid = os.popen(query).read().rstrip()
        for j in range(1, int(self.node) + 1):
            query = self.basedir + "/bin/mysql --user=root --socket=" + \
                    self.socket + ' -e"set global pxc_strict_mode=DISABLED;' \
                                  '" > /dev/null 2>&1'
            self.run_query(query)
            query = self.basedir + \
                '/bin/mysql ' \
                ' --user=root --socket=/tmp/node1.sock test' \
                ' -Bse"flush table sbtest1 with read lock;' \
                'select sleep(120);unlock tables"  2>&1 &'
            os.system(query)
            flow_control_status = 'OFF'
            while flow_control_status == 'OFF':
                query = self.basedir + \
                    '/bin/mysql  --user=root --socket=/tmp/node1.sock' \
                    ' -Bse"show status like ' \
                    "'wsrep_flow_control_status';" + '"' \
                    "| awk '{ print $2 }'  2>&1"
                flow_control_status = os.system(query)
                time.sleep(1)
        kill_sysbench = "kill -9 " + sysbench_pid
        os.system(kill_sysbench)


cluster_interaction = ClusterInteraction(basedir, workdir, user, socket, pt_basedir, node)
checksum = table_checksum.TableChecksum(pt_basedir, basedir, workdir, node, socket)
print('----------------------------------------------')
print('Cluster interaction QA using flow control test')
print('----------------------------------------------')
cluster_interaction.start_pxc()
cluster_interaction.flow_control_qa()
checksum.sanity_check()
checksum.data_consistency('test')
