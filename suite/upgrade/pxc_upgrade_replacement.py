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
    def startup(self, wsrep_extra=None):
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
        # Check wsrep sync status
        query_cluster_status = GALERA_LOWER_BASE + '/bin/mysql --user=root --socket=' + \
            WORKDIR + '/node' + str(cluster_node) + \
            '/mysql.sock -Bse"show status like \'wsrep_local_state_comment\';"' \
            ' 2>/dev/null | awk \'{print $2}\''
        # Get ping status
        ping_query = GALERA_LOWER_BASE + '/bin/mysqladmin --user=root --socket=' + \
            WORKDIR + '/node' + str(cluster_node) + \
            '/mysql.sock ping > /dev/null 2>&1'
        # check server live status - Timeout 300 sec
        for startup_timer in range(300):
            time.sleep(1)
            ping_check = subprocess.call(ping_query, shell=True, stderr=subprocess.DEVNULL)
            ping_status = ("{}".format(ping_check))
            if int(ping_status) == 0:
                wsrep_status = ""
                while wsrep_status != "Synced":
                    status_query = BASEDIR + '/bin/mysql --user=root --socket=' + \
                        WORKDIR + '/node' + str(cluster_node) + \
                        '/mysql.sock -Bse"show status like ' \
                        "'wsrep_local_state_comment'\"  2>&1 | awk \'{print $2}\'"
                    wsrep_status = os.popen(status_query).read().rstrip()
                utility_cmd.check_testcase(int(ping_status), "Node startup is successful"
                                           "(Node status:" + wsrep_status + ")")
                break  # break the loop if mysqld is running
            if startup_timer > 298:
                utility_cmd.check_testcase(0, "ERROR! Node is not synced with cluster. "
                                              "Check the error log to get more info")
                exit(1)

    def start_upper_version(self):
        # Start Galera cluster for upgrade test
        # Copy node3.cnf to node4.cnf
        shutil.copy(WORKDIR + '/conf/node3.cnf',
                    WORKDIR + '/conf/node4.cnf')
        # get cluster address
        query = GALERA_LOWER_BASE + '/bin/mysql --user=root --socket=' + WORKDIR + \
            '/node3/mysql.sock -Bse"show variables like \'wsrep_cluster_address\';"' \
            ' 2>/dev/null | awk \'{print $2}\''
        wsrep_cluster_addr = os.popen(query).read().rstrip()
        # get node3 port
        query = GALERA_LOWER_BASE + "/bin/mysql --user=root --socket=" + \
            WORKDIR + '/node3/mysql.sock -Bse"select @@port" 2>&1'
        port_no = os.popen(query).read().rstrip()
        wsrep_port_no = int(port_no) + 108      # node4 cluster connection port
        port_no = int(port_no) + 100            # node4 port
        # Update node4.cnf for startup
        os.system("sed -i 's#node3#node4#g' " + WORKDIR + '/conf/node4.cnf')
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
        # Create startup script for node4
        create_startup = 'sed  "s#' + GALERA_LOWER_BASE + '#' + GALERA_UPPER_BASE + \
                         '#g" ' + WORKDIR + '/log/startup3.sh > ' + \
                         WORKDIR + '/log/startup4.sh'
        if debug == 'YES':
            print(create_startup)
        os.system(create_startup)
        os.system("sed -i 's#node3#node4#g' " + WORKDIR + '/log/startup4.sh')
        os.system("rm -rf " + WORKDIR + '/node4')
        os.mkdir(WORKDIR + '/node4')
        # start node4
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
        # Sanity check for sysbench run
        result = sysbench_node1.sanity_check(db)
        utility_cmd.check_testcase(result, "Sysbench run sanity check")
        # Sysbench dataload
        result = sysbench_node1.sysbench_load(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS, SYSBENCH_NORMAL_TABLE_SIZE)
        utility_cmd.check_testcase(result, "Sysbench data load")
        sysbench_node2 = sysbench_run.SysbenchRun(GALERA_LOWER_BASE, WORKDIR,
                                                  WORKDIR + '/node2/mysql.sock', debug)
        sysbench_node3 = sysbench_run.SysbenchRun(GALERA_LOWER_BASE, WORKDIR,
                                                  WORKDIR + '/node3/mysql.sock', debug)
        # sysbench read/write run
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
        # sysbench readonly run
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

    def rolling_replacement(self):
        # Start Galera cluster for rolling replacement test
        for i in range(1, int(NODE) + 1):
            shutil.copy(WORKDIR + '/conf/node' + str(int(i + 2)) + '.cnf',
                        WORKDIR + '/conf/node' + str(int(i + 3)) + '.cnf')
            query = GALERA_LOWER_BASE + '/bin/mysql --user=root --socket=' + WORKDIR + \
                '/node' + str(int(i + 2)) + '/mysql.sock -Bse"show variables like \'wsrep_cluster_address\';"' \
                ' 2>/dev/null | awk \'{print $2}\''
            wsrep_cluster_addr = os.popen(query).read().rstrip()
            query = GALERA_LOWER_BASE + "/bin/mysql --user=root --socket=" + \
                WORKDIR + '/node' + str(int(i + 2)) + '/mysql.sock -Bse"select @@port" 2>&1'
            port_no = os.popen(query).read().rstrip()
            wsrep_port_no = int(port_no) + 108
            port_no = int(port_no) + 100
            os.system("sed -i 's#node" + str(int(i + 2)) +
                      "#node" + str(int(i + 3)) + "#g' " +
                      WORKDIR + '/conf/node' + str(int(i + 3)) + '.cnf')
            os.system("sed -i '/wsrep_sst_auth=root:/d' " +
                      WORKDIR + '/conf/node' + str(int(i + 3)) + '.cnf')
            os.system("sed -i  '0,/^[ \\t]*wsrep_cluster_address[ \\t]*=.*$/s|"
                      "^[ \\t]*wsrep_cluster_address[ \\t]*=.*$|wsrep_cluster_address="
                      + wsrep_cluster_addr + "127.0.0.1:" + str(wsrep_port_no) + "|' "
                      + WORKDIR + '/conf/node' + str(int(i + 3)) + '.cnf')
            os.system("sed -i  '0,/^[ \\t]*port[ \\t]*=.*$/s|"
                      "^[ \\t]*port[ \\t]*=.*$|port="
                      + str(port_no) + "|' " + WORKDIR + '/conf/node' + str(int(i + 3)) + '.cnf')
            os.system('sed -i  "0,/^[ \\t]*wsrep_provider_options[ \\t]*=.*$/s|'
                      "^[ \\t]*wsrep_provider_options[ \\t]*=.*$|wsrep_provider_options="
                      "'gmcast.listen_addr=tcp://127.0.0.1:" + str(wsrep_port_no) +
                      "'|\" " + WORKDIR + '/conf/node' + str(int(i + 3)) + '.cnf')
            os.system("sed -i  '0,/^[ \\t]*server_id[ \\t]*=.*$/s|"
                      "^[ \\t]*server_id[ \\t]*=.*$|server_id="
                      "14|' " + WORKDIR + '/conf/node' + str(int(i + 3)) + '.cnf')

            create_startup = 'sed  "s#' + GALERA_LOWER_BASE + '#' + GALERA_UPPER_BASE + \
                '#g" ' + WORKDIR + '/log/startup' + str(int(i + 2)) + '.sh > ' + \
                WORKDIR + '/log/startup' + str(int(i + 3)) + '.sh'
            if debug == 'YES':
                print(create_startup)
            os.system(create_startup)
            os.system("sed -i 's#node" + str(int(i + 2)) +
                      "#node" + str(int(i + 3)) + "#g' " + WORKDIR +
                      '/log/startup' + str(int(i + 3)) + '.sh')
            os.system("rm -rf " + WORKDIR + '/node' + str(int(i + 3)))
            os.mkdir(WORKDIR + '/node' + str(int(i + 3)))
            upgrade_startup = "bash " + WORKDIR + \
                '/log/startup' + str(int(i + 3)) + '.sh'

            status_query = BASEDIR + '/bin/mysql --user=root --socket=' + \
                WORKDIR + '/node1/mysql.sock -Bse"show status like ' \
                "'wsrep_local_state_comment'\"  2>&1 | awk \'{print $2}\'"
            wsrep_status = os.popen(status_query).read().rstrip()
            print(wsrep_status)
            status_query = BASEDIR + '/bin/mysql --user=root --socket=' + \
                           WORKDIR + '/node2/mysql.sock -Bse"show status like ' \
                                     "'wsrep_local_state_comment'\"  2>&1 | awk \'{print $2}\'"
            wsrep_status = os.popen(status_query).read().rstrip()
            print(wsrep_status)
            status_query = BASEDIR + '/bin/mysql --user=root --socket=' + \
                           WORKDIR + '/node3/mysql.sock -Bse"show status like ' \
                                     "'wsrep_local_state_comment'\"  2>&1 | awk \'{print $2}\'"
            wsrep_status = os.popen(status_query).read().rstrip()
            print(wsrep_status)
            time.sleep(10)
            if debug == 'YES':
                print(upgrade_startup)
            result = os.system(upgrade_startup)
            utility_cmd.check_testcase(result, "Starting Galera cluster node" +
                                       str(int(i + 3)) + " for upgrade testing")
            self.startup_check(int(i + 3))

            upgrade_cmd = GALERA_UPPER_BASE + '/bin/mysql_upgrade -uroot --socket=' + \
                WORKDIR + '/node' + str(int(i + 3)) + \
                '/mysql.sock --skip-write-binlog > ' + WORKDIR + '/log/node' + str(int(i + 3)) + '_upgrade.log 2>&1'
            if debug == 'YES':
                print(upgrade_cmd)
            result = os.system(upgrade_cmd)
            utility_cmd.check_testcase(result, "Cluster node" + str(int(i + 3)) + " upgrade is successful")


