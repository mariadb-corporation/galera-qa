#!/usr/bin/env python3
import os
import sys
import argparse
import time
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from config import *
from util import pxc_startup
from util import db_connection
from util import sysbench_run
from util import utility
from util import createsql
from util import rqg_datagen

# Read argument
parser = argparse.ArgumentParser(prog='PXC consistency test', usage='%(prog)s [options]')
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
sysbench_run_time = 10


class ConsistencyCheck:
    def __init__(self, basedir, workdir, user, node1_socket, pt_basedir, node):
        self.workdir = workdir
        self.basedir = basedir
        self.user = user
        self.socket = node1_socket
        self.pt_basedir = pt_basedir
        self.node = node

    def run_query(self, query):
        query_status = os.system(query)
        if int(query_status) != 0:
            print("ERROR! Query execution failed: " + query)
            return 1
        return 0

    def start_pxc(self):
        # Start PXC cluster for replication test
        dbconnection_check = db_connection.DbConnection(USER, WORKDIR + '/node1/mysql.sock')
        server_startup = pxc_startup.StartCluster(parent_dir, WORKDIR, BASEDIR, int(NODE), debug)
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
        result = server_startup.start_cluster()
        utility_cmd.check_testcase(result, "Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "Database connection")

    def sysbench_run(self, socket, db):
        # Sysbench dataload for consistency test
        sysbench = sysbench_run.SysbenchRun(BASEDIR, WORKDIR,
                                            socket, debug)

        result = sysbench.sanity_check(db)
        utility_cmd.check_testcase(result, "Replication QA sysbench run sanity check")
        result = sysbench.sysbench_load(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS, SYSBENCH_NORMAL_TABLE_SIZE)
        utility_cmd.check_testcase(result, "Replication QA sysbench data load")
        if encryption == 'YES':
            for i in range(1, int(SYSBENCH_TABLE_COUNT) + 1):
                encrypt_table = BASEDIR + '/bin/mysql --user=root ' \
                    '--socket=' + socket + ' -e "' \
                    ' alter table ' + db + '.sbtest' + str(i) + \
                    " encryption='Y'" \
                    '"; > /dev/null 2>&1'
                if debug == 'YES':
                    print(encrypt_table)
                os.system(encrypt_table)

    def data_load(self, db, socket):
        # Random dataload for consistency test
        if os.path.isfile(parent_dir + '/util/createsql.py'):
            generate_sql = createsql.GenerateSQL('/tmp/dataload.sql', 1000)
            generate_sql.OutFile()
            generate_sql.CreateTable()
            sys.stdout = sys.__stdout__
            create_db = self.basedir + "/bin/mysql --user=root --socket=" + \
                socket + ' -Bse"drop database if exists ' + db + \
                ';create database ' + db + ';" 2>&1'
            if debug == 'YES':
                print(create_db)
            result = os.system(create_db)
            utility_cmd.check_testcase(result, "Sample DB creation")
            data_load_query = self.basedir + "/bin/mysql --user=root --socket=" + \
                socket + ' ' + db + ' -f <  /tmp/dataload.sql >/dev/null 2>&1'
            if debug == 'YES':
                print(data_load_query)
            result = os.system(data_load_query)
            utility_cmd.check_testcase(result, "Sample data load")


print("\nPXC data consistency test between nodes")
print("----------------------------------------")
consistency_run = ConsistencyCheck(BASEDIR, WORKDIR, USER, WORKDIR + '/node1/mysql.sock', PT_BASEDIR, NODE)
rqg_dataload = rqg_datagen.RQGDataGen(BASEDIR, WORKDIR, USER, debug)
consistency_run.start_pxc()
consistency_run.sysbench_run(WORKDIR + '/node1/mysql.sock', 'test')
consistency_run.data_load('pxc_dataload_db', WORKDIR + '/node1/mysql.sock')
rqg_dataload.pxc_dataload(WORKDIR + '/node1/mysql.sock')
version = utility_cmd.version_check(BASEDIR)
time.sleep(5)
result = utility_cmd.check_table_count(BASEDIR, 'test', WORKDIR + '/node1/mysql.sock',
                                       WORKDIR + '/node2/mysql.sock')
utility_cmd.check_testcase(result, "Checksum run for DB: test")
result = utility_cmd.check_table_count(BASEDIR, 'pxc_dataload_db', WORKDIR + '/node1/mysql.sock',
                                       WORKDIR + '/node2/mysql.sock')
utility_cmd.check_testcase(result, "Checksum run for DB: pxc_dataload_db")
result = utility_cmd.check_table_count(BASEDIR, 'db_galera', WORKDIR + '/node1/mysql.sock',
                                       WORKDIR + '/node2/mysql.sock')
utility_cmd.check_testcase(result, "Checksum run for DB: db_galera")