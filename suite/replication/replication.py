#!/usr/bin/env python3.7
import os
import sys
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from util import pxc_startup
from util import db_connection
from util import sysbench_run
from util import ps_startup
from util import utility
from util import createsql
import configparser

# Reading initial configuration
config = configparser.ConfigParser()
config.read(parent_dir + '/config.ini')
workdir = config['config']['workdir']
basedir = config['config']['basedir']
node = config['config']['node']
user = config['config']['user']
pt_basedir = config['config']['pt_basedir']
sysbench_user = config['sysbench']['sysbench_user']
sysbench_pass = config['sysbench']['sysbench_pass']
sysbench_db = config['sysbench']['sysbench_db']
sysbench_threads = 10
sysbench_table_size = 1000
sysbench_run_time = 10
utility_cmd = utility.Utility()


class SetupReplication:
    def __init__(self, basedir, workdir, node):
        self.basedir = basedir
        self.workdir = workdir
        self.node = node

    def start_pxc(self):
        # Start PXC cluster for replication test
        script_dir = os.path.dirname(os.path.realpath(__file__))
        dbconnection_check = db_connection.DbConnection(user, '/tmp/node1.sock')
        server_startup = pxc_startup.StartCluster(parent_dir, workdir, basedir, int(node))
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "PXC: Startup sanity check")
        result = server_startup.create_config()
        utility_cmd.check_testcase(result, "PXC: Configuration file creation")
        result = server_startup.add_myextra_configuration(script_dir + '/replication.cnf')
        utility_cmd.check_testcase(result, "PXC: Adding custom configuration")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "PXC: Initializing cluster")
        result = server_startup.start_cluster()
        utility_cmd.check_testcase(result, "PXC: Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "PXC: Database connection")

    def start_ps(self):
        # Start PXC cluster for replication test
        script_dir = os.path.dirname(os.path.realpath(__file__))
        dbconnection_check = db_connection.DbConnection(user, '/tmp/psnode.sock')
        server_startup = ps_startup.StartPerconaServer(parent_dir, workdir, basedir)
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "PS: Startup sanity check")
        result = server_startup.create_config()
        utility_cmd.check_testcase(result, "PS: Configuration file creation")
        result = server_startup.add_myextra_configuration(script_dir + '/replication.cnf')
        utility_cmd.check_testcase(result, "PS: Adding custom configuration")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "PS: Initializing cluster")
        result = server_startup.start_server()
        utility_cmd.check_testcase(result, "PS: Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "PS: Database connection")

    def start_replication(self, master_socket, slave_socket):
        # Setup async replication
        flush_log = self.basedir + "/bin/mysql --user=root --socket=" + \
            master_socket + \
            ' -Bse"flush logs" 2>&1'
        os.system(flush_log)
        master_log_file = self.basedir + "/bin/mysql --user=root --socket=" + \
            master_socket + \
            " -Bse'show master logs' | awk '{print $1}' | tail -1 2>&1"
        master_log_file = os.popen(master_log_file).read().rstrip()
        master_port = self.basedir + "/bin/mysql --user=root --socket=" + \
            master_socket + \
            ' -Bse"select @@port" 2>&1'
        master_port = os.popen(master_port).read().rstrip()
        invoke_slave = self.basedir + "/bin/mysql --user=root --socket=" + \
            slave_socket + ' -Bse"CHANGE MASTER TO MASTER_HOST=' + \
            "'127.0.0.1', MASTER_PORT=" + master_port + ", MASTER_USER='root'" + \
            ", MASTER_LOG_FILE='" + master_log_file + "'" + \
            ', MASTER_LOG_POS=4; START SLAVE;" 2>&1'
        os.system(invoke_slave)
        check_slave_status = self.basedir + "/bin/mysql --user=root --socket=" + \
            slave_socket + ' -Bse"SELECT SERVICE_STATE ' \
            'FROM performance_schema.replication_connection_status" 2>&1'
        check_slave_status = os.popen(check_slave_status).read().rstrip()
        if check_slave_status != 'ON':
            print("ERROR!: Slave is not running" + check_slave_status)
            exit(1)
        else:
            utility_cmd.check_testcase(0, "PS: Slave started")

    def sysbench_run(self, socket, db, node):
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

    def replication_status(self, socket):
        check_slave_status = self.basedir + "/bin/mysql --user=root --socket=" + \
            socket + ' -Bse"SELECT SERVICE_STATE ' \
            'FROM performance_schema.replication_connection_status" 2>&1'
        check_slave_status = os.popen(check_slave_status).read().rstrip()
        if check_slave_status != 'ON':
            print("ERROR!: Slave is not running" + check_slave_status)
            utility_cmd.check_testcase(1, "PS: Slave status after data load")
            exit(1)
        else:
            utility_cmd.check_testcase(0, "PS: Slave status after data load")


replication_run = SetupReplication(basedir, workdir, node)
print("\nPXC Node as Master and PS node as Slave")
print("---------------------------------------")
replication_run.start_pxc()
replication_run.start_ps()
replication_run.start_replication('/tmp/node1.sock', '/tmp/psnode.sock')
replication_run.sysbench_run('/tmp/node1.sock', 'pxcdb', 'PXC')
replication_run.data_load('pxc_dataload_db', '/tmp/node1.sock', 'PXC')
replication_run.replication_status('/tmp/psnode.sock')
print("\nPXC Node as Slave and PS node as Master")
print("---------------------------------------")
replication_run.start_pxc()
replication_run.start_ps()
replication_run.start_replication('/tmp/psnode.sock', '/tmp/node1.sock')
replication_run.sysbench_run('/tmp/psnode.sock', 'psdb', 'PS')
replication_run.data_load('ps_dataload_db', '/tmp/psnode.sock', 'PS')
replication_run.replication_status('/tmp/node1.sock')
print("\nPXC/PS Node as master and Slave")
print("---------------------------------------")
replication_run.start_pxc()
replication_run.start_ps()
replication_run.start_replication('/tmp/psnode.sock', '/tmp/node1.sock')
replication_run.start_replication('/tmp/node1.sock', '/tmp/psnode.sock')
replication_run.sysbench_run('/tmp/psnode.sock', 'psdb', 'PS')
replication_run.data_load('ps_dataload_db', '/tmp/psnode.sock', 'PS')
replication_run.sysbench_run('/tmp/node1.sock', 'pxcdb', 'PXC')
replication_run.data_load('pxc_dataload_db', '/tmp/node1.sock', 'PXC')
replication_run.replication_status('/tmp/node1.sock')
replication_run.replication_status('/tmp/psnode.sock')