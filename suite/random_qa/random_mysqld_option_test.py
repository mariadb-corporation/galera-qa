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
from util import utility
from util import createsql
utility_cmd = utility.Utility()
utility_cmd.check_python_version()

# Read argument
parser = argparse.ArgumentParser(prog='PXC random mysqld option test', usage='%(prog)s [options]')
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
socket = config['config']['node1_socket']
pt_basedir = config['config']['pt_basedir']
sysbench_table_size = 10000
sysbench_run_time = 100


class RandomMySQLDOptionQA:
    def start_pxc(self):
        # Start PXC cluster for random mysqld options QA
        dbconnection_check = db_connection.DbConnection(user, '/tmp/node1.sock')
        server_startup = pxc_startup.StartCluster(parent_dir, workdir, basedir, int(node))
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "Startup sanity check")
        if encryption == 'YES':
            result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "Configuration file creation")
        else:
            result = server_startup.create_config('none')
            utility_cmd.check_testcase(result, "Configuration file creation")
        result = utility_cmd.create_custom_cnf(parent_dir, workdir)
        utility_cmd.check_testcase(result, "Added random mysqld options")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "Initializing cluster")
        result = server_startup.start_cluster('--max-connections=1500')
        utility_cmd.check_testcase(result, "Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "Database connection")

    def data_load(self, socket, db):
        # Sysbench data load
        sysbench = sysbench_run.SysbenchRun(basedir, workdir, socket)
        result = sysbench.sanity_check(db)
        utility_cmd.check_testcase(result, "Sysbench run sanity check")
        result = sysbench.sysbench_load(db, 64, 64, sysbench_table_size)
        utility_cmd.check_testcase(result, "Sysbench data load")
        result = sysbench.sysbench_oltp_read_write(db, 64, 64, sysbench_table_size, sysbench_run_time)
        utility_cmd.check_testcase(result, "Sysbench read write run")
        result = sysbench.sysbench_oltp_write_only(db, 64, 64, sysbench_table_size, sysbench_run_time)
        utility_cmd.check_testcase(result, "Sysbench write run")
        result = sysbench.sysbench_oltp_read_only(db, 64, 64, sysbench_table_size, sysbench_run_time)
        utility_cmd.check_testcase(result, "Sysbench read run")

        # Add prepared statement SQLs
        create_ps = basedir + "/bin/mysql --user=root --socket=" + \
            socket + ' < ' + parent_dir + '/util/prepared_statements.sql > /dev/null 2>&1'
        result = os.system(create_ps)
        utility_cmd.check_testcase(result, "Creating prepared statements")
        # Random data load
        if os.path.isfile(parent_dir + '/util/createsql.py'):
            generate_sql = createsql.GenerateSQL('/tmp/dataload.sql', 1000)
            generate_sql.OutFile()
            generate_sql.CreateTable()
            sys.stdout = sys.__stdout__
            data_load_query = basedir + "/bin/mysql --user=root --socket=" + \
                socket + ' ' + db + ' -f <  /tmp/dataload.sql >/dev/null 2>&1'
            result = os.system(data_load_query)
            utility_cmd.check_testcase(result, "Sample data load")


print("------------------------------")
print("PXC Random MySQLD options test")
print("------------------------------")
random_mysql_option_qa = RandomMySQLDOptionQA()
random_mysql_option_qa.start_pxc()
random_mysql_option_qa.data_load(socket, 'test')
