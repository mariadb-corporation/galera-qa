#!/usr/bin/env python3
import os
import sys
import configparser
import argparse
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from util import pxc_startup
from util import db_connection
from util import sysbench_run
from util import ps_startup
from util import utility
from util import createsql
from util import rqg_datagen
utility_cmd = utility.Utility()
utility_cmd.check_python_version()

# Read argument
parser = argparse.ArgumentParser(prog='PXC replication test', usage='%(prog)s [options]')
parser.add_argument('-e', '--encryption-run', action='store_true',
                    help='This option will enable encryption options')
args = parser.parse_args()
if args.encryption_run is True:
    encryption = 'YES'
else:
    encryption = 'NO'

# Reading initial configuration
config = configparser.ConfigParser()
config.read(parent_dir + '/config.ini')
workdir = config['config']['workdir']
basedir = config['config']['basedir']
node = config['config']['node']
user = config['config']['user']
node1_socket = config['config']['node1_socket']
ps1_socket = config['config']['ps1_socket']
ps2_socket = config['config']['ps2_socket']
pt_basedir = config['config']['pt_basedir']
sysbench_user = config['sysbench']['sysbench_user']
sysbench_pass = config['sysbench']['sysbench_pass']
sysbench_db = config['sysbench']['sysbench_db']
sysbench_threads = 10
sysbench_table_size = 1000
sysbench_run_time = 10
version = utility_cmd.version_check(basedir)

class SetupReplication:
    def __init__(self, basedir, workdir, node):
        self.basedir = basedir
        self.workdir = workdir
        self.node = node

    def start_pxc(self, my_extra=None):
        """ Start Percona XtraDB Cluster. This method will
            perform sanity checks for cluster startup
            :param my_extra: We can pass extra PXC startup option
                             with this parameter
        """
        # Start PXC cluster for replication test
        if my_extra is None:
            my_extra = ''
        script_dir = os.path.dirname(os.path.realpath(__file__))
        dbconnection_check = db_connection.DbConnection(user, node1_socket)
        server_startup = pxc_startup.StartCluster(parent_dir, workdir, basedir, int(self.node))
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "PXC: Startup sanity check")
        if encryption == 'YES':
            result = utility_cmd.create_ssl_certificate(workdir)
            utility_cmd.check_testcase(result, "PXC: SSL Configuration")
            result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "PXC: Configuration file creation")
        else:
            result = server_startup.create_config('none')
            utility_cmd.check_testcase(result, "PXC: Configuration file creation")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "PXC: Initializing cluster")
        result = server_startup.add_myextra_configuration(script_dir + '/gtid_replication.cnf')
        utility_cmd.check_testcase(result, "PXC: Adding custom configuration")
        result = server_startup.start_cluster(my_extra)
        utility_cmd.check_testcase(result, "PXC: Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "PXC: Database connection")

    def start_ps(self, node, my_extra=None):
        """ Start Percona Server. This method will
            perform sanity checks for PS startup
            :param my_extra: We can pass extra PS startup
                             option with this parameter
        """
        if my_extra is None:
            my_extra = ''
        # Start PXC cluster for replication test
        script_dir = os.path.dirname(os.path.realpath(__file__))
        dbconnection_check = db_connection.DbConnection(user, ps1_socket)
        server_startup = ps_startup.StartPerconaServer(parent_dir, workdir, basedir, int(node))
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "PS: Startup sanity check")
        result = server_startup.create_config()
        utility_cmd.check_testcase(result, "PS: Configuration file creation")
        result = server_startup.add_myextra_configuration(script_dir + '/gtid_replication.cnf')
        utility_cmd.check_testcase(result, "PS: Adding custom configuration")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "PS: Initializing cluster")
        result = server_startup.start_server(my_extra)
        utility_cmd.check_testcase(result, "PS: Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "PS: Database connection")

    def sysbench_run(self, socket, db, node):
        # Sysbench data load
        sysbench = sysbench_run.SysbenchRun(basedir, workdir,
                                            sysbench_user, sysbench_pass,
                                            socket, sysbench_threads,
                                            sysbench_table_size, db,
                                            sysbench_threads, sysbench_run_time)

        result = sysbench.sanity_check()
        utility_cmd.check_testcase(result, node + ": Replication QA sysbench run sanity check")
        result = sysbench.sysbench_load()
        utility_cmd.check_testcase(result, node + ": Replication QA sysbench data load")

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
            result = os.system(create_db)
            utility_cmd.check_testcase(result, node + ": Replication QA sample DB creation")
            data_load_query = self.basedir + "/bin/mysql --user=root --socket=" + \
                socket + ' ' + db + ' -f <  /tmp/dataload.sql >/dev/null 2>&1'
            result = os.system(data_load_query)
            utility_cmd.check_testcase(result, node + ": Replication QA sample data load")

    def replication_testcase(self, ps_node, master, slave, comment, master_socket, slave_socket):
        if comment == "mtr":
            self.start_pxc('--slave-parallel-workers=5')
            self.start_ps(ps_node, '--slave-parallel-workers=5')
            comment = 'none'
        else:
            self.start_pxc()
            self.start_ps(ps_node)
        if comment == "msr":
            utility_cmd.invoke_replication(basedir, ps1_socket,
                                           slave_socket, 'GTID', "for channel 'master1'")
            utility_cmd.invoke_replication(basedir, ps2_socket,
                                           slave_socket, 'GTID', "for channel 'master2'")
        else:
            utility_cmd.invoke_replication(basedir, master_socket,
                                           slave_socket, 'GTID', comment)

        replication_run.sysbench_run(master_socket, 'sbtest', master)
        replication_run.data_load('ps_dataload_db', master_socket, master)
        rqg_dataload.initiate_rqg('rqg_test', master_socket)

        if comment == "msr":
            utility_cmd.replication_io_status(basedir, slave_socket, slave, 'master1')
            utility_cmd.replication_sql_status(basedir, slave_socket, slave, 'master1')
            utility_cmd.replication_io_status(basedir, slave_socket, slave, 'master2')
            utility_cmd.replication_sql_status(basedir, slave_socket, slave, 'master2')
        else:
            utility_cmd.replication_io_status(basedir, slave_socket, slave, comment)
            utility_cmd.replication_sql_status(basedir, slave_socket, slave, comment)


replication_run = SetupReplication(basedir, workdir, node)
rqg_dataload = rqg_datagen.RQGDataGen(basedir, workdir,
                                      'replication', user)
print("\nGTID PXC Node as Master and PS node as Slave")
print("----------------------------------------------")
replication_run.replication_testcase('1', 'PXC', 'PS', 'none', node1_socket, ps1_socket)
print("\nGTID PXC Node as Slave and PS node as Master")
print("----------------------------------------------")
replication_run.replication_testcase('1', 'PS', 'PXC', 'none', ps1_socket, node1_socket)

if int(version) > int("050700"):
    print("\nGTID PXC multi source replication")
    print("-----------------------------------")
    replication_run.replication_testcase('2', 'PS', 'PXC', 'msr', ps1_socket, node1_socket)
    print("\nGTID PXC multi thread replication")
    print("-----------------------------------")
    replication_run.replication_testcase('1', 'PS', 'PXC', 'mtr', ps1_socket, node1_socket)

