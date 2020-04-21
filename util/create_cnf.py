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

    def createconfig(self):
        """ Method to create cluster configuration file
            based on the node count. To create configuration
            file it will take default values from conf/pxc.cnf.
            For customised configuration please add your values
            in conf/custom.conf.
        """
        port = random.randint(10, 50) * 1001
        port_list = []
        addr_list = ''
        for j in range(1, self.node + 1):
            port_list += [port + (j * 2)]
            addr_list = addr_list + '127.0.0.1:' + str(port + (j * 2) + 2) + ','
        if not os.path.isfile(self.workdir + '/conf/pxc.cnf'):
            print('Default pxc.cnf is missing in ' + self.workdir + '/conf')
            return 1
        for i in range(1, self.node + 1):
            shutil.copy(self.workdir + '/conf/pxc.cnf', self.workdir + '/conf/node' + str(i) + '.cnf')
            cnf_name = open(self.workdir + '/conf/node' + str(i) + '.cnf', 'a+')
            cnf_name.write('wsrep_cluster_address=gcomm://' + addr_list + '\n')
            cnf_name.write('port=' + str(port_list[i - 1]) + '\n')
            cnf_name.write("wsrep_provider_options='gmcast.listen_addr=tcp://127.0.0.1:" +
                           str(port_list[i - 1] + 8) + "'\n")
            cnf_name.close()
        return 0


config = configparser.ConfigParser()
config.read('config.ini')
workdir = config['config']['workdir']
basedir = config['config']['basedir']
cnf_file = CreateCNF(workdir, basedir, 2)
cnf_file.createconfig()