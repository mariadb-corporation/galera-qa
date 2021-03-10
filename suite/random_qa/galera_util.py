#!/usr/bin/env python3
import os
import sys
import argparse
import time
import subprocess
import itertools
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from config import *
from util import galera_startup
from util import db_connection
from util import utility

# Read argument
parser = argparse.ArgumentParser(prog='Galera Utility', usage='%(prog)s [options]')
parser.add_argument('-e', '--encryption-run', action='store_true',
                    help='This option will enable encryption options')
parser.add_argument('--start', action='store_true',
                    help='Start Galera nodes')
parser.add_argument('--stop', action='store_true',
                    help='Stop Galera nodes')
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


class GaleraUtil:
    def start_galera(self):
        # Start Galera cluster
        dbconnection_check = db_connection.DbConnection(USER, WORKDIR + '/node1/mysql.sock')
        server_startup = galera_startup.StartCluster(parent_dir, WORKDIR, BASEDIR, int(NODE), debug)
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "Startup sanity check")
        # Check encryption run
        if encryption == 'YES':
            # Add encryption options
            result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "Configuration file creation")
        else:
            result = server_startup.create_config('none')
            utility_cmd.check_testcase(result, "Configuration file creation")
        # Initialize cluster (create data directory)
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "Initializing cluster")
        # Start cluster
        result = server_startup.start_cluster('--max-connections=1500 ')
        utility_cmd.check_testcase(result, "Cluster startup")
        # Check DB connection
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "Database connection")
        # Create database test
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
        utility_cmd.check_testcase(0, "Galera connection string")
        for i in range(1, int(NODE) + 1):
            # Print connection string
            print('\t' + BASEDIR + '/bin/mysql --user=root --socket=' +
                  WORKDIR + '/node' + str(i) + '/mysql.sock')

    def stop_galera(self):
        # Stop Galera cluster
        for i in range(int(NODE), 0, -1):
            shutdown_node = BASEDIR + '/bin/mysqladmin --user=root --socket=' + \
                        WORKDIR + '/node' + str(i) + '/mysql.sock shutdown > /dev/null 2>&1'
            result = os.system(shutdown_node)
            utility_cmd.check_testcase(result, "Galera: shutting down cluster node" + str(i))


galera_util = GaleraUtil()
if args.start is True:
    # Start Cluster
    galera_util.start_galera()

if args.stop is True:
    # Stop cluster
    galera_util.stop_galera()
