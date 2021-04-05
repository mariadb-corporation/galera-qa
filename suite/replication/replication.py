#!/usr/bin/env python3
import os
import sys
import configparser
import argparse
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from config import *
from util import galera_startup
from util import db_connection
from util import sysbench_run
from util import md_startup
from util import utility
from util import createsql
from util import rqg_datagen

# Read argument
parser = argparse.ArgumentParser(prog='Galera replication test', usage='%(prog)s [options]')
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

version = utility_cmd.version_check(BASEDIR)


class SetupReplication:
    def __init__(self, basedir, workdir, node):
        self.basedir = basedir
        self.workdir = workdir
        self.node = node

    def start_galera(self, my_extra=None):
        """ Start MariaDB Galera Cluster. This method will
            perform sanity checks for cluster startup
            :param my_extra: We can pass extra Galera startup option
                             with this parameter
        """
        # Start Galera cluster for replication test
        if my_extra is None:
            my_extra = ''
        dbconnection_check = db_connection.DbConnection(USER, WORKDIR + '/node1/mysql.sock')
        server_startup = galera_startup.StartCluster(parent_dir, WORKDIR, BASEDIR, int(self.node), debug)
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "Galera: Startup sanity check")
        if encryption == 'YES':
            result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "Galera: Configuration file creation")
        else:
            result = server_startup.create_config('none')
            utility_cmd.check_testcase(result, "Galera: Configuration file creation")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "Galera: Initializing cluster")
        result = server_startup.add_myextra_configuration(cwd + '/replication.cnf')
        utility_cmd.check_testcase(result, "Galera: Adding custom configuration")
        result = server_startup.start_cluster(my_extra)
        utility_cmd.check_testcase(result, "Galera: Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "Galera: Database connection")

    def start_md(self, node, my_extra=None):
        """ Start MariaDB Server. This method will
            perform sanity checks for MD startup
            :param my_extra: We can pass extra MD startup
                             option with this parameter
        """
        if my_extra is None:
            my_extra = ''
        # Start MariaDB Server for replication test
        dbconnection_check = db_connection.DbConnection(USER, MD1_SOCKET)
        server_startup = md_startup.StartPerconaServer(parent_dir, WORKDIR, BASEDIR, int(node), debug)
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "MD: Startup sanity check")
        if encryption == 'YES':
            result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "MD: Configuration file creation")
        else:
            result = server_startup.create_config()
            utility_cmd.check_testcase(result, "MD: Configuration file creation")
        result = server_startup.add_myextra_configuration(cwd + '/replication.cnf')
        utility_cmd.check_testcase(result, "MD: Adding custom configuration")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "MD: Initializing MariaDB Server")
        result = server_startup.start_server(my_extra)
        utility_cmd.check_testcase(result, "MD: MariaDB Server startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "MD: Database connection")

    def sysbench_run(self, socket, db, node):
        # Sysbench data load
        sysbench = sysbench_run.SysbenchRun(BASEDIR, WORKDIR,
                                            socket, debug)

        result = sysbench.sanity_check(db)
        utility_cmd.check_testcase(result, node + ": Replication QA sysbench run sanity check")
        result = sysbench.sysbench_load(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS, SYSBENCH_NORMAL_TABLE_SIZE)
        utility_cmd.check_testcase(result, node + ": Replication QA sysbench data load")
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

    def data_load(self, db, socket, node):
        # Random data load
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
            utility_cmd.check_testcase(result, node + ": Replication QA sample DB creation")
            data_load_query = self.basedir + "/bin/mysql --user=root --socket=" + \
                socket + ' ' + db + ' -f <  /tmp/dataload.sql >/dev/null 2>&1'
            if debug == 'YES':
                print(data_load_query)
            result = os.system(data_load_query)
            utility_cmd.check_testcase(result, node + ": Replication QA sample data load")
        # Add prepared statement SQLs
        create_ps = self.basedir + "/bin/mysql --user=root --socket=" + \
            socket + ' < ' + parent_dir + '/util/prepared_statements.sql > /dev/null 2>&1'
        if debug == 'YES':
            print(create_ps)
        result = os.system(create_ps)
        utility_cmd.check_testcase(result, node + ": Replication QA prepared statements dataload")

    def replication_testcase(self, ps_node, master, slave, comment, master_socket, slave_socket):
        if comment == "mtr":
            self.start_galera('--slave-parallel-workers=5')
            self.start_md(ps_node, '--slave-parallel-workers=5')
            comment = 'none'
        else:
            self.start_galera()
            self.start_md(ps_node)
        if comment == "msr":
            utility_cmd.invoke_msr_replication(BASEDIR, MD1_SOCKET, MD2_SOCKET, slave_socket, 'NONGTID')
        else:
            utility_cmd.invoke_replication(BASEDIR, master_socket,
                                           slave_socket, 'NONGTID', comment)

        replication_run.sysbench_run(master_socket, 'sbtest', master)
        replication_run.data_load('md_dataload_db', master_socket, master)
        rqg_dataload = rqg_datagen.RQGDataGen(BASEDIR, WORKDIR, USER, debug)
        rqg_dataload.galera_dataload(master_socket)

        if comment == "msr":
            utility_cmd.replication_io_status(BASEDIR, slave_socket, slave, "'master1'")
            utility_cmd.replication_sql_status(BASEDIR, slave_socket, slave, "'master1'")
            utility_cmd.replication_io_status(BASEDIR, slave_socket, slave, "'master2'")
            utility_cmd.replication_sql_status(BASEDIR, slave_socket, slave, "'master2'")
        else:
            utility_cmd.replication_io_status(BASEDIR, slave_socket, slave, comment)
            utility_cmd.replication_sql_status(BASEDIR, slave_socket, slave, comment)

        utility_cmd.stop_galera(WORKDIR, BASEDIR, NODE)
        utility_cmd.stop_md(WORKDIR, BASEDIR, ps_node)


replication_run = SetupReplication(BASEDIR, WORKDIR, NODE)
print("\nNON-GTID Galera Node as Master and MD node as Slave")
print("----------------------------------------------")
replication_run.replication_testcase('1', 'Galera', 'MD', 'none',
                                     WORKDIR + '/node1/mysql.sock', MD1_SOCKET)
print("\nNON-GTID Galera Node as Slave and MD node as Master")
print("----------------------------------------------")
replication_run.replication_testcase('1', 'MD', 'Galera', 'none', MD1_SOCKET,
                                     WORKDIR + '/node1/mysql.sock')

print("\nNON-GTID Galera multi source replication")
print("-----------------------------------")
replication_run.replication_testcase('2', 'MD', 'Galera', 'msr', MD1_SOCKET,
                                     WORKDIR + '/node1/mysql.sock')
print("\nNON-GTID Galera multi thread replication")
print("-----------------------------------")
replication_run.replication_testcase('1', 'MD', 'Galera', 'mtr', MD1_SOCKET,
                                     WORKDIR + '/node1/mysql.sock')
