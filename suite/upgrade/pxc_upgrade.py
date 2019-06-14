#!/usr/bin/env python3
import os
import sys
import configparser
import argparse
import subprocess
import time
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from util import pxc_startup
from util import db_connection
from util import sysbench_run
from util import utility
from util import rqg_datagen
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
pxc_lower_base = config['upgrade']['pxc_lower_base']
pxc_upper_base = config['upgrade']['pxc_upper_base']
node = '3'
user = config['config']['user']
socket = config['config']['node1_socket']
pt_basedir = config['config']['pt_basedir']
sysbench_user = config['sysbench']['sysbench_user']
sysbench_pass = config['sysbench']['sysbench_pass']
sysbench_db = config['sysbench']['sysbench_db']
sysbench_threads = 10
sysbench_table_size = 1000
sysbench_run_time = 1000


class PXCUpgrade:
    def startup(self):
        # Start PXC cluster for upgrade test
        dbconnection_check = db_connection.DbConnection(user, socket)
        server_startup = pxc_startup.StartCluster(parent_dir, workdir, pxc_lower_base, int(node))
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
        sysbench = sysbench_run.SysbenchRun(pxc_lower_base, workdir,
                                            sysbench_user, sysbench_pass,
                                            socket, sysbench_threads,
                                            sysbench_table_size, db,
                                            sysbench_threads, sysbench_run_time)

        result = sysbench.sanity_check()
        utility_cmd.check_testcase(result, "Sysbench run sanity check")
        result = sysbench.sysbench_load()
        utility_cmd.check_testcase(result, "Sysbench data load")

    def startup_check(self, cluster_node):
        """ This method will check the node
            startup status.
        """
        ping_query = pxc_lower_base + '/bin/mysqladmin --user=root --socket=/tmp/node' + str(cluster_node) + \
            '.sock ping > /dev/null 2>&1'
        for startup_timer in range(120):
            time.sleep(1)
            ping_check = subprocess.call(ping_query, shell=True, stderr=subprocess.DEVNULL)
            ping_status = ("{}".format(ping_check))
            if int(ping_status) == 0:
                utility_cmd.check_testcase(int(ping_status), "Node startup is successful")
                break  # break the loop if mysqld is running

    def upgrade(self):
        """ This function will upgrade
            Percona XtraDB Cluster to
            latest version and perform
            table checksum.
        """
        self.sysbench_run(socket, 'test')
        for i in range(int(node), 0, -1):
            shutdown_node = pxc_lower_base + '/bin/mysqladmin --user=root --socket=/tmp/node' + str(i) + \
                '.sock shutdown > /dev/null 2>&1'
            result = os.system(shutdown_node)
            utility_cmd.check_testcase(result, "Shutdown cluster node" + str(i) + " for upgrade testing")
            startup_cmd = pxc_upper_base + '/bin/mysqld --defaults-file=' + \
                workdir + '/conf/node' + str(i) + '.cnf --datadir=' + \
                workdir + '/node' + str(i) + ' --basedir=' + pxc_upper_base + \
                ' --wsrep-provider=none --log-error=' + \
                workdir + '/log/node' + str(i) + '.err > ' + \
                workdir + '/log/node' + str(i) + '.err 2>&1 &'
            os.system(startup_cmd)
            self.startup_check(i)
            upgrade_cmd = pxc_upper_base + '/bin/mysql_upgrade -uroot --socket=/tmp/node' + \
                str(i) + '.sock > ' + workdir + '/log/node' + str(i) + '_upgrade.log 2>&1'
            result = os.system(upgrade_cmd)
            utility_cmd.check_testcase(result, "Cluster node" + str(i) + " upgrade is successful")
            shutdown_node = pxc_upper_base + '/bin/mysqladmin --user=root --socket=/tmp/node' + str(i) + \
                '.sock shutdown > /dev/null 2>&1'
            result = os.system(shutdown_node)
            utility_cmd.check_testcase(result, "Shutdown cluster node" + str(i) + " after upgrade run")
            create_startup = 'sed  "s#' + pxc_lower_base + '#' + pxc_upper_base + \
                '#g" ' + workdir + '/log/startup' + str(i) + '.sh > ' + \
                workdir + '/log/upgrade_startup' + str(i) + '.sh'
            os.system(create_startup)
            if i == 1:
                remove_bootstrap_option = 'sed -i "s#--wsrep-new-cluster##g" ' + \
                    workdir + '/log/upgrade_startup' + str(i) + '.sh'
                os.system(remove_bootstrap_option)
            time.sleep(5)
            upgrade_startup = "bash " + workdir + \
                              '/log/upgrade_startup' + str(i) + '.sh'
            result = os.system(upgrade_startup)
            utility_cmd.check_testcase(result, "Starting cluster node" + str(i) + " after upgrade run")
            self.startup_check(i)


query = pxc_lower_base + "/bin/mysqld --version 2>&1 | grep -oe '[0-9]\.[0-9][\.0-9]*' | head -n1"
lower_version = os.popen(query).read().rstrip()
query = pxc_upper_base + "/bin/mysqld --version 2>&1 | grep -oe '[0-9]\.[0-9][\.0-9]*' | head -n1"
upper_version = os.popen(query).read().rstrip()
print("\nPXC Upgrade test : Upgrading from PXC-" + lower_version + " to PXC-" + upper_version)
print("------------------------------------------------------------------------------")
checksum = table_checksum.TableChecksum(pt_basedir, pxc_upper_base, workdir, node, socket)
upgrade_qa = PXCUpgrade()
upgrade_qa.startup()
rqg_dataload = rqg_datagen.RQGDataGen(pxc_lower_base, workdir,
                                      'galera', user)
rqg_dataload.initiate_rqg('rqg_galera', socket)
rqg_dataload = rqg_datagen.RQGDataGen(pxc_lower_base, workdir,
                                      'transactions', user)
rqg_dataload.initiate_rqg('rqg_transactions', socket)
rqg_dataload = rqg_datagen.RQGDataGen(pxc_lower_base, workdir,
                                      'partitioning', user)
rqg_dataload.initiate_rqg('rqg_partitioning', socket)
upgrade_qa.upgrade()
checksum.sanity_check()
checksum.data_consistency('test,rqg_galera,rqg_transactions,rqg_partitioning')
