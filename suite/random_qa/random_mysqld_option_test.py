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
from util import utility
from util import createsql

# Read argument
parser = argparse.ArgumentParser(prog='Galera random mysqld option test', usage='%(prog)s [options]')
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


class RandomMySQLDOptionQA:

    def data_load(self, socket, db):
        # Sysbench data load
        sysbench = sysbench_run.SysbenchRun(BASEDIR, WORKDIR, socket, debug)
        result = sysbench.sanity_check(db)
        utility_cmd.check_testcase(result, "Sysbench run sanity check")
        result = sysbench.sysbench_load(db, 10, 10, SYSBENCH_NORMAL_TABLE_SIZE)
        utility_cmd.check_testcase(result, "Sysbench data load")

        # Add prepared statement SQLs
        create_ps = BASEDIR + "/bin/mysql --user=root --socket=" + \
            socket + ' < ' + parent_dir + '/util/prepared_statements.sql > /dev/null 2>&1'
        result = os.system(create_ps)
        utility_cmd.check_testcase(result, "Creating prepared statements")
        # Random data load
        if os.path.isfile(parent_dir + '/util/createsql.py'):
            generate_sql = createsql.GenerateSQL('/tmp/dataload.sql', 1000)
            generate_sql.OutFile()
            generate_sql.CreateTable()
            sys.stdout = sys.__stdout__
            data_load_query = BASEDIR + "/bin/mysql --user=root --socket=" + \
                socket + ' ' + db + ' -f <  /tmp/dataload.sql >/dev/null 2>&1'
            result = os.system(data_load_query)
            utility_cmd.check_testcase(result, "Sample data load")


print("---------------------------------")
print("Galera Random MySQLD options test")
print("---------------------------------")
mysql_options = open(parent_dir + '/conf/mysql_options_pxc80.txt')
for mysql_option in mysql_options:
    if os.path.exists(WORKDIR + '/random_mysql_error'):
        os.system('rm -rf ' + WORKDIR + '/random_mysql_error >/dev/null 2>&1')
        os.mkdir(WORKDIR + '/random_mysql_error')
    else:
        os.mkdir(WORKDIR + '/random_mysql_error')
    random_mysql_option_qa = RandomMySQLDOptionQA()
    # Start Galera cluster for random mysqld options QA
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

    cnf_name = open(WORKDIR + '/conf/custom.cnf', 'a+')
    cnf_name.write('\n')
    cnf_name.write(mysql_option)
    cnf_name.close()

    # result = utility_cmd.create_custom_cnf(parent_dir, WORKDIR)
    utility_cmd.check_testcase(0, "Added random mysqld option: " + mysql_option)
    result = server_startup.initialize_cluster()
    utility_cmd.check_testcase(result, "Initializing cluster")
    result = server_startup.start_cluster('--max-connections=1500')
    option = mysql_option.split('=')[0]
    opt_value = mysql_option.split('=')[1]
    opt_dir = option + '_' + opt_value
    if result != 0:
        os.mkdir(WORKDIR + '/random_mysql_error/' + opt_dir)
        shutil.copy(WORKDIR + '/conf/custom.cnf', WORKDIR +
                    '/random_mysql_error/' + opt_dir + '/custom.cnf')
        shutil.copytree(WORKDIR + '/log', WORKDIR + '/random_mysql_error/' + opt_dir + '/log')
        continue
    utility_cmd.check_testcase(result, "Cluster startup", "Not terminate")
    result = dbconnection_check.connection_check()
    utility_cmd.check_testcase(result, "Database connection")
    random_mysql_option_qa.data_load(WORKDIR + '/node1/mysql.sock', 'test')
    utility_cmd.stop_galera(WORKDIR, BASEDIR, NODE)
mysql_options.close()
