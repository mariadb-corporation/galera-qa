# This will help us to create cluster cnf on the fly
import os
import configparser
import shutil
import random

class CreateCNF:

    def __init__(self, workdir, basedir, node):
        self.node = node
        self.workdir = workdir
        self.basedir = basedir

    """ Method to create cluster configuration file 
        based on the node count. To create configuration
        file it will take default values from conf/my.cnf.
        For customised configuration please add your values 
        in conf/custom.conf.
    """
    def createconfig(self):
        rport = random.randint(10, 50) * 1000
        rport_list = []
        raddr_list = ''
        for j in range(1, self.node + 1):
            rport_list += [rport + (j * 100)]
            raddr_list = raddr_list + '127.0.0.1:' + str(rport + (j * 100) + 8 ) + ','
        if not os.path.isfile(self.workdir + '/conf/my.cnf'):
            print('Default my.cnf is missing in ' + self.workdir + '/conf')
            exit(1)
        for i in range(1, self.node + 1):
            shutil.copy(self.workdir + '/conf/my.cnf', self.workdir + '/conf/node' + str(i) + '.cnf')
            cnfname = open(self.workdir + '/conf/node' + str(i) + '.cnf', 'a+')
            cnfname.write('wsrep_cluster_address=gcomm://' + raddr_list + '\n')
            cnfname.write('port=' + str(rport_list[i - 1]) + '\n')
            cnfname.write("wsrep_provider_options='gmcast.listen_addr=tcp://127.0.0.1:" + str(rport_list[i - 1] + 8) + "'\n")
            cnfname.close()

config = configparser.ConfigParser()
config.read('config.ini')
workdir = config['config']['workdir']
basedir = config['config']['basedir']
cnffile = CreateCNF(workdir, basedir, 2)
cnffile.createconfig()
