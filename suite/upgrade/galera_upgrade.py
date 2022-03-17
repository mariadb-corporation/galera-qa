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
from util import galera_startup
from util import db_connection
from util import sysbench_run
from util import utility
from util import rqg_datagen

# Read argument
parser = argparse.ArgumentParser(prog='Galera upgrade test', usage='%(prog)s [options]')
parser.add_argument('-e', '--encryption-run', action='store_true',
                    help='This option will enable encryption options')
parser.add_argument('-r', '--rr', action='store_true',
                    help='This option will enable rr tracing')
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
if args.rr is True:
    rr = 'YES'
else:
    rr = 'NO'

utility_cmd = utility.Utility(debug)
utility_cmd.check_python_version()


class GALERAUpgrade:
    def startup(self, sst_opt, wsrep_extra=None):
        # Start Galera cluster for upgrade test
        dbconnection_check = db_connection.DbConnection(USER, WORKDIR + '/node1/mysql.sock')
        server_startup = galera_startup.StartCluster(parent_dir, WORKDIR, GALERA_LOWER_BASE, int(NODE), debug)
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
                result = server_startup.create_config(sst_opt, 'gcache.keep_pages_size=5;'
                                                      'gcache.page_size=1024M;gcache.size=1024M;')
            else:
                result = server_startup.create_config(sst_opt)
            utility_cmd.check_testcase(result, "Configuration file creation")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "Initializing cluster")
        if rr == 'YES':
            result = server_startup.start_cluster(rr)
        else:
            result = server_startup.start_cluster()
        utility_cmd.check_testcase(result, "Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "Database connection")

    def startup_check(self, cluster_node):
        """ This method will check the node
            startup status.
        """
        ping_query = GALERA_LOWER_BASE + '/bin/mysqladmin --user=root --socket=' + \
            WORKDIR + '/node' + str(cluster_node) + \
            '/mysql.sock ping > /dev/null 2>&1'
        for startup_timer in range(300):
            time.sleep(1)
            ping_check = subprocess.call(ping_query, shell=True, stderr=subprocess.DEVNULL)
            ping_status = ("{}".format(ping_check))
            if int(ping_status) == 0:
                version = utility_cmd.version_check(GALERA_UPPER_BASE)
                if int(version) > int("080000"):
                    wsrep_status = ""
                    while wsrep_status != "Synced":
                        status_query = BASEDIR + '/bin/mysql --user=root --socket=' + \
                            WORKDIR + '/node' + str(cluster_node) + \
                            '/mysql.sock -Bse"show status like ' \
                            "'wsrep_local_state_comment'\"  2>&1 | awk \'{print $2}\'"
                        wsrep_status = os.popen(status_query).read().rstrip()
                    utility_cmd.check_testcase(int(ping_status), "Node startup is successful"
                                                                 "(Node status:" + wsrep_status + ")")
                time.sleep(10)
                break  # break the loop if mysqld is running
            if startup_timer > 298:
                utility_cmd.check_testcase(1, "STARTUP TIMEOUT ERROR! Node is not synced with cluster. "
                                              "Check the error log to get more info")
                exit(1)

    def start_upper_version(self):
        # Start Galera cluster for upgrade test
        shutil.copy(WORKDIR + '/conf/node3.cnf',
                    WORKDIR + '/conf/node4.cnf')
        query = GALERA_LOWER_BASE + '/bin/mysql --user=root --socket=' + WORKDIR + \
            '/node3/mysql.sock -Bse"show variables like \'wsrep_cluster_address\';"' \
            ' 2>/dev/null | awk \'{print $2}\''
        wsrep_cluster_addr = os.popen(query).read().rstrip()
        query = GALERA_LOWER_BASE + "/bin/mysql --user=root --socket=" + \
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
        create_startup = 'sed  "s#' + GALERA_LOWER_BASE + '#' + GALERA_UPPER_BASE + \
                         '#g" ' + WORKDIR + '/log/startup3.sh > ' + \
                         WORKDIR + '/log/startup4.sh'
        if debug == 'YES':
            print(create_startup)
        os.system(create_startup)
        os.system("sed -i 's#node3#node4#g' " + WORKDIR + '/log/startup4.sh')
        os.system("rm -rf " + WORKDIR + '/node4')
        os.mkdir(WORKDIR + '/node4')
        upgrade_startup = "bash " + WORKDIR + \
                          '/log/startup4.sh'
        if debug == 'YES':
            print(upgrade_startup)
        result = os.system(upgrade_startup)
        utility_cmd.check_testcase(result, "Starting Galera cluster node4 for upgrade testing")
        self.startup_check(4)
        upgrade_cmd = GALERA_UPPER_BASE + '/bin/mysql_upgrade -uroot --socket=' + \
            WORKDIR + '/node4/mysql.sock --skip-write-binlog > ' + \
            WORKDIR + '/log/node4_upgrade.log 2>&1'
        if debug == 'YES':
            print(upgrade_cmd)
        result = os.system(upgrade_cmd)
        utility_cmd.check_testcase(result, "Cluster node4 upgrade is successful")

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
            MariaDB Galera Cluster to
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
            if i == 3:
                if upgrade_type == 'readwrite_sst':
                    sysbench_node1 = sysbench_run.SysbenchRun(GALERA_LOWER_BASE, WORKDIR, WORKDIR +
                                                              '/node1/mysql.sock', debug)
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

            os.system("sed -i '/basedir =/d' " + WORKDIR + '/conf/node' + str(i) + '.cnf')
            os.system("sed -i '/wsrep-provider =/d' " + WORKDIR + '/conf/node' + str(i) + '.cnf')
            startup_cmd = GALERA_UPPER_BASE + '/bin/mysqld --defaults-file=' + \
                WORKDIR + '/conf/node' + str(i) + '.cnf --wsrep-provider=' + \
                GALERA_UPPER_BASE + '/lib/libgalera_smm.so --datadir=' + \
                WORKDIR + '/node' + str(i) + ' --basedir=' + GALERA_UPPER_BASE + ' >> ' + \
                WORKDIR + '/node' + str(i) + '/node' + str(i) + '.err 2>&1 &'
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
            print(result)
            utility_cmd.check_testcase(result, "Cluster node" + str(i) + " upgrade is successful")

        time.sleep(10)
        sysbench_node = sysbench_run.SysbenchRun(GALERA_LOWER_BASE, WORKDIR,
                                                  WORKDIR + '/node1/mysql.sock', debug)
        result = sysbench_node.sysbench_oltp_read_write('test', SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS,
                                                SYSBENCH_NORMAL_TABLE_SIZE, 100)
        utility_cmd.check_testcase(result, "Sysbench oltp run after upgrade")
        time.sleep(5)

        result = utility_cmd.check_table_count(GALERA_UPPER_BASE, 'test',
                                               WORKDIR + '/node1/mysql.sock',
                                               WORKDIR + '/node2/mysql.sock')
        utility_cmd.check_testcase(result, "Checksum run for DB: test")
        result = utility_cmd.check_table_count(GALERA_UPPER_BASE, 'db_galera',
                                               WORKDIR + '/node1/mysql.sock',
                                               WORKDIR + '/node2/mysql.sock')
        utility_cmd.check_testcase(result, "Checksum run for DB: db_galera")
        result = utility_cmd.check_table_count(GALERA_UPPER_BASE, 'db_mariadb',
                                               WORKDIR + '/node1/mysql.sock',
                                               WORKDIR + '/node2/mysql.sock')
        utility_cmd.check_testcase(result, "Checksum run for DB: db_mariadb")
        result = utility_cmd.check_table_count(GALERA_UPPER_BASE, 'db_runtime',
                                               WORKDIR + '/node1/mysql.sock',
                                               WORKDIR + '/node2/mysql.sock')
        utility_cmd.check_testcase(result, "Checksum run for DB: db_runtime")
        result = utility_cmd.check_table_count(GALERA_UPPER_BASE, 'db_optimizer',
                                               WORKDIR + '/node1/mysql.sock',
                                               WORKDIR + '/node2/mysql.sock')
        utility_cmd.check_testcase(result, "Checksum run for DB: db_optimizer")
        result = utility_cmd.check_table_count(GALERA_UPPER_BASE, 'db_temporal',
                                               WORKDIR + '/node1/mysql.sock',
                                               WORKDIR + '/node2/mysql.sock')
        utility_cmd.check_testcase(result, "Checksum run for DB: db_temporal")
        utility_cmd.stop_galera(WORKDIR, GALERA_UPPER_BASE, NODE)


query = GALERA_LOWER_BASE + "/bin/mysqld --version 2>&1 | grep -oE '([0-9]+).([0-9]+).([0-9]+)' | tail -1"
lower_version = os.popen(query).read().rstrip()
query = GALERA_UPPER_BASE + "/bin/mysqld --version 2>&1 | grep -oE '([0-9]+).([0-9]+).([0-9]+)' | tail -1"
upper_version = os.popen(query).read().rstrip()
version = utility_cmd.version_check(GALERA_UPPER_BASE)
upgrade_qa = GALERAUpgrade()
print('--------------------------------------------------------------------------------------------------')
print("\nGalera Upgrade test : Upgrading from GALERA-" + lower_version + " to GALERA-" + upper_version)
print('--------------------------------------------------------------------------------------------------')
sst_opts = ["none"]
'''
for i in sst_opts:
    print('--------------------------------------------------------------------------------------------------')
    print(datetime.now().strftime("%H:%M:%S ") + " Rolling upgrade without active workload (SST encryption : "
          + i + ")")
    print('--------------------------------------------------------------------------------------------------')
    upgrade_qa.startup(i)
    rqg_dataload = rqg_datagen.RQGDataGen(GALERA_LOWER_BASE, WORKDIR, USER, debug)
    rqg_dataload.galera_dataload(WORKDIR + '/node1/mysql.sock')
    upgrade_qa.rolling_upgrade('none')

for i in sst_opts:
    print('------------------------------------------------------------------------------------')
    print(datetime.now().strftime("%H:%M:%S ") + " Rolling upgrade with active readonly workload (SST encryption : "
          + i + ")")
    print('------------------------------------------------------------------------------------')
    upgrade_qa.startup(i)
    rqg_dataload = rqg_datagen.RQGDataGen(GALERA_LOWER_BASE, WORKDIR, USER, debug)
    rqg_dataload.galera_dataload(WORKDIR + '/node1/mysql.sock')
    upgrade_qa.rolling_upgrade('readonly')
'''
for i in sst_opts:
    print('------------------------------------------------------------------------------------')
    print(datetime.now().strftime("%H:%M:%S ") + " Rolling upgrade with active read/write workload"
                                                 "(enforcing SST on node-join) (SST encryption : " + i + ")")
    print('------------------------------------------------------------------------------------')
    upgrade_qa.startup(i)
#    rqg_dataload = rqg_datagen.RQGDataGen(GALERA_LOWER_BASE, WORKDIR, USER, debug)
#    rqg_dataload.galera_dataload(WORKDIR + '/node1/mysql.sock')
    upgrade_qa.rolling_upgrade('readwrite_sst')
'''
for i in sst_opts:
    print('------------------------------------------------------------------------------------')
    print(datetime.now().strftime("%H:%M:%S ") + " Rolling upgrade with active read/write workload"
                                                 "(enforcing IST on node-join) (SST encryption : " + i + ")")
    print('------------------------------------------------------------------------------------')
    upgrade_qa.startup('wsrep_extra')
    rqg_dataload = rqg_datagen.RQGDataGen(GALERA_LOWER_BASE, WORKDIR, USER, debug)
    rqg_dataload.galera_dataload(WORKDIR + '/node1/mysql.sock')
    upgrade_qa.rolling_upgrade('readwrite')

if int(version) > int("080000"):
    for i in sst_opts:
        print('------------------------------------------------------------------------------------')
        print(datetime.now().strftime("%H:%M:%S ") + "Mix of GALERA-" +
              lower_version + " and GALERA-" + upper_version + "(without active workload) (SST encryption : " + i + ")")
        print('------------------------------------------------------------------------------------')
        upgrade_qa = GALERAUpgrade()
        upgrade_qa.startup(i)
        upgrade_qa.start_upper_version()
        print('------------------------------------------------------------------------------------')
        print(datetime.now().strftime("%H:%M:%S ") + "Mix of GALERA-" +
              lower_version + " and GALERA-" + upper_version + "(with active read/write workload) (SST encryption : "
              + i + ")")
        print('------------------------------------------------------------------------------------')
        upgrade_qa.startup(i, 'wsrep_extra')
        rqg_dataload = rqg_datagen.RQGDataGen(GALERA_LOWER_BASE, WORKDIR, USER, debug)
        rqg_dataload.galera_dataload(WORKDIR + '/node1/mysql.sock')
        upgrade_qa.sysbench_run(WORKDIR + '/node1/mysql.sock', 'test', 'readwrite')
        upgrade_qa.start_upper_version()
'''
