#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
import time
from datetime import datetime
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from config import *
from util import galera_startup
from util import md_startup
from util import db_connection
from util import sysbench_run
from util import utility
from util import rqg_datagen

# Read argument
parser = argparse.ArgumentParser(prog='Galera upgrade test', usage='%(prog)s [options]')
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


class PXCUpgrade:
    def startup(self, replication_conf):
        # Start Galera cluster for upgrade test
        dbconnection_check = db_connection.DbConnection(USER, WORKDIR + '/node1/mysql.sock')
        server_startup = galera_startup.StartCluster(parent_dir, WORKDIR, GALERA_LOWER_BASE, int(NODE), debug)
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "Startup sanity check")
        if encryption == 'YES':
            result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "Configuration file creation")
        else:
            result = server_startup.create_config('none')
            utility_cmd.check_testcase(result, "Configuration file creation")
        result = server_startup.add_myextra_configuration(parent_dir + '/suite/replication/' + replication_conf)
        utility_cmd.check_testcase(result, "Galera: Adding custom configuration")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "Initializing cluster")
        result = server_startup.start_cluster()
        utility_cmd.check_testcase(result, "Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "Database connection")

    def start_md(self, node, replication_conf, my_extra=None):
        """ Start MariaDB Server. This method will
            perform sanity checks for PS startup
            :param my_extra: We can pass extra PS startup
                             option with this parameter
        """
        if my_extra is None:
            my_extra = ''
        # Start Galera cluster for replication test
        dbconnection_check = db_connection.DbConnection(USER, MD1_SOCKET)
        server_startup = md_startup.StartPerconaServer(parent_dir, WORKDIR, GALERA_LOWER_BASE, int(node), debug)
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "MD: Startup sanity check")
        if encryption == 'YES':
            result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "MD: Configuration file creation")
        else:
            result = server_startup.create_config()
            utility_cmd.check_testcase(result, "MD: Configuration file creation")
        result = server_startup.add_myextra_configuration(parent_dir + '/suite/replication/' + replication_conf)
        utility_cmd.check_testcase(result, "MD: Adding custom configuration")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "MD: Initializing cluster")
        result = server_startup.start_server(my_extra)
        utility_cmd.check_testcase(result, "MD: Server startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "MD: Database connection")

    def sysbench_run(self, node1_socket, db, upgrade_type):
        # Sysbench dataload for consistency test
        sysbench_node1 = sysbench_run.SysbenchRun(GALERA_LOWER_BASE, WORKDIR,
                                                  node1_socket, debug)

        result = sysbench_node1.sanity_check(db)
        utility_cmd.check_testcase(result, "Sysbench run sanity check")
        result = sysbench_node1.sysbench_load(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS, SYSBENCH_NORMAL_TABLE_SIZE)
        utility_cmd.check_testcase(result, "Sysbench data load")
        sysbench_node2 = sysbench_run.SysbenchRun(GALERA_LOWER_BASE, WORKDIR,
                                                  WORKDIR + '/node2/mysql.sock', debug)
        sysbench_node3 = sysbench_run.SysbenchRun(GALERA_LOWER_BASE, WORKDIR,
                                                  WORKDIR + '/node3/mysql.sock', debug)
        if upgrade_type == 'readwrite':
            result = sysbench_node1.sysbench_oltp_read_write(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS,
                                                             SYSBENCH_NORMAL_TABLE_SIZE, 1000, 'Yes')
            utility_cmd.check_testcase(result, "Initiated sysbench oltp run on node1")
            result = sysbench_node2.sysbench_oltp_read_write(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS,
                                              SYSBENCH_NORMAL_TABLE_SIZE, 1000, 'Yes')
            utility_cmd.check_testcase(result, "Initiated sysbench oltp run on node2")
            result = sysbench_node3.sysbench_oltp_read_write(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS,
                                              SYSBENCH_NORMAL_TABLE_SIZE, 1000, 'Yes')
            utility_cmd.check_testcase(result, "Initiated sysbench oltp run on node3")
        elif upgrade_type == 'readonly':
            result = sysbench_node1.sysbench_oltp_read_only(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS,
                                              SYSBENCH_NORMAL_TABLE_SIZE, 1000, 'Yes')
            utility_cmd.check_testcase(result, "Initiated sysbench readonly run on node1")
            result = sysbench_node2.sysbench_oltp_read_only(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS,
                                              SYSBENCH_NORMAL_TABLE_SIZE, 1000, 'Yes')
            utility_cmd.check_testcase(result, "Initiated sysbench readonly run on node2")
            result = sysbench_node3.sysbench_oltp_read_only(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS,
                                              SYSBENCH_NORMAL_TABLE_SIZE, 1000, 'Yes')
            utility_cmd.check_testcase(result, "Initiated sysbench readonly run on node3")

    def startup_check(self, cluster_node):
        """ This method will check the node
            startup status.
        """
        ping_query = GALERA_LOWER_BASE + '/bin/mysqladmin --user=root --socket=' + \
            WORKDIR + '/node' + str(cluster_node) + \
            '/mysql.sock ping > /dev/null 2>&1'
        for startup_timer in range(120):
            time.sleep(1)
            ping_check = subprocess.call(ping_query, shell=True, stderr=subprocess.DEVNULL)
            ping_status = ("{}".format(ping_check))
            if int(ping_status) == 0:
                utility_cmd.check_testcase(int(ping_status), "Node startup is successful")
                break  # break the loop if mysqld is running

    def rolling_upgrade(self, upgrade_type):
        """ This function will upgrade
            MariaDB Galera Cluster to
            latest version and perform
            table checksum.
        """
        self.sysbench_run('/tmp/mdnode1.sock', 'sbtest', upgrade_type)
        time.sleep(10)
        for i in range(int(NODE), 0, -1):
            query = "ps -ef | grep sysbench | grep -v gep | grep node" + \
                                 str(i) + " | awk '{print $2}'"
            sysbench_pid = os.popen(query).read().rstrip()
            kill_sysbench = "kill -9 " + sysbench_pid + " > /dev/null 2>&1"
            if debug == 'YES':
                print("Terminating sysbench run : " + kill_sysbench)
            os.system(kill_sysbench)
            shutdown_node = GALERA_LOWER_BASE + '/bin/mysqladmin --user=root --socket=' + \
                WORKDIR + '/node' + str(i) + \
                '/mysql.sock shutdown > /dev/null 2>&1'
            if debug == 'YES':
                print(shutdown_node)
            result = os.system(shutdown_node)
            utility_cmd.check_testcase(result, "Shutdown cluster node" + str(i) + " for upgrade testing")
            startup_cmd = GALERA_UPPER_BASE + '/bin/mysqld --defaults-file=' + \
                WORKDIR + '/conf/node' + str(i) + '.cnf --wsrep-provider=' + \
                GALERA_UPPER_BASE + '/lib/libgalera_smm.so --datadir=' + \
                WORKDIR + '/node' + str(i) + ' --basedir=' + GALERA_UPPER_BASE + ' --log-error=' + \
                WORKDIR + '/log/upgrade_node' + str(i) + '.err >> ' + \
                WORKDIR + '/log/upgrade_node' + str(i) + '.err 2>&1 &'
            utility_cmd.check_testcase(0, "Starting cluster node" + str(i) + " with upgraded version")

            if debug == 'YES':
                print(startup_cmd)
            os.system(startup_cmd)
            self.startup_check(i)
            upgrade_cmd = GALERA_UPPER_BASE + '/bin/mysql_upgrade -uroot --socket=' + \
                WORKDIR + '/node' + str(i) + \
                '/mysql.sock --skip-write-binlog > ' + WORKDIR + '/log/node' + str(i) + '_upgrade.log 2>&1'
            if debug == 'YES':
                print(upgrade_cmd)
            result = os.system(upgrade_cmd)
            utility_cmd.check_testcase(result, "Cluster node" + str(i) + " upgrade is successful")

        time.sleep(10)
        utility_cmd.replication_io_status(BASEDIR, WORKDIR + '/node3/mysql.sock', 'Galera slave', 'none')
        utility_cmd.replication_sql_status(BASEDIR, WORKDIR + '/node3/mysql.sock', 'Galera slave', 'none')
        sysbench_node = sysbench_run.SysbenchRun(GALERA_LOWER_BASE, WORKDIR,
                                                 WORKDIR + '/node1/mysql.sock', debug)
        result = sysbench_node.sysbench_oltp_read_write('sbtest', SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS,
                                                        SYSBENCH_NORMAL_TABLE_SIZE, 100)
        utility_cmd.check_testcase(result, "Sysbench oltp run after upgrade")
        time.sleep(15)

        result = utility_cmd.check_table_count(GALERA_UPPER_BASE, 'sbtest',
                                               WORKDIR + '/node1/mysql.sock',
                                               WORKDIR + '/node2/mysql.sock')
        utility_cmd.check_testcase(result, "Checksum run for DB: sbtest")
        result = utility_cmd.check_table_count(GALERA_UPPER_BASE, 'db_galera',
                                               WORKDIR + '/node1/mysql.sock',
                                               WORKDIR + '/node2/mysql.sock')
        utility_cmd.check_testcase(result, "Checksum run for DB: db_galera")
        result = utility_cmd.check_table_count(GALERA_UPPER_BASE, 'db_transactions',
                                               WORKDIR + '/node1/mysql.sock',
                                               WORKDIR + '/node2/mysql.sock')
        utility_cmd.check_testcase(result, "Checksum run for DB: db_transactions")
        result = utility_cmd.check_table_count(GALERA_UPPER_BASE, 'db_partitioning',
                                               WORKDIR + '/node1/mysql.sock',
                                               WORKDIR + '/node2/mysql.sock')
        utility_cmd.check_testcase(result, "Checksum run for DB: db_partitioning")

        utility_cmd.stop_galera(WORKDIR, GALERA_UPPER_BASE, NODE)
        utility_cmd.stop_galera(WORKDIR, GALERA_LOWER_BASE, 1)


query = GALERA_LOWER_BASE + "/bin/mysqld --version 2>&1 | grep -oe '[0-9]\.[0-9][\.0-9]*' | head -n1"
lower_version = os.popen(query).read().rstrip()
query = GALERA_UPPER_BASE + "/bin/mysqld --version 2>&1 | grep -oe '[0-9]\.[0-9][\.0-9]*' | head -n1"
upper_version = os.popen(query).read().rstrip()
version = utility_cmd.version_check(GALERA_UPPER_BASE)
print('------------------------------------------------------------------------------------------')
print("\nGalera Asyc non-gtid replication upgrade test : Upgrading from Galera-" + lower_version +
      " to Galera-" + upper_version)
print('------------------------------------------------------------------------------------------')
upgrade_qa = PXCUpgrade()
upgrade_qa.startup('replication.cnf')
upgrade_qa.start_md('1', 'replication.cnf')
utility_cmd.invoke_replication(GALERA_LOWER_BASE, '/tmp/mdnode1.sock',
                               WORKDIR + '/node3/mysql.sock', 'NONGTID', 'none')
utility_cmd.replication_io_status(GALERA_LOWER_BASE, WORKDIR + '/node3/mysql.sock', 'Galera slave', 'none')
utility_cmd.replication_sql_status(GALERA_LOWER_BASE, WORKDIR + '/node3/mysql.sock', 'Galera slave', 'none')
rqg_dataload = rqg_datagen.RQGDataGen(GALERA_LOWER_BASE, WORKDIR, USER, debug)
rqg_dataload.galera_dataload(WORKDIR + '/node1/mysql.sock')
upgrade_qa.rolling_upgrade('none')

print('--------------------------------------------------------------------------------------')
print("\nGalera Asyc gtid replication upgrade test : Upgrading from Galera-" + lower_version +
      " to Galera-" + upper_version)
print('--------------------------------------------------------------------------------------')
upgrade_qa.startup('gtid_replication.cnf')
upgrade_qa.start_md('1', 'gtid_replication.cnf')
utility_cmd.invoke_replication(GALERA_LOWER_BASE, '/tmp/mdnode1.sock',
                               WORKDIR + '/node3/mysql.sock', 'GTID', 'none')
utility_cmd.replication_io_status(GALERA_LOWER_BASE, WORKDIR + '/node3/mysql.sock', 'Galera slave', 'none')
utility_cmd.replication_sql_status(GALERA_LOWER_BASE, WORKDIR + '/node3/mysql.sock', 'Galera slave', 'none')
rqg_dataload = rqg_datagen.RQGDataGen(GALERA_LOWER_BASE, WORKDIR, USER, debug)
rqg_dataload.galera_dataload(WORKDIR + '/node1/mysql.sock')
upgrade_qa.rolling_upgrade('none')
