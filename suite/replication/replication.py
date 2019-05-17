import os
from util import pxc_startup
import configparser

# Reading initial configuration
config = configparser.ConfigParser()
config.read('config.ini')
workdir = config['config']['workdir']
basedir = config['config']['basedir']
node = config['config']['node']

class SetupReplication():
    def __init__(self, basedir, workdir, node):
        self.basedir = basedir
        self.workdir = workdir
        self.node = node

    def start_server(self):
        # Start PXC cluster for replication test
        script_dir = os.path.dirname(os.path.realpath(__file__))
        if os.path.isfile(script_dir + '/replication.cnf'):
            cnf_name = open(script_dir + '/replication.cnf', 'a+')
        server_startup = pxc_startup.StartCluster(script_dir, workdir, basedir, int(node))
        server_startup.sanitycheck()
        server_startup.createconfig()
        server_startup.myextra_config(script_dir + '/replication.cnf')
        server_startup.initializecluster()
        server_startup.startcluster()
        server_startup.connectioncheck()

