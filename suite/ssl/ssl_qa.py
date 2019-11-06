#!/usr/bin/env python3
import os
import sys
import argparse
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
from util import table_checksum
utility_cmd = utility.Utility()
utility_cmd.check_python_version()

# Read argument
parser = argparse.ArgumentParser(prog='PXC SSL test', usage='%(prog)s [options]')
parser.add_argument('-e', '--encryption-run', action='store_true',
                    help='This option will enable encryption options')
args = parser.parse_args()
if args.encryption_run is True:
    encryption = 'YES'
else:
    encryption = 'NO'


class SSLCheck:
    def __init__(self, basedir, workdir, user, node1_socket, node):
        self.workdir = workdir
        self.basedir = basedir
        self.user = user
        self.socket = node1_socket
        self.node = node

    def run_query(self, query):
        query_status = os.system(query)
        if int(query_status) != 0:
            print("ERROR! Query execution failed: " + query)
            return 1
        return 0

    def start_pxc(self):
        # Start PXC cluster for SSL test
        dbconnection_check = db_connection.DbConnection(USER, self.socket)
        server_startup = pxc_startup.StartCluster(parent_dir, WORKDIR, BASEDIR, int(NODE))
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "Startup sanity check")
        if encryption == 'YES':
            result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "Configuration file creation")
        else:
            result = server_startup.create_config('ssl')
            utility_cmd.check_testcase(result, "Configuration file creation")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "Initializing cluster")
        result = server_startup.start_cluster()
        utility_cmd.check_testcase(result, "Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "Database connection")

    def sysbench_run(self, node1_socket, db):
        sysbench = sysbench_run.SysbenchRun(BASEDIR, WORKDIR,
                                            WORKDIR + '/node1/mysql.sock')

        result = sysbench.sanity_check(db)
        utility_cmd.check_testcase(result, "SSL QA sysbench run sanity check")
        result = sysbench.sysbench_load(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS,
                                        SYSBENCH_NORMAL_TABLE_SIZE)
        utility_cmd.check_testcase(result, "SSL QA sysbench data load")
        if encryption == 'YES':
            for i in range(1, SYSBENCH_THREADS + 1):
                encrypt_table = BASEDIR + '/bin/mysql --user=root ' \
                    '--socket=/tmp/node1.sock -e "' \
                    ' alter table ' + db + '.sbtest' + str(i) + \
                    " encryption='Y'" \
                    '"; > /dev/null 2>&1'
                os.system(encrypt_table)

    def data_load(self, db, node1_socket):
        if os.path.isfile(parent_dir + '/util/createsql.py'):
            generate_sql = createsql.GenerateSQL('/tmp/dataload.sql', 1000)
            generate_sql.OutFile()
            generate_sql.CreateTable()
            sys.stdout = sys.__stdout__
            create_db = self.basedir + "/bin/mysql --user=root --socket=" + \
                node1_socket + ' -Bse"drop database if exists ' + db + \
                ';create database ' + db + ';" 2>&1'
            result = os.system(create_db)
            utility_cmd.check_testcase(result, "SSL QA sample DB creation")
            data_load_query = self.basedir + "/bin/mysql --user=root --socket=" + \
                node1_socket + ' ' + db + ' -f <  /tmp/dataload.sql >/dev/null 2>&1'
            result = os.system(data_load_query)
            utility_cmd.check_testcase(result, "SSL QA sample data load")


print("\nPXC SSL test")
print("--------------")
ssl_run = SSLCheck(BASEDIR, WORKDIR, USER, WORKDIR + '/node1/mysql.sock', NODE)
ssl_run.start_pxc()
ssl_run.sysbench_run(WORKDIR + '/node1/mysql.sock', 'sbtest')
ssl_run.data_load('pxc_dataload_db', WORKDIR + '/node1/mysql.sock')
rqg_dataload = rqg_datagen.RQGDataGen(BASEDIR, WORKDIR, USER)
rqg_dataload.initiate_rqg('examples', 'test', WORKDIR + '/node1/mysql.sock')
version = utility_cmd.version_check(BASEDIR)
if int(version) < int("080000"):
    checksum = table_checksum.TableChecksum(PT_BASEDIR, BASEDIR, WORKDIR,
                                            NODE, WORKDIR + '/node1/mysql.sock')
    checksum.sanity_check()
    checksum.data_consistency('test,pxc_dataload_db')
else:
    result = utility_cmd.check_table_count(BASEDIR, 'test', WORKDIR + '/node1/mysql.sock',
                                           WORKDIR + '/node2/mysql.sock')
    utility_cmd.check_testcase(result, "Checksum run for DB: test")
    result = utility_cmd.check_table_count(BASEDIR, 'pxc_dataload_db', WORKDIR + '/node1/mysql.sock',
                                           WORKDIR + '/node2/mysql.sock')
    utility_cmd.check_testcase(result, "Checksum run for DB: pxc_dataload_db")