query = GALERA_LOWER_BASE + "/bin/mysqld --version 2>&1 | grep -oE '([0-9]+).([0-9]+).([0-9]+)' | head -n1"
lower_version = os.popen(query).read().rstrip()
query = GALERA_UPPER_BASE + "/bin/mysqld --version 2>&1 | grep -oE '([0-9]+).([0-9]+).([0-9]+)' | head -n1"
upper_version = os.popen(query).read().rstrip()
version = utility_cmd.version_check(GALERA_UPPER_BASE)
print('--------------------------------------------------------------------------------------------')
print("\nGalera Upgrade test : Upgrading from PXC-" + lower_version + " to PXC-" + upper_version)
print('--------------------------------------------------------------------------------------------')
print(datetime.now().strftime("%H:%M:%S ") + " Rolling replacement upgrade without active workload")
print('--------------------------------------------------------------------------------------------')
upgrade_qa = PXCUpgrade()
upgrade_qa.startup()
rqg_dataload = rqg_datagen.RQGDataGen(GALERA_LOWER_BASE, WORKDIR, USER, debug)
rqg_dataload.galera_dataload(WORKDIR + '/node1/mysql.sock')
upgrade_qa.rolling_replacement()
utility_cmd.stop_galera(WORKDIR, BASEDIR, NODE)
