#!/usr/bin/env python3
import os
import sys
import argparse
import itertools
import time
import subprocess
from datetime import datetime
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from config import *
from util import sysbench_run
from util import utility
from util import db_connection
from util import pxc_startup
utility_cmd = utility.Utility()
utility_cmd.check_python_version()


# Read argument
parser = argparse.ArgumentParser(prog='PXC WSREP provider random test', usage='%(prog)s [options]')
parser.add_argument('-e', '--encryption-run', action='store_true',
                    help='This option will enable encryption options')
args = parser.parse_args()
if args.encryption_run is True:
    encryption = 'YES'
else:
    encryption = 'NO'


class WSREPProviderRandomTest:
    def startup_check(self, cluster_node):
        """ This method will check the node recovery
            startup status.
        """
        restart_server = "bash " + WORKDIR + \
                           '/log/startup' + str(cluster_node) + '.sh'
        os.system(restart_server)
        ping_query = BASEDIR + '/bin/mysqladmin --user=root --socket=' + \
                     WORKDIR + '/node' + cluster_node + '/mysql.sock ping > /dev/null 2>&1'
        for startup_timer in range(120):
            time.sleep(1)
            ping_check = subprocess.call(ping_query, shell=True, stderr=subprocess.DEVNULL)
            ping_status = ("{}".format(ping_check))
            if int(ping_status) == 0:
                utility_cmd.check_testcase(int(ping_status), "Cluster node restart is successful")
                break  # break the loop if mysqld is running

    def start_random_test(self, socket, db):
        my_extra = "--innodb_buffer_pool_size=8G --innodb_log_file_size=1G"
        dbconnection_check = db_connection.DbConnection(USER, socket)
        server_startup = pxc_startup.StartCluster(parent_dir, WORKDIR, BASEDIR, int(NODE))
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "Startup sanity check")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "Initializing cluster")
        if encryption == 'YES':
            result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "Configuration file creation")
        else:
            result = server_startup.create_config('none')
            utility_cmd.check_testcase(result, "Configuration file creation")
        result = server_startup.start_cluster(my_extra)
        utility_cmd.check_testcase(result, "Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "Database connection")
        # Sysbench load test
        sysbench = sysbench_run.SysbenchRun(BASEDIR, WORKDIR,
                                            socket)
        result = sysbench.sanity_check(db)
        utility_cmd.check_testcase(result, "Sysbench run sanity check")
        result = sysbench.sysbench_load(db, 64, 64, SYSBENCH_LOAD_TEST_TABLE_SIZE)
        utility_cmd.check_testcase(result, "Sysbench data load")
        utility_cmd.stop_pxc(WORKDIR, BASEDIR, NODE)
        wsrep_provider_options = {
            "gcache.keep_pages_size": [0, 1, 2],
            "gcache.recover": ["yes", "no"],
            "gcache.page_size": ["512M", "1024M"],
            "gcache.size": ["512M", "1024M", "2048M"],
            "repl.commit_order": [0, 1, 2, 3]
        }

        keys = wsrep_provider_options.keys()
        values = (wsrep_provider_options[key] for key in keys)
        wsrep_combinations = [dict(zip(keys, combination)) for combination in itertools.product(*values)]
        wsrep_provider_option = ''
        for wsrep_combination in range(0, len(wsrep_combinations)):
            for wsrep_option, wsrep_value in wsrep_combinations[wsrep_combination].items():
                wsrep_provider_option += wsrep_option + "=" + str(wsrep_value) + ";"
            print(datetime.now().strftime("%H:%M:%S ") + " WSREP Provider combination("
                  + wsrep_provider_option + ")")

            if encryption == 'YES':
                result = server_startup.create_config('encryption', wsrep_provider_option)
                utility_cmd.check_testcase(result, "Updated configuration file")
            else:
                result = server_startup.create_config('none', wsrep_provider_option)
                utility_cmd.check_testcase(result, "Updated configuration file")

            result = server_startup.start_cluster()
            utility_cmd.check_testcase(result, "Cluster startup")
            result = dbconnection_check.connection_check()
            utility_cmd.check_testcase(result, "Database connection check")
            result = sysbench.sysbench_oltp_read_write(db, 64, 64,
                                                       SYSBENCH_LOAD_TEST_TABLE_SIZE, 300)
            utility_cmd.check_testcase(result, "Sysbench oltp run initiated")
            query = 'pidof sysbench'
            sysbench_pid = os.popen(query).read().rstrip()
            time.sleep(100)
            shutdown_node = BASEDIR + '/bin/mysqladmin --user=root --socket=' + \
                            WORKDIR + '/node3/mysql.sock shutdown > /dev/null 2>&1'
            result = os.system(shutdown_node)
            utility_cmd.check_testcase(result, "Shutdown cluster node for IST/SST check")
            time.sleep(5)
            kill_sysbench = "kill -9 " + sysbench_pid
            os.system(kill_sysbench)
            self.startup_check(3)

            wsrep_provider_option = ''
            time.sleep(5)
            result = utility_cmd.check_table_count(BASEDIR, db, socket, WORKDIR + '/node2/mysql.sock')
            utility_cmd.check_testcase(result, "Checksum run for DB: test")
            utility_cmd.stop_pxc(WORKDIR, BASEDIR, NODE)


print("--------------------------------")
print("\nPXC WSREP provider random test")
print("--------------------------------")
sysbench_wsrep_provider_random_test = WSREPProviderRandomTest()
sysbench_wsrep_provider_random_test.start_random_test(WORKDIR + '/node1/mysql.sock', 'test')

