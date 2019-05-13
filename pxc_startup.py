#!/usr/bin/env python
# Created by Ramesh Sivaraman, Percona LLC.
# This will help us to start Percona XtraDB Cluster

import os
import subprocess
import random
import shutil
import time

class StartCluster:

    def __init__(self, scriptdir, workdir, basedir, node):
        self.scriptdir = scriptdir
        self.workdir = workdir
        self.basedir = basedir
        self.node = node

    """ Sanity check method will remove existing
        cluster data directories and forcefully kill
        running mysqld processes. This will also check 
        the availability of mysqld binary file.
    """
    def sanitycheck(self):
        #kill existing mysqld process
        os.system("ps -ef | grep 'node[0-9]' | grep -v grep | awk '{print $2}' | xargs kill -9 >/dev/null 2>&1")
        if not os.path.exists(self.workdir + '/log'):
            os.mkdir(self.workdir + '/log')

        if not os.path.exists(self.workdir + '/conf'):
            os.mkdir(self.workdir + '/conf')

        if os.path.isfile(self.basedir + '/bin/mysqld'):
            binary = self.basedir + '/bin/mysqld'
        else:
            print('mysqld is missing in basedir')
            return 1
            exit(1)

        return 0

    # This method will help us to check PXC version
    def versioncheck(self):
        version_info = os.popen(self.basedir +
                                "/bin/mysqld --version 2>&1 | grep -oe '[0-9]\.[0-9][\.0-9]*' | head -n1").read()
        version = "{:02d}{:02d}{:02d}".format(int(version_info.split('.')[0]),
                                              int(version_info.split('.')[1]),
                                              int(version_info.split('.')[2]))
        return version

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
            raddr_list = raddr_list + '127.0.0.1:' + str(rport + (j * 100) + 8) + ','
        if not os.path.isfile(self.scriptdir + '/conf/my.cnf'):
            print('Default my.cnf is missing in ' + self.scriptdir + '/conf')
            exit(1)
        else:
            shutil.copy(self.scriptdir + '/conf/custom.cnf', self.workdir + '/conf/custom.cnf')

        for i in range(1, self.node + 1):
            shutil.copy(self.scriptdir + '/conf/my.cnf', self.workdir + '/conf/node' + str(i) + '.cnf')
            cnfname = open(self.workdir + '/conf/node' + str(i) + '.cnf', 'a+')
            cnfname.write('wsrep_cluster_address=gcomm://' + raddr_list + '\n')

            """ Calling version check method to compare the version to 
                add wsrep_sst_auth variable. This variable does not 
                required starting from PXC-8.x 
            """
            version = self.versioncheck()
            if int(version) < int("080000"):
                cnfname.write('wsrep_sst_auth=root:\n')
            cnfname.write('port=' + str(rport_list[i - 1]) + '\n')
            cnfname.write("wsrep_provider_options='gmcast.listen_addr=tcp://127.0.0.1:"
                          + str(rport_list[i - 1] + 8) + "'\n")
            cnfname.write('socket=/tmp/node' + str(i) + '.sock\n')
            cnfname.close()

    """ Method to initialize the cluster database 
        directories. This will initialize the cluster 
        using --initialize-insecure option for 
        passwordless authentication.
    """
    def initializecluster(self):
        for i in range(1, self.node + 1):
            if os.path.exists(self.workdir + '/node' + str(i)):
                os.system('rm -rf ' + self.workdir + '/node' + str(i) + '>/dev/null 2>&1')
            if not os.path.isfile(self.workdir + '/conf/node' + str(i) + '.cnf'):
                print('Could not find config file /conf/node' + str(i) + '.cnf')
                exit(1)
            initialize_node = self.basedir + '/bin/mysqld --no-defaults --initialize-insecure --datadir=' \
                              + self.workdir + '/node' + str(i) + ' > ' + self.workdir \
                              + '/log/startup' + str(i) + '.log 2>&1'

            proc = subprocess.call(initialize_node, shell=True, stderr=subprocess.DEVNULL)
            result = ("{}".format(proc))

        return int(result)

    # Method to start the cluster nodes. This method
    # will also check the startup status.
    def startcluster(self):
        for i in range(1, self.node + 1):
            if i == 1:
                startup = self.basedir + '/bin/mysqld --defaults-file=' + self.workdir + '/conf/node' + str(i) + \
                          '.cnf --datadir=' + self.workdir + '/node' + str(i) + ' --basedir=' + self.basedir + \
                          ' --wsrep-provider=' + self.basedir + \
                          '/lib/libgalera_smm.so --wsrep-new-cluster --log-error=' + self.workdir +\
                          '/log/node' + str(i) + '.err > ' + self.workdir + '/log/node' + str(i) + '.err 2>&1 &'
            else:
                startup = self.basedir + '/bin/mysqld --defaults-file=' + self.workdir + '/conf/node' + str(i) + \
                          '.cnf --datadir=' + self.workdir + '/node' + str(i) + ' --basedir=' + self.basedir + \
                          ' --wsrep-provider=' + self.basedir + \
                          '/lib/libgalera_smm.so --log-error=' + self.workdir + '/log/node' + str(i) + '.err > ' \
                          + self.workdir + '/log/node' + str(i) + '.err 2>&1 &'

            proc = subprocess.call(startup, shell=True, stderr=subprocess.DEVNULL)
            result = ("{}".format(proc))
            pingquery = self.basedir + '/bin/mysqladmin --user=root --socket=/tmp/node' + str(i) \
                          + '.sock ping > /dev/null 2>&1'
            for startup_timer in range(120):
                time.sleep(1)
                pingcheck = subprocess.call(pingquery, shell=True, stderr=subprocess.DEVNULL)
                pingstatus = ("{}".format(pingcheck))
                if int(pingstatus) == 0:
                    break  # break the loop if mysqld is running

        return int(pingstatus)

