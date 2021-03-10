#!/usr/bin/env python3
import os
import sys
import argparse
import time
import subprocess
import itertools
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from config import *
from util import galera_startup
from util import db_connection
from util import utility

# Read argument
parser = argparse.ArgumentParser(prog='Galera random mysqld option test', usage='%(prog)s [options]')
parser.add_argument('-e', '--encryption-run', action='store_true',
                    help='This option will enable encryption options')
parser.add_argument('-d', '--debug', action='store_true',
                    help='This option will enable debug logging')
args = parser.parse_args()
if args.encryption_run is True:
    encryption = 'YES'
    PQUERY_EXTRA = ""
else:
    encryption = 'NO'
    PQUERY_EXTRA = "--no-enc"

if args.debug is True:
    debug = 'YES'
else:
    debug = 'NO'

utility_cmd = utility.Utility(debug)
utility_cmd.check_python_version()


class RandomPQueryQA:
    def start_galera(self):
        # Start Galera cluster for pquery run
        dbconnection_check = db_connection.DbConnection(USER, WORKDIR + '/node1/mysql.sock')
        server_startup = galera_startup.StartCluster(parent_dir, WORKDIR, BASEDIR, int(NODE), debug)
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "Startup sanity check")
        if encryption == 'YES':
            result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "Configuration file creation")
        else:
            result = server_startup.create_config('none')
            utility_cmd.check_testcase(result, "Configuration file creation")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "Initializing cluster")
        result = server_startup.start_cluster('--max-connections=1500')
        utility_cmd.check_testcase(result, "Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "Database connection")
        query = BASEDIR + "/bin/mysql --user=root --socket=" + \
            WORKDIR + "/node1/mysql.sock -e'drop database if exists test " \
                          "; create database test ;' > /dev/null 2>&1"
        if debug == 'YES':
            print(query)
        query_status = os.system(query)
        if int(query_status) != 0:
            # return 1
            print("ERROR!: Could not create test database.")
            exit(1)

    def startup_check(self, cluster_node):
        """ This method will check the node
            startup status.
        """
        ping_query = BASEDIR + '/bin/mysqladmin --user=root --socket=' + \
                     WORKDIR + '/node' + str(cluster_node) + '/mysql.sock ping > /dev/null 2>&1'
        for startup_timer in range(120):
            time.sleep(1)
            ping_check = subprocess.call(ping_query, shell=True, stderr=subprocess.DEVNULL)
            ping_status = ("{}".format(ping_check))
            if int(ping_status) == 0:
                utility_cmd.check_testcase(int(ping_status), "Cluster restart is successful")
                break  # break the loop if mysqld is running

    def data_load(self, socket, db):
        # pquery crash recovery qa
        self.start_galera()
        for i in range(1, 10):
            PQUERY_CMD = PQUERY_BIN + " --database=" + db + " --threads=50 --logdir=" + \
                         WORKDIR + "/log --log-all-queries --log-failed-queries --user=root --socket=" + \
                         socket + " --seed 1000 --tables 25 --records 1000 " + \
                         PQUERY_EXTRA + " --seconds 300 --undo-tbs-count 0  --sql-file " + \
                         PQUERY_GRAMMER_FILE + " --step " + str(i) + " > " + \
                         WORKDIR + "/log/pquery_run.log"
            utility_cmd.check_testcase(0, "PQUERY RUN command : " + PQUERY_CMD)
            query_status = os.system(PQUERY_CMD)
            if int(query_status) != 0:
                utility_cmd.check_testcase(1, "ERROR!: PQUERY run is failed")
            # kill existing mysqld process
            if debug == 'YES':
                print("Killing existing mysql process using 'kill -9' command")
            os.system("ps -ef | grep '" + WORKDIR + "/conf/node[0-9].cnf' | grep -v grep | "
                                                    "awk '{print $2}' | xargs kill -9 >/dev/null 2>&1")
            for j in range(1, int(NODE) + 1):
                if j == 1:
                    os.system("sed -i 's#safe_to_bootstrap: 0#safe_to_bootstrap: 1#' " +
                              WORKDIR + '/node1/grastate.dat')
                startup = "bash " + WORKDIR + \
                          '/log/startup' + str(j) + '.sh'
                if debug == 'YES':
                    print(startup)
                os.system(startup)
                self.startup_check(j)


print("-----------------------")
print("Galera Random PQUERY QA")
print("-----------------------")
random_pquery_qa = RandomPQueryQA()
if not os.path.isfile(PQUERY_BIN):
    print(PQUERY_BIN + ' does not exist')
    exit(1)
random_pquery_qa.data_load(WORKDIR + '/node1/mysql.sock', 'test')
