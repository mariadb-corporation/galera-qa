#!/usr/bin/env python3
import os
import sys
import itertools
import argparse
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from config import *
from util import sysbench_run
from util import utility
from util import table_checksum
from util import rqg_datagen
from util import pxc_startup
from util import db_connection
from util import createsql

# Read argument
parser = argparse.ArgumentParser(prog='PXC replication test', usage='%(prog)s [options]')
parser.add_argument('-e', '--encryption-run', action='store_true',
                    help='This option will enable encryption options')
parser.add_argument('-d', '--debug', action='store_true',
                    help='This option will enable debug logging')
args = parser.parse_args()
if args.debug is True:
    debug = 'YES'
else:
    debug = 'NO'

utility_cmd = utility.Utility(debug)
utility_cmd.check_python_version()


class EncryptionTest:
    def sysbench_run(self, socket, db):
        # Sysbench data load
        version = utility_cmd.version_check(BASEDIR)
        checksum = ""
        if int(version) < int("080000"):
            checksum = table_checksum.TableChecksum(PT_BASEDIR, BASEDIR, WORKDIR, NODE, socket, debug)
            checksum.sanity_check()

        sysbench = sysbench_run.SysbenchRun(BASEDIR, WORKDIR, socket)
        result = sysbench.sanity_check(db)
        utility_cmd.check_testcase(result, "Sysbench run sanity check")
        result = sysbench.sysbench_load(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS, SYSBENCH_LOAD_TEST_TABLE_SIZE)
        utility_cmd.check_testcase(result, "Sysbench data load (threads : " + str(SYSBENCH_THREADS) + ")")

    def encryption_qa(self):
        # Encryption QA
        # Create data insert procedure
        rqg_dataload = rqg_datagen.RQGDataGen(BASEDIR, WORKDIR, USER)

        encryption_tmp_ts = ['innodb_temp_tablespace_encrypt=ON', 'innodb_temp_tablespace_encrypt=OFF']
        encryption_bin_log = ['binlog_encryption=ON', 'binlog_encryption=OFF']
        encryption_default_tbl = ['default_table_encryption=ON', 'default_table_encryption=OFF']
        encryption_redo_log = ['innodb_redo_log_encrypt=ON', 'innodb_redo_log_encrypt=OFF']
        encryption_undo_log = ['innodb_undo_log_encrypt=ON', 'innodb_undo_log_encrypt=OFF']
        encryption_sys_ts = ['innodb_sys_tablespace_encrypt=ON', 'innodb_sys_tablespace_encrypt=OFF']

        for encryption_tmp_ts_value, encryption_bin_log_value, encryption_default_tbl_value, \
            encryption_redo_log_value, encryption_undo_log_value, encryption_sys_ts_value in \
            itertools.product(encryption_tmp_ts, encryption_bin_log, encryption_default_tbl,
                              encryption_redo_log, encryption_undo_log, encryption_sys_ts):
            encryption_combination = encryption_tmp_ts_value + " " + encryption_bin_log_value + \
                                     " " + encryption_default_tbl_value + " " + encryption_redo_log_value + \
                                     " " + encryption_undo_log_value + " " + encryption_sys_ts_value
            utility_cmd.check_testcase(0, "Encryption options : " + encryption_combination)
            # Start PXC cluster for encryption test
            dbconnection_check = db_connection.DbConnection(USER, WORKDIR + '/node1/mysql.sock')
            server_startup = pxc_startup.StartCluster(parent_dir, WORKDIR, BASEDIR, int(NODE), debug)
            result = server_startup.sanity_check()
            utility_cmd.check_testcase(result, "Startup sanity check")
            result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "Configuration file creation")
            cnf_name = open(WORKDIR + '/conf/random_encryption.cnf', 'w+')
            cnf_name.write('[mysqld]\n')
            cnf_name.write("early-plugin-load=keyring_file.so" + '\n')
            cnf_name.write("keyring_file_data=keyring" + '\n')
            cnf_name.write(encryption_tmp_ts_value + '\n')
            cnf_name.write(encryption_bin_log_value + '\n')
            cnf_name.write(encryption_default_tbl_value + '\n')
            cnf_name.write(encryption_redo_log_value + '\n')
            cnf_name.write(encryption_undo_log_value + '\n')
            cnf_name.write(encryption_sys_ts_value + '\n')
            cnf_name.close()
            for i in range(1, int(NODE) + 1):
                os.system("sed -i 's#pxc_encrypt_cluster_traffic = OFF#pxc_encrypt_cluster_traffic = ON#g' " +
                          WORKDIR + '/conf/node' + str(i) + '.cnf')
                n_name = open(WORKDIR + '/conf/node' + str(i) + '.cnf', 'a+')
                n_name.write('!include ' + WORKDIR + '/conf/random_encryption.cnf\n')
                n_name.close()

            if encryption_sys_ts_value == "innodb_sys_tablespace_encrypt=ON":
                init_extra = "--innodb_sys_tablespace_encrypt=ON " \
                             "--early-plugin-load=keyring_file.so " \
                             " --keyring_file_data=keyring"
                result = server_startup.initialize_cluster(init_extra)

            else:
                result = server_startup.initialize_cluster()
            utility_cmd.check_testcase(result, "Initializing cluster")
            result = server_startup.start_cluster()
            utility_cmd.check_testcase(result, "Cluster startup")
            result = dbconnection_check.connection_check()
            utility_cmd.check_testcase(result, "Database connection")
            self.sysbench_run(WORKDIR + '/node1/mysql.sock', 'test')
            rqg_dataload.pxc_dataload(WORKDIR + '/node1/mysql.sock')
            # Add prepared statement SQLs
            create_ps = BASEDIR + "/bin/mysql --user=root --socket=" + \
                WORKDIR + '/node1/mysql.sock' + ' < ' + parent_dir + \
                '/util/prepared_statements.sql > /dev/null 2>&1'
            if debug == 'YES':
                print(create_ps)
            result = os.system(create_ps)
            utility_cmd.check_testcase(result, "Creating prepared statements")
            # Random data load
            if os.path.isfile(parent_dir + '/util/createsql.py'):
                generate_sql = createsql.GenerateSQL('/tmp/dataload.sql', 1000)
                generate_sql.OutFile()
                generate_sql.CreateTable()
                sys.stdout = sys.__stdout__
                data_load_query = BASEDIR + "/bin/mysql --user=root --socket=" + \
                    WORKDIR + '/node1/mysql.sock' + ' test -f <  /tmp/dataload.sql >/dev/null 2>&1'
                if debug == 'YES':
                    print(data_load_query)
                result = os.system(data_load_query)
                utility_cmd.check_testcase(result, "Sample data load")
            utility_cmd.stop_pxc(WORKDIR, BASEDIR, NODE)


print("-----------------------")
print("PXC Encryption test")
print("-----------------------")
encryption_test = EncryptionTest()
encryption_test.encryption_qa()
