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
from util import pxc_startup
from util import ps_startup
from util import db_connection
from util import sysbench_run
from util import utility
from util import rqg_datagen

# Read argument
parser = argparse.ArgumentParser(prog='PXC upgrade test', usage='%(prog)s [options]')
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
        # Start PXC cluster for upgrade test
        dbconnection_check = db_connection.DbConnection(USER, WORKDIR + '/node1/mysql.sock')
        server_startup = pxc_startup.StartCluster(parent_dir, WORKDIR, PXC_LOWER_BASE, int(NODE), debug)
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "Startup sanity check")
        if encryption == 'YES':
            result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "Configuration file creation")
        else:
            result = server_startup.create_config('none')
            utility_cmd.check_testcase(result, "Configuration file creation")
        result = server_startup.add_myextra_configuration(parent_dir + '/suite/replication/' + replication_conf)
        utility_cmd.check_testcase(result, "PXC: Adding custom configuration")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "Initializing cluster")
        result = server_startup.start_cluster()
        utility_cmd.check_testcase(result, "Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "Database connection")

    def start_ps(self, node, replication_conf, my_extra=None):
        """ Start Percona Server. This method will
            perform sanity checks for PS startup
            :param my_extra: We can pass extra PS startup
                             option with this parameter
        """
        if my_extra is None:
            my_extra = ''
        # Start PXC cluster for replication test
        dbconnection_check = db_connection.DbConnection(USER, PS1_SOCKET)
        server_startup = ps_startup.StartPerconaServer(parent_dir, WORKDIR, PXC_LOWER_BASE, int(node), debug)
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "PS: Startup sanity check")
        if encryption == 'YES':
            result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "PS: Configuration file creation")
        else:
            result = server_startup.create_config()
            utility_cmd.check_testcase(result, "PS: Configuration file creation")
        result = server_startup.add_myextra_configuration(parent_dir + '/suite/replication/' + replication_conf)
        utility_cmd.check_testcase(result, "PS: Adding custom configuration")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "PS: Initializing cluster")
        result = server_startup.start_server(my_extra)
        utility_cmd.check_testcase(result, "PS: Server startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "PS: Database connection")

    def sysbench_run(self, node1_socket, db, upgrade_type):
        # Sysbench dataload for consistency test
        sysbench_node1 = sysbench_run.SysbenchRun(PXC_LOWER_BASE, WORKDIR,
                                                  node1_socket, debug)

        result = sysbench_node1.sanity_check(db)
        utility_cmd.check_testcase(result, "Sysbench run sanity check")
        result = sysbench_node1.sysbench_load(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS, SYSBENCH_NORMAL_TABLE_SIZE)
        utility_cmd.check_testcase(result, "Sysbench data load")
        version = utility_cmd.version_check(PXC_LOWER_BASE)
        if int(version) > int("050700"):
            if encryption == 'YES':
                for i in range(1, int(SYSBENCH_TABLE_COUNT) + 1):
                    encrypt_table = PXC_LOWER_BASE + '/bin/mysql --user=root ' \
                        '--socket=' + WORKDIR + '/node1/mysql.sock -e "' \
                        ' alter table ' + db + '.sbtest' + str(i) + \
                        " encryption='Y'" \
                        '"; > /dev/null 2>&1'
                    if debug == 'YES':
                        print(encrypt_table)
                    os.system(encrypt_table)
        sysbench_node2 = sysbench_run.SysbenchRun(PXC_LOWER_BASE, WORKDIR,
                                                  WORKDIR + '/node2/mysql.sock', debug)
        sysbench_node3 = sysbench_run.SysbenchRun(PXC_LOWER_BASE, WORKDIR,
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
        ping_query = PXC_LOWER_BASE + '/bin/mysqladmin --user=root --socket=' + \
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
            Percona XtraDB Cluster to
            latest version and perform
            table checksum.
        """
        self.sysbench_run(WORKDIR + '/node1/mysql.sock', 'test', upgrade_type)
        self.sysbench_run('/tmp/psnode1.sock', 'sbtest', upgrade_type)
        time.sleep(10)
        for i in range(int(NODE), 0, -1):
            query = "ps -ef | grep sysbench | grep -v gep | grep node" + \
                                 str(i) + " | awk '{print $2}'"
            sysbench_pid = os.popen(query).read().rstrip()
            kill_sysbench = "kill -9 " + sysbench_pid + " > /dev/null 2>&1"
            if debug == 'YES':
                print("Terminating sysbench run : " + kill_sysbench)
            os.system(kill_sysbench)
            shutdown_node = PXC_LOWER_BASE + '/bin/mysqladmin --user=root --socket=' + \
                WORKDIR + '/node' + str(i) + \
                '/mysql.sock shutdown > /dev/null 2>&1'
            if debug == 'YES':
                print(shutdown_node)
            result = os.system(shutdown_node)
            utility_cmd.check_testcase(result, "Shutdown cluster node" + str(i) + " for upgrade testing")
            version = utility_cmd.version_check(PXC_UPPER_BASE)
            if int(version) > int("080000"):
                os.system("sed -i '/wsrep_sst_auth=root:/d' " + WORKDIR + '/conf/node' + str(i) + '.cnf')
                startup_cmd = PXC_UPPER_BASE + '/bin/mysqld --defaults-file=' + \
                    WORKDIR + '/conf/node' + str(i) + '.cnf --datadir=' + \
                    WORKDIR + '/node' + str(i) + ' --basedir=' + PXC_UPPER_BASE + ' --log-error=' + \
                    WORKDIR + '/log/upgrade_node' + str(i) + '.err >> ' + \
                    WORKDIR + '/log/upgrade_node' + str(i) + '.err 2>&1 &'
            else:
                startup_cmd = PXC_UPPER_BASE + '/bin/mysqld --defaults-file=' + \
                    WORKDIR + '/conf/node' + str(i) + '.cnf --datadir=' + \
                    WORKDIR + '/node' + str(i) + ' --basedir=' + PXC_UPPER_BASE + \
                    ' --wsrep-provider=none --log-error=' + \
                    WORKDIR + '/log/upgrade_node' + str(i) + '.err >> ' + \
                    WORKDIR + '/log/upgrade_node' + str(i) + '.err 2>&1 &'
            if debug == 'YES':
                print(startup_cmd)
            os.system(startup_cmd)
            self.startup_check(i)
            if int(version) < int("080000"):
                upgrade_cmd = PXC_UPPER_BASE + '/bin/mysql_upgrade -uroot --socket=' + \
                    WORKDIR + '/node' + str(i) + \
                    '/mysql.sock > ' + WORKDIR + '/log/node' + str(i) + '_upgrade.log 2>&1'
                if debug == 'YES':
                    print(upgrade_cmd)
                result = os.system(upgrade_cmd)
                utility_cmd.check_testcase(result, "Cluster node" + str(i) + " upgrade is successful")
            shutdown_node = PXC_UPPER_BASE + '/bin/mysqladmin --user=root --socket=' + \
                WORKDIR + '/node' + str(i) + \
                '/mysql.sock shutdown > /dev/null 2>&1'
            if debug == 'YES':
                print(shutdown_node)
            result = os.system(shutdown_node)
            utility_cmd.check_testcase(result, "Shutdown cluster node" + str(i) + " after upgrade run")
            create_startup = 'sed  "s#' + PXC_LOWER_BASE + '#' + PXC_UPPER_BASE + \
                '#g" ' + WORKDIR + '/log/startup' + str(i) + '.sh > ' + \
                WORKDIR + '/log/upgrade_startup' + str(i) + '.sh'
            if debug == 'YES':
                print(create_startup)
            os.system(create_startup)
            if i == 1:
                remove_bootstrap_option = 'sed -i "s#--wsrep-new-cluster##g" ' + \
                    WORKDIR + '/log/upgrade_startup' + str(i) + '.sh'
                if debug == 'YES':
                    print(remove_bootstrap_option)
                os.system(remove_bootstrap_option)
            time.sleep(5)

            upgrade_startup = "bash " + WORKDIR + \
                              '/log/upgrade_startup' + str(i) + '.sh'
            if debug == 'YES':
                print(upgrade_startup)
            result = os.system(upgrade_startup)
            utility_cmd.check_testcase(result, "Starting cluster node" + str(i) + " after upgrade run")
            self.startup_check(i)
        time.sleep(10)
        utility_cmd.replication_io_status(BASEDIR, WORKDIR + '/node3/mysql.sock', 'PXC slave', 'none')
        utility_cmd.replication_sql_status(BASEDIR, WORKDIR + '/node3/mysql.sock', 'PXC slave', 'none')
        sysbench_node = sysbench_run.SysbenchRun(PXC_LOWER_BASE, WORKDIR,
                                                 WORKDIR + '/node1/mysql.sock', debug)
        result = sysbench_node.sysbench_oltp_read_write('test', SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS,
                                                        SYSBENCH_NORMAL_TABLE_SIZE, 100)
        utility_cmd.check_testcase(result, "Sysbench oltp run after upgrade")
        time.sleep(5)

        result = utility_cmd.check_table_count(PXC_UPPER_BASE, 'test',
                                               WORKDIR + '/node1/mysql.sock',
                                               WORKDIR + '/node2/mysql.sock')
        utility_cmd.check_testcase(result, "Checksum run for DB: test")
        result = utility_cmd.check_table_count(PXC_UPPER_BASE, 'db_galera',
                                               WORKDIR + '/node1/mysql.sock',
                                               WORKDIR + '/node2/mysql.sock')
        utility_cmd.check_testcase(result, "Checksum run for DB: db_galera")
        result = utility_cmd.check_table_count(PXC_UPPER_BASE, 'db_transactions',
                                               WORKDIR + '/node1/mysql.sock',
                                               WORKDIR + '/node2/mysql.sock')
        utility_cmd.check_testcase(result, "Checksum run for DB: db_transactions")
        result = utility_cmd.check_table_count(PXC_UPPER_BASE, 'db_partitioning',
                                               WORKDIR + '/node1/mysql.sock',
                                               WORKDIR + '/node2/mysql.sock')
        utility_cmd.check_testcase(result, "Checksum run for DB: db_partitioning")

        utility_cmd.stop_pxc(WORKDIR, PXC_UPPER_BASE, NODE)
        utility_cmd.stop_ps(WORKDIR, PXC_LOWER_BASE, 1)


query = PXC_LOWER_BASE + "/bin/mysqld --version 2>&1 | grep -oe '[0-9]\.[0-9][\.0-9]*' | head -n1"
lower_version = os.popen(query).read().rstrip()
query = PXC_UPPER_BASE + "/bin/mysqld --version 2>&1 | grep -oe '[0-9]\.[0-9][\.0-9]*' | head -n1"
upper_version = os.popen(query).read().rstrip()
version = utility_cmd.version_check(PXC_UPPER_BASE)
print('------------------------------------------------------------------------------------')
print("\nPXC Asyc non-gtid replication upgrade test : Upgrading from PXC-" + lower_version +
      " to PXC-" + upper_version)
print('------------------------------------------------------------------------------------')
upgrade_qa = PXCUpgrade()
upgrade_qa.startup('replication.cnf')
upgrade_qa.start_ps('1', 'replication.cnf')
utility_cmd.invoke_replication(PXC_LOWER_BASE, '/tmp/psnode1.sock',
                               WORKDIR + '/node3/mysql.sock', 'NONGTID', 'none')
utility_cmd.replication_io_status(PXC_LOWER_BASE, WORKDIR + '/node3/mysql.sock', 'PXC slave', 'none')
utility_cmd.replication_sql_status(PXC_LOWER_BASE, WORKDIR + '/node3/mysql.sock', 'PXC slave', 'none')
rqg_dataload = rqg_datagen.RQGDataGen(PXC_LOWER_BASE, WORKDIR, USER, debug)
rqg_dataload.pxc_dataload(WORKDIR + '/node1/mysql.sock')
upgrade_qa.rolling_upgrade('none')

print('------------------------------------------------------------------------------------')
print("\nPXC Asyc gtid replication upgrade test : Upgrading from PXC-" + lower_version +
      " to PXC-" + upper_version)
print('------------------------------------------------------------------------------------')
upgrade_qa.startup('gtid_replication.cnf')
upgrade_qa.start_ps('1', 'gtid_replication.cnf')
utility_cmd.invoke_replication(PXC_LOWER_BASE, '/tmp/psnode1.sock',
                               WORKDIR + '/node3/mysql.sock', 'GTID', 'none')
utility_cmd.replication_io_status(PXC_LOWER_BASE, WORKDIR + '/node3/mysql.sock', 'PXC slave', 'none')
utility_cmd.replication_sql_status(PXC_LOWER_BASE, WORKDIR + '/node3/mysql.sock', 'PXC slave', 'none')
rqg_dataload = rqg_datagen.RQGDataGen(PXC_LOWER_BASE, WORKDIR, USER, debug)
rqg_dataload.pxc_dataload(WORKDIR + '/node1/mysql.sock')
upgrade_qa.rolling_upgrade('none')
utility_cmd.stop_pxc(WORKDIR, BASEDIR, NODE)
utility_cmd.stop_ps(WORKDIR, BASEDIR, 1)
