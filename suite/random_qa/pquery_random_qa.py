#!/usr/bin/env python3
import os
import sys
import argparse
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

    def data_load(self, socket, db):

        # pquery random load
        threads = [16, 64, 512, 1024]
        tables = [16, 32, 64, 128]
        records = [100, 500, 1000]
        seeds = [100, 500, 1000]
        for thread, table, record, seed in \
                itertools.product(threads, tables, records, seeds):
            self.start_galera()
            pquery_cmd = PQUERY_BIN + " --database=" + db + " --threads=" + str(table) + " --logdir=" + \
                WORKDIR + "/log --log-all-queries --log-failed-queries --user=root --socket=" + \
                socket + " --seed " + str(seed) + " --tables " + str(table) + " " + \
                PQUERY_EXTRA + " --seconds 300  --sql-file " + \
                PQUERY_GRAMMER_FILE + " --records " + str(record) + "> " + \
                WORKDIR + "/log/pquery_run.log"
            utility_cmd.check_testcase(0, "PQUERY RUN command : " + pquery_cmd)
            query_status = os.system(pquery_cmd)
            if int(query_status) != 0:
                utility_cmd.check_testcase(1, "ERROR!: PQUERY run is failed")


print("-----------------------")
print("Galera Random PQUERY QA")
print("-----------------------")
random_pquery_qa = RandomPQueryQA()
if not os.path.isfile(PQUERY_BIN):
    print(PQUERY_BIN + ' does not exist')
    exit(1)
random_pquery_qa.data_load(WORKDIR + '/node1/mysql.sock', 'test')
