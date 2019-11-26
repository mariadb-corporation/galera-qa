#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
import time
import shutil
from datetime import datetime
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
parser = argparse.ArgumentParser(prog='PXC upgrade test', usage='%(prog)s [options]')
parser.add_argument('-e', '--encryption-run', action='store_true',
                    help='This option will enable encryption options')
args = parser.parse_args()
if args.encryption_run is True:
    encryption = 'YES'
else:
    encryption = 'NO'


class PXCUpgrade:
    def startup(self, wsrep_extra=None):
        # Start PXC cluster for upgrade test
        dbconnection_check = db_connection.DbConnection(USER, WORKDIR + '/node1/mysql.sock')
        server_startup = pxc_startup.StartCluster(parent_dir, WORKDIR, PXC_LOWER_BASE, int(NODE))
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "Startup sanity check")
        if encryption == 'YES':
            if wsrep_extra is not None:
                result = server_startup.create_config('encryption',
                                                      'gcache.keep_pages_size=5;'
                                                      'gcache.page_size=1024M;gcache.size=1024M;')
            else:
                result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "Configuration file creation")
        else:
            if wsrep_extra is not None:
                result = server_startup.create_config('none', 'gcache.keep_pages_size=5;'
                                                      'gcache.page_size=1024M;gcache.size=1024M;')
            else:
                result = server_startup.create_config('none')
            utility_cmd.check_testcase(result, "Configuration file creation")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "Initializing cluster")
        result = server_startup.start_cluster()
        utility_cmd.check_testcase(result, "Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "Database connection")

    def startup_check(self, cluster_node):
        """ This method will check the node
            startup status.
        """
        query_cluster_status = PXC_LOWER_BASE + '/bin/mysql --user=root --socket=' + \
            WORKDIR + '/node' + str(cluster_node) + \
            '/mysql.sock -Bse"show status like \'wsrep_local_state_comment\';"' \
            ' 2>/dev/null | awk \'{print $2}\''
        ping_query = PXC_LOWER_BASE + '/bin/mysqladmin --user=root --socket=' + \
            WORKDIR + '/node' + str(cluster_node) + \
            '/mysql.sock ping > /dev/null 2>&1'
        for startup_timer in range(300):
            time.sleep(1)
            cluster_status = os.popen(query_cluster_status).read().rstrip()
            if cluster_status == 'Synced':
                utility_cmd.check_testcase(0, "Node startup is successful")
                break
            if startup_timer > 298:
                utility_cmd.check_testcase(0, "Warning! Node is not synced with cluster. "
                                              "Check the error log to get more info")
                ping_check = subprocess.call(ping_query, shell=True, stderr=subprocess.DEVNULL)
                ping_status = ("{}".format(ping_check))
                if int(ping_status) == 0:
                    utility_cmd.check_testcase(int(ping_status), "Node startup is successful "
                                                                 "(Node status:" + cluster_status + ")")
                    break  # break the loop if mysqld is running

    def start_upper_version(self):
        # Start PXC cluster for upgrade test
        shutil.copy(WORKDIR + '/conf/node3.cnf',
                    WORKDIR + '/conf/node4.cnf')
        query = PXC_LOWER_BASE + '/bin/mysql --user=root --socket=' + WORKDIR + \
            '/node3/mysql.sock -Bse"show variables like \'wsrep_cluster_address\';"' \
            ' 2>/dev/null | awk \'{print $2}\''
        wsrep_cluster_addr = os.popen(query).read().rstrip()
        query = PXC_LOWER_BASE + "/bin/mysql --user=root --socket=" + \
                WORKDIR + '/node3/mysql.sock -Bse"select @@port" 2>&1'
        port_no = os.popen(query).read().rstrip()
        wsrep_port_no = int(port_no) + 108
        port_no = int(port_no) + 100
        os.system("sed -i 's#node3#node4#g' " + WORKDIR + '/conf/node4.cnf')
        os.system("sed -i '/wsrep_sst_auth=root:/d' " + WORKDIR + '/conf/node4.cnf')
        os.system("sed -i  '0,/^[ \\t]*wsrep_cluster_address[ \\t]*=.*$/s|" 
                  "^[ \\t]*wsrep_cluster_address[ \\t]*=.*$|wsrep_cluster_address="
                  + wsrep_cluster_addr + "127.0.0.1:" + str(wsrep_port_no) + "|' "
                  + WORKDIR + '/conf/node4.cnf')
        os.system("sed -i  '0,/^[ \\t]*port[ \\t]*=.*$/s|"
                  "^[ \\t]*port[ \\t]*=.*$|port="
                  + str(port_no) + "|' " + WORKDIR + '/conf/node4.cnf')
        os.system('sed -i  "0,/^[ \\t]*wsrep_provider_options[ \\t]*=.*$/s|'
                  "^[ \\t]*wsrep_provider_options[ \\t]*=.*$|wsrep_provider_options="
                  "'gmcast.listen_addr=tcp://127.0.0.1:" + str(wsrep_port_no) + "'"
                  '|" ' + WORKDIR + '/conf/node4.cnf')
        os.system("sed -i  '0,/^[ \\t]*server_id[ \\t]*=.*$/s|"
                  "^[ \\t]*server_id[ \\t]*=.*$|server_id="
                  "14|' " + WORKDIR + '/conf/node4.cnf')
        create_startup = 'sed  "s#' + PXC_LOWER_BASE + '#' + PXC_UPPER_BASE + \
                         '#g" ' + WORKDIR + '/log/startup3.sh > ' + \
                         WORKDIR + '/log/startup4.sh'
        os.system(create_startup)
        os.system("sed -i 's#node3#node4#g' " + WORKDIR + '/log/startup4.sh')
        os.system("rm -rf " + WORKDIR + '/node4')
        os.mkdir(WORKDIR + '/node4')
        upgrade_startup = "bash " + WORKDIR + \
                          '/log/startup4.sh'
        result = os.system(upgrade_startup)
        utility_cmd.check_testcase(result, "Starting PXC-8.0 cluster node4 for upgrade testing")
        self.startup_check(4)

    def sysbench_run(self, node1_socket, db, upgrade_type):
        # Sysbench dataload for consistency test
        sysbench_node1 = sysbench_run.SysbenchRun(PXC_LOWER_BASE, WORKDIR,
                                            node1_socket)

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
                    os.system(encrypt_table)
        sysbench_node2 = sysbench_run.SysbenchRun(PXC_LOWER_BASE, WORKDIR,
                                                  WORKDIR + '/node2/mysql.sock')
        sysbench_node3 = sysbench_run.SysbenchRun(PXC_LOWER_BASE, WORKDIR,
                                                  WORKDIR + '/node3/mysql.sock')
        if upgrade_type == 'readwrite' or upgrade_type == 'readwrite_sst':
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

    def rolling_upgrade(self, upgrade_type):
        """ This function will upgrade
            Percona XtraDB Cluster to
            latest version and perform
            table checksum.
        """
        self.sysbench_run(WORKDIR + '/node1/mysql.sock', 'test', upgrade_type)
        time.sleep(5)
        for i in range(int(NODE), 0, -1):
            query = "ps -ef | grep sysbench | grep -v gep | grep node" + \
                                 str(i) + " | awk '{print $2}'"
            sysbench_pid = os.popen(query).read().rstrip()
            kill_sysbench = "kill -9 " + sysbench_pid + " > /dev/null 2>&1"
            os.system(kill_sysbench)
            shutdown_node = PXC_LOWER_BASE + '/bin/mysqladmin --user=root --socket=' + \
                WORKDIR + '/node' + str(i) + \
                '/mysql.sock shutdown > /dev/null 2>&1'
            result = os.system(shutdown_node)
            utility_cmd.check_testcase(result, "Shutdown cluster node" + str(i) + " for upgrade testing")
            if i == 3:
                if upgrade_type == 'readwrite_sst':
                    sysbench_node1 = sysbench_run.SysbenchRun(PXC_LOWER_BASE, WORKDIR, WORKDIR +
                                                              '/node1/mysql.sock')
                    sysbench_node1.sanity_check('test_one')
                    sysbench_node1.sanity_check('test_two')
                    sysbench_node1.sanity_check('test_three')
                    result = sysbench_node1.sysbench_load('test_one', SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS,
                                                          SYSBENCH_LOAD_TEST_TABLE_SIZE)
                    utility_cmd.check_testcase(result, "Sysbench data load(DB: test_one)")
                    result = sysbench_node1.sysbench_load('test_two', SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS,
                                                          SYSBENCH_LOAD_TEST_TABLE_SIZE)
                    utility_cmd.check_testcase(result, "Sysbench data load(DB: test_two)")
                    result = sysbench_node1.sysbench_load('test_three', SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS,
                                                          SYSBENCH_LOAD_TEST_TABLE_SIZE)
                    utility_cmd.check_testcase(result, "Sysbench data load(DB: test_three)")

            version = utility_cmd.version_check(PXC_UPPER_BASE)
            if int(version) > int("080000"):
                os.system("sed -i '/wsrep_sst_auth=root:/d' " + WORKDIR + '/conf/node' + str(i) + '.cnf')
                os.system("sed -i 's#wsrep_slave_threads=8#wsrep_slave_threads=30#g' " + WORKDIR +
                          '/conf/node' + str(i) + '.cnf')
                startup_cmd = PXC_UPPER_BASE + '/bin/mysqld --defaults-file=' + \
                    WORKDIR + '/conf/node' + str(i) + '.cnf --datadir=' + \
                    WORKDIR + '/node' + str(i) + ' --basedir=' + PXC_UPPER_BASE + \
                    ' --wsrep-provider=' + PXC_UPPER_BASE + \
                    '/lib/libgalera_smm.so --log-error=' + \
                    WORKDIR + '/log/upgrade_node' + str(i) + '.err >> ' + \
                    WORKDIR + '/log/upgrade_node' + str(i) + '.err 2>&1 &'
            else:
                startup_cmd = PXC_UPPER_BASE + '/bin/mysqld --defaults-file=' + \
                    WORKDIR + '/conf/node' + str(i) + '.cnf --datadir=' + \
                    WORKDIR + '/node' + str(i) + ' --basedir=' + PXC_UPPER_BASE + \
                    ' --wsrep-provider=none --log-error=' + \
                    WORKDIR + '/log/upgrade_node' + str(i) + '.err >> ' + \
                    WORKDIR + '/log/upgrade_node' + str(i) + '.err 2>&1 &'
            os.system(startup_cmd)
            self.startup_check(i)
            if int(version) < int("080000"):
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
        time.sleep(10)
        sysbench_node = sysbench_run.SysbenchRun(PXC_LOWER_BASE, WORKDIR,
                                                  WORKDIR + '/node1/mysql.sock')
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


query = PXC_LOWER_BASE + "/bin/mysqld --version 2>&1 | grep -oe '[0-9]\.[0-9][\.0-9]*' | head -n1"
lower_version = os.popen(query).read().rstrip()
query = PXC_UPPER_BASE + "/bin/mysqld --version 2>&1 | grep -oe '[0-9]\.[0-9][\.0-9]*' | head -n1"
upper_version = os.popen(query).read().rstrip()
version = utility_cmd.version_check(PXC_UPPER_BASE)
print('------------------------------------------------------------------------------------')
print("\nPXC Upgrade test : Upgrading from PXC-" + lower_version + " to PXC-" + upper_version)
print('------------------------------------------------------------------------------------')
print(datetime.now().strftime("%H:%M:%S ") + " Rolling upgrade without active workload")
print('------------------------------------------------------------------------------------')
upgrade_qa = PXCUpgrade()
upgrade_qa.startup()
rqg_dataload = rqg_datagen.RQGDataGen(PXC_LOWER_BASE, WORKDIR, USER)
rqg_dataload.pxc_dataload(WORKDIR + '/node1/mysql.sock')
upgrade_qa.rolling_upgrade('none')
print('------------------------------------------------------------------------------------')
print(datetime.now().strftime("%H:%M:%S ") + " Rolling upgrade with active readonly workload")
print('------------------------------------------------------------------------------------')
upgrade_qa.startup()
rqg_dataload = rqg_datagen.RQGDataGen(PXC_LOWER_BASE, WORKDIR, USER)
rqg_dataload.pxc_dataload(WORKDIR + '/node1/mysql.sock')
upgrade_qa.rolling_upgrade('readonly')
print('------------------------------------------------------------------------------------')
print(datetime.now().strftime("%H:%M:%S ") + " Rolling upgrade with active read/write workload"
                                             "(enforcing SST on node-join)")
print('------------------------------------------------------------------------------------')
upgrade_qa.startup()
rqg_dataload = rqg_datagen.RQGDataGen(PXC_LOWER_BASE, WORKDIR, USER)
rqg_dataload.pxc_dataload(WORKDIR + '/node1/mysql.sock')
upgrade_qa.rolling_upgrade('readwrite_sst')
print('------------------------------------------------------------------------------------')
print(datetime.now().strftime("%H:%M:%S ") + " Rolling upgrade with active read/write workload"
                                            "(enforcing IST on node-join)")
print('------------------------------------------------------------------------------------')
upgrade_qa.startup('wsrep_extra')
rqg_dataload = rqg_datagen.RQGDataGen(PXC_LOWER_BASE, WORKDIR, USER)
rqg_dataload.pxc_dataload(WORKDIR + '/node1/mysql.sock')
upgrade_qa.rolling_upgrade('readwrite')
if int(version) > int("080000"):
    print('------------------------------------------------------------------------------------')
    print(datetime.now().strftime("%H:%M:%S ") + "Mix of PXC-" +
          lower_version + " and PXC-" + upper_version + "(without active workload)")
    print('------------------------------------------------------------------------------------')
    upgrade_qa = PXCUpgrade()
    upgrade_qa.startup()
    upgrade_qa.start_upper_version()
    print('------------------------------------------------------------------------------------')
    print(datetime.now().strftime("%H:%M:%S ") + "Mix of PXC-" +
          lower_version + " and PXC-" + upper_version + "(with active read/write workload)")
    print('------------------------------------------------------------------------------------')
    upgrade_qa.startup('wsrep_extra')
    rqg_dataload = rqg_datagen.RQGDataGen(PXC_LOWER_BASE, WORKDIR, USER)
    rqg_dataload.pxc_dataload(WORKDIR + '/node1/mysql.sock')
    upgrade_qa.sysbench_run(WORKDIR + '/node1/mysql.sock', 'test', 'readwrite')
    upgrade_qa.start_upper_version()
