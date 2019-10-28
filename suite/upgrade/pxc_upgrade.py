#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
import time
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from config import *
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


class PXCUpgrade:
    def startup(self):
        # Start PXC cluster for upgrade test
        dbconnection_check = db_connection.DbConnection(USER, WORKDIR + '/node1/mysql.sock')
        server_startup = pxc_startup.StartCluster(parent_dir, WORKDIR, PXC_LOWER_BASE, int(NODE))
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "Startup sanity check")
        if encryption == 'YES':
            result = utility_cmd.create_ssl_certificate(WORKDIR)
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

    def sysbench_run(self, node1_socket, db):
        # Sysbench dataload for consistency test
        sysbench = sysbench_run.SysbenchRun(PXC_LOWER_BASE, WORKDIR,
                                            node1_socket)

        result = sysbench.sanity_check(db)
        utility_cmd.check_testcase(result, "Sysbench run sanity check")
        result = sysbench.sysbench_load(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS, SYSBENCH_NORMAL_TABLE_SIZE)
        utility_cmd.check_testcase(result, "Sysbench data load")
        version = utility_cmd.version_check(PXC_LOWER_BASE)
        if int(version) > int("050700"):
            if encryption == 'YES':
                for i in range(1, SYSBENCH_TABLE_COUNT + 1):
                    encrypt_table = PXC_LOWER_BASE + '/bin/mysql --user=root ' \
                        '--socket=' + WORKDIR + '/node1/mysql.sock -e "' \
                        ' alter table ' + db + '.sbtest' + str(i) + \
                        " encryption='Y'" \
                        '"; > /dev/null 2>&1'
                    os.system(encrypt_table)

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

    def upgrade(self):
        """ This function will upgrade
            Percona XtraDB Cluster to
            latest version and perform
            table checksum.
        """
        self.sysbench_run(WORKDIR + '/node1/mysql.sock', 'test')
        for i in range(int(NODE), 0, -1):
            shutdown_node = PXC_LOWER_BASE + '/bin/mysqladmin --user=root --socket=' + \
                WORKDIR + '/node' + str(i) + \
                '/mysql.sock shutdown > /dev/null 2>&1'
            result = os.system(shutdown_node)
            utility_cmd.check_testcase(result, "Shutdown cluster node" + str(i) + " for upgrade testing")
            version = utility_cmd.version_check(PXC_UPPER_BASE)
            if int(version) > int("080000"):
                os.system("sed -i '/wsrep_sst_auth=root:/d' " + WORKDIR + '/conf/node' + str(i) + '.cnf')
            startup_cmd = PXC_UPPER_BASE + '/bin/mysqld --defaults-file=' + \
                WORKDIR + '/conf/node' + str(i) + '.cnf --datadir=' + \
                WORKDIR + '/node' + str(i) + ' --basedir=' + PXC_UPPER_BASE + \
                ' --wsrep-provider=none --log-error=' + \
                WORKDIR + '/log/node' + str(i) + '.err > ' + \
                WORKDIR + '/log/node' + str(i) + '.err 2>&1 &'
            os.system(startup_cmd)
            self.startup_check(i)
            upgrade_cmd = PXC_UPPER_BASE + '/bin/mysql_upgrade -uroot --socket=' + \
                WORKDIR + '/node' + str(i) + \
                '/mysql.sock > ' + WORKDIR + '/log/node' + str(i) + '_upgrade.log 2>&1'
            result = os.system(upgrade_cmd)
            utility_cmd.check_testcase(result, "Cluster node" + str(i) + " upgrade is successful")
            shutdown_node = PXC_UPPER_BASE + '/bin/mysqladmin --user=root --socket=' + \
                WORKDIR + '/node' + str(i) + \
                '/mysql.sock shutdown > /dev/null 2>&1'
            result = os.system(shutdown_node)
            utility_cmd.check_testcase(result, "Shutdown cluster node" + str(i) + " after upgrade run")
            create_startup = 'sed  "s#' + PXC_LOWER_BASE + '#' + PXC_UPPER_BASE + \
                '#g" ' + WORKDIR + '/log/startup' + str(i) + '.sh > ' + \
                WORKDIR + '/log/upgrade_startup' + str(i) + '.sh'
            os.system(create_startup)
            if i == 1:
                remove_bootstrap_option = 'sed -i "s#--wsrep-new-cluster##g" ' + \
                    WORKDIR + '/log/upgrade_startup' + str(i) + '.sh'
                os.system(remove_bootstrap_option)
            time.sleep(5)
            upgrade_startup = "bash " + WORKDIR + \
                              '/log/upgrade_startup' + str(i) + '.sh'
            result = os.system(upgrade_startup)
            utility_cmd.check_testcase(result, "Starting cluster node" + str(i) + " after upgrade run")
            self.startup_check(i)


query = PXC_LOWER_BASE + "/bin/mysqld --version 2>&1 | grep -oe '[0-9]\.[0-9][\.0-9]*' | head -n1"
lower_version = os.popen(query).read().rstrip()
query = PXC_UPPER_BASE + "/bin/mysqld --version 2>&1 | grep -oe '[0-9]\.[0-9][\.0-9]*' | head -n1"
upper_version = os.popen(query).read().rstrip()
print("\nPXC Upgrade test : Upgrading from PXC-" + lower_version + " to PXC-" + upper_version)
print("------------------------------------------------------------------------------")
upgrade_qa = PXCUpgrade()
upgrade_qa.startup()
rqg_dataload = rqg_datagen.RQGDataGen(PXC_LOWER_BASE, WORKDIR, USER)
rqg_dataload.pxc_dataload(WORKDIR + '/node1/mysql.sock')
upgrade_qa.upgrade()

version = utility_cmd.version_check(PXC_UPPER_BASE)
if int(version) < int("080000"):
    checksum = table_checksum.TableChecksum(PT_BASEDIR, PXC_UPPER_BASE, WORKDIR, NODE,
                                            WORKDIR + '/node1/mysql.sock')
    checksum.sanity_check()
    checksum.data_consistency('test,db_galera,db_transactions,db_partitioning')
else:
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
