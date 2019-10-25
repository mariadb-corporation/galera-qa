#!/usr/bin/env python3
import os
import sys
import configparser
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
NODE1_SOCKET = config['config']['node1_socket']
NODE2_SOCKET = config['config']['node2_socket']
NODE3_SOCKET = config['config']['node3_socket']
PS1_SOCKET = config['config']['ps1_socket']
TRIALS = config['config']['trials']
SAVE_SQL = config['config']['save_sql']
SAVE_TRIALS_WITH_CORE = config['config']['save_trials_with_core']
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
    def start_server(self, node):
        if SERVER == "pxc":
            my_extra = ""
            utility_cmd.start_pxc(parent_dir, WORKDIR, BASEDIR, node, NODE1_SOCKET, USER, encryption, my_extra)
        elif SERVER == "ps":
            my_extra = ""
            utility_cmd.start_ps(parent_dir, WORKDIR, BASEDIR, node, PS1_SOCKET, USER, encryption, my_extra)


print("-------------------------")
print("\nPXC pquery run         ")
print("-------------------------")
pquery_run = PQueryRun()
if SERVER == "pxc":
    pquery_run.start_server(NODE)
elif SERVER == "ps":
    pquery_run.start_server(1)
