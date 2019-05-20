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

    def sanity_check(self):
        """ Sanity check method will remove existing
            cluster data directories and forcefully kill
            running mysqld processes. This will also check
            the availability of mysqld binary file.
        """
        # kill existing mysqld process
        os.system("ps -ef | grep 'node[0-9]' | grep -v grep | "
                  "awk '{print $2}' | xargs kill -9 >/dev/null 2>&1")
        if not os.path.exists(self.workdir + '/log'):
            os.mkdir(self.workdir + '/log')

        if not os.path.exists(self.workdir + '/conf'):
            os.mkdir(self.workdir + '/conf')

        if not os.path.isfile(self.basedir + '/bin/mysqld'):
            print(self.basedir + '/bin/mysqld does not exist')
            return 1
            exit(1)
        return 0

    # This method will help us to check PXC version
    def version_check(self):
        version_info = os.popen(self.basedir +
                                "/bin/mysqld --version 2>&1 "
                                "| grep -oe '[0-9]\.[0-9][\.0-9]*' | head -n1").read()
        version = "{:02d}{:02d}{:02d}".format(int(version_info.split('.')[0]),
                                              int(version_info.split('.')[1]),
                                              int(version_info.split('.')[2]))
        return version

    def create_config(self):
        """ Method to create cluster configuration file
            based on the node count. To create configuration
            file it will take default values from conf/pxc.cnf.
            For customised configuration please add your values
            in conf/custom.conf.
        """
        port = random.randint(10, 50) * 1000
        port_list = []
        addr_list = ''
        for j in range(1, self.node + 1):
            port_list += [port + (j * 100)]
            addr_list = addr_list + '127.0.0.1:' + str(port + (j * 100) + 8) + ','
        if not os.path.isfile(self.scriptdir + '/conf/pxc.cnf'):
            print('Default pxc.cnf is missing in ' + self.scriptdir + '/conf')
            return 1
            exit(1)
        else:
            shutil.copy(self.scriptdir + '/conf/custom.cnf', self.workdir + '/conf/custom.cnf')
        for i in range(1, self.node + 1):
            shutil.copy(self.scriptdir + '/conf/pxc.cnf',
                        self.workdir + '/conf/node' + str(i) + '.cnf')
            cnf_name = open(self.workdir + '/conf/node' + str(i) + '.cnf', 'a+')
            cnf_name.write('wsrep_cluster_address=gcomm://' + addr_list + '\n')

            """ Calling version check method to compare the version to 
                add wsrep_sst_auth variable. This variable does not 
                required starting from PXC-8.x 
            """
            version = self.version_check()
            if int(version) < int("080000"):
                cnf_name.write('wsrep_sst_auth=root:\n')
            cnf_name.write('port=' + str(port_list[i - 1]) + '\n')
            cnf_name.write("wsrep_provider_options='gmcast.listen_addr=tcp://127.0.0.1:"
                           + str(port_list[i - 1] + 8) + "'\n")
            cnf_name.write('socket=/tmp/node' + str(i) + '.sock\n')
            cnf_name.write('server_id=' + str(10 + i) + '\n')
            cnf_name.write('!include ' + self.workdir + '/conf/custom.cnf\n')
            cnf_name.close()
        return 0

    def add_myextra_configuration(self, config_file):
        """ Adding extra configurations
            based on the testcase
        """
        if not os.path.isfile(config_file):
            print('Custom config ' + config_file + ' is missing')
            return 1
            exit(1)
        config_file = config_file
        cnf_name = open(self.workdir + '/conf/custom.cnf', 'a+')
        cnf_name.write('\n')
        cnf_name.write('!include ' + config_file + '\n')
        cnf_name.close()
        return 0

    def initialize_cluster(self):
        """ Method to initialize the cluster database
            directories. This will initialize the cluster
            using --initialize-insecure option for
            passwordless authentication.
        """
        for i in range(1, self.node + 1):
            if os.path.exists(self.workdir + '/node' + str(i)):
                os.system('rm -rf ' + self.workdir + '/node' + str(i) + '>/dev/null 2>&1')
            if not os.path.isfile(self.workdir + '/conf/node' + str(i) + '.cnf'):
                print('Could not find config file /conf/node' + str(i) + '.cnf')
                exit(1)
            initialize_node = self.basedir + '/bin/mysqld --no-defaults --initialize-insecure --datadir=' \
                              + self.workdir + '/node' + str(i) + ' > ' + self.workdir \
                              + '/log/startup' + str(i) + '.log 2>&1'

            run_query = subprocess.call(initialize_node, shell=True, stderr=subprocess.DEVNULL)
            result = ("{}".format(run_query))

        return int(result)

    def start_cluster(self):
        """ Method to start the cluster nodes. This method
            will also check the startup status.
        """
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

            run_query = subprocess.call(startup, shell=True, stderr=subprocess.DEVNULL)
            result = ("{}".format(run_query))
            ping_query = self.basedir + '/bin/mysqladmin --user=root --socket=/tmp/node' + str(i) \
                          + '.sock ping > /dev/null 2>&1'
            for startup_timer in range(120):
                time.sleep(1)
                ping_check = subprocess.call(ping_query, shell=True, stderr=subprocess.DEVNULL)
                ping_status = ("{}".format(ping_check))
                if int(ping_status) == 0:
                    break  # break the loop if mysqld is running

        return int(ping_status)

