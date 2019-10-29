#!/usr/bin/env python3
import os
import sys
import configparser
import datetime
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from util import utility
utility_cmd = utility.Utility()
utility_cmd.check_python_version()

# Reading initial configuration
config = configparser.ConfigParser()
config.read('pquery3-run.ini')

WORKDIR = config['config']['workdir']
RUNDIR = config['config']['rundir']
BASEDIR = config['config']['basedir']
SERVER = config['config']['server']
NODE = config['config']['node']
USER = config['config']['user']
TRIALS = config['config']['trials']
SAVE_SQL = config['config']['save_sql']
SAVE_TRIALS_WITH_CORE = config['config']['save_trials_with_core']
ENCRYPTION = config['config']['encryption']
MY_EXTRA = config['config']['myextra']
PQUERY_BIN = config['pquery']['pquery_bin']
PQUERY_BASE_CONFIG = config['pquery']['pquery_base_config']
TABLES = config['pquery']['tables']
RECORDS = config['pquery']['records']
SEED = config['pquery']['seed']
RECREATE_TABLE = config['pquery']['recreate_table']
OPTIMIZE = config['pquery']['optimize']
RENAME_COLUMN = config['pquery']['rename_column']
ADD_INDEX = config['pquery']['add_index']
DROP_INDEX = config['pquery']['drop_index']
ADD_COLUMN = config['pquery']['add_column']
PRIMARY_KEY_PROBABLITY = config['pquery']['primary_key_probablity']


class PQueryRun:
    def printit(self, text):
        now = datetime.now().strftime("%H:%M:%S ")
        print(now + ' ' + f'{text:100}')

    def start_server(self, node):
        self.printit("Generating PXC data directory template")
        if SERVER == "pxc":
            utility_cmd.start_pxc(parent_dir, WORKDIR, BASEDIR, node,
                                  WORKDIR + '/node1/mysql.sock', USER, ENCRYPTION, MY_EXTRA)
            self.printit("3 Node PXC Cluster started ok. Clients:")
        elif SERVER == "ps":
            utility_cmd.start_ps(parent_dir, WORKDIR, BASEDIR, node,
                                 WORKDIR + '/psnode1/mysql.sock', USER, ENCRYPTION, MY_EXTRA)

    def stop_server(self, node):
        if SERVER == "pxc":
            for i in range(1, NODE + 1):
                shutdown_node = BASEDIR + '/bin/mysqladmin --user=root --socket=' + \
                            WORKDIR + '/node' + str(i) + '/mysql.sock shutdown > /dev/null 2>&1'
                result = os.system(shutdown_node)
                utility_cmd.check_testcase(result, "Shutdown cluster node for crash recovery")
        elif SERVER == "ps":
            utility_cmd.start_ps(parent_dir, WORKDIR, BASEDIR, node,
                                 WORKDIR + '/psnode1/mysql.sock', USER, ENCRYPTION, MY_EXTRA)


print("-------------------------")
print("\nPXC pquery run         ")
print("-------------------------")
pquery_run = PQueryRun()
if SERVER == "pxc":
    pquery_run.start_server(NODE)
elif SERVER == "ps":
    pquery_run.start_server(1)
