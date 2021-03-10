#!/usr/bin/env python3
import os
import sys
import argparse
import shutil
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

# Read argument
parser = argparse.ArgumentParser(prog='Galera replication test using PXB', usage='%(prog)s [options]')
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
        script_dir = os.path.dirname(os.path.realpath(__file__))
        dbconnection_check = db_connection.DbConnection(USER, WORKDIR + '/node1/mysql.sock')
        server_startup = galera_startup.StartCluster(parent_dir, WORKDIR, BASEDIR, int(self.node), debug)
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "PXC: Startup sanity check")
        if encryption == 'YES':
            result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "PXC: Configuration file creation")
        else:
            result = server_startup.create_config('none')
            utility_cmd.check_testcase(result, "PXC: Configuration file creation")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "PXC: Initializing cluster")
        result = server_startup.add_myextra_configuration(script_dir + '/replication.cnf')
        utility_cmd.check_testcase(result, "PXC: Adding custom configuration")
        result = server_startup.start_cluster(my_extra)
        utility_cmd.check_testcase(result, "PXC: Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "PXC: Database connection")

    def backup_galera_node(self):
        """ Backup Cluster node using
            Percona XtraBackup tool.
            This method will also do
            sanity check before backup
        """
        utility_cmd.pxb_sanity_check(BASEDIR, WORKDIR, WORKDIR + '/node1/mysql.sock')
        if os.path.exists(WORKDIR + '/mdnode1'):
            shutil.rmtree(WORKDIR + '/mdnode1')
        utility_cmd.pxb_backup(WORKDIR, WORKDIR + '/node1', WORKDIR + '/node1/mysql.sock',
                               encryption, WORKDIR + '/mdnode1')

    def start_slave(self, node, my_extra=None):
        """ Start MariaDB Server. This method will
            perform sanity checks for PS startup
            :param my_extra: We can pass extra MD startup
                             option with this parameter
        """
        if my_extra is None:
            my_extra = ''
        # Start Galera cluster for replication test
        script_dir = os.path.dirname(os.path.realpath(__file__))
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
        result = server_startup.add_myextra_configuration(script_dir + '/replication.cnf')
        utility_cmd.check_testcase(result, "MD: Adding custom configuration")
        result = server_startup.start_server(my_extra)
        utility_cmd.check_testcase(result, "MD: Cluster startup")
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


replication_run = SetupReplication(BASEDIR, WORKDIR, NODE)
print("\nSetup replication using Percona Xtrabackup")
print("------------------------------------------")
replication_run.start_galera()
replication_run.sysbench_run(WORKDIR + '/node1/mysql.sock', 'galeradb', 'Galera')
replication_run.data_load('mdg_dataload_db', WORKDIR + '/node1/mysql.sock', 'Galera')
replication_run.backup_galera_node()
replication_run.start_slave('1')
utility_cmd.invoke_replication(BASEDIR, WORKDIR + '/node1/mysql.sock', MD1_SOCKET, 'backup_slave', 'none')
utility_cmd.replication_io_status(BASEDIR, MD1_SOCKET, 'MD', 'none')
utility_cmd.replication_sql_status(BASEDIR, MD1_SOCKET, 'MD', 'none')

utility_cmd.stop_galera(WORKDIR, BASEDIR, NODE)
utility_cmd.stop_md(WORKDIR, BASEDIR, '1')
