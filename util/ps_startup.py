#!/usr/bin/env python
# Created by Ramesh Sivaraman, Percona LLC.
# This will help us to start Percona Server

import os
import subprocess
import random
import shutil
import time


class StartPerconaServer:

    def __init__(self, scriptdir, workdir, basedir):
        self.scriptdir = scriptdir
        self.workdir = workdir
        self.basedir = basedir

    def sanity_check(self):
        """ Sanity check method will remove existing
            data directory and forcefully kill
            running PS mysqld processes. This will also check
            the availability of mysqld binary file.
        """
        #kill existing mysqld process
        os.system("ps -ef | grep 'psnode' | grep -v grep | awk '{print $2}' | xargs kill -9 >/dev/null 2>&1")
        if not os.path.exists(self.workdir + '/log'):
            os.mkdir(self.workdir + '/log')

        if not os.path.exists(self.workdir + '/conf'):
            os.mkdir(self.workdir + '/conf')

        if not os.path.isfile(self.basedir + '/bin/mysqld'):
            print(self.basedir + '/bin/mysqld does not exist')
            return 1
            exit(1)

        return 0

    # This method will help us to check PS version
    def version_check(self):
        version_info = os.popen(self.basedir +
                                "/bin/mysqld --version 2>&1 | grep -oe '[0-9]\.[0-9][\.0-9]*' | head -n1").read()
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
        if not os.path.isfile(self.scriptdir + '/conf/ps.cnf'):
            print('Default pxc.cnf is missing in ' + self.scriptdir + '/conf')
            return 1
            exit(1)
        else:
            shutil.copy(self.scriptdir + '/conf/custom.cnf', self.workdir + '/conf/custom.cnf')
            shutil.copy(self.scriptdir + '/conf/ps.cnf', self.workdir + '/conf/ps.cnf')
            cnf_name = open(self.workdir + '/conf/ps.cnf', 'a+')
            cnf_name.write('\nport=' + str(port) + '\n')
            cnf_name.write('socket=/tmp/psnode.sock\n')
            cnf_name.write('server_id=100\n')
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
        if os.path.exists(self.workdir + '/psnode'):
            os.system('rm -rf ' + self.workdir + '/psnode >/dev/null 2>&1')
        if not os.path.isfile(self.workdir + '/conf/ps.cnf'):
            print('Could not find config file /conf/ps.cnf')
            exit(1)
        initialize_node = self.basedir + '/bin/mysqld --no-defaults --initialize-insecure --datadir=' \
                          + self.workdir + '/psnode > ' + self.workdir \
                          + '/log/ps_startup.log 2>&1'

        run_query = subprocess.call(initialize_node, shell=True, stderr=subprocess.DEVNULL)
        result = ("{}".format(run_query))
        return int(result)

    def start_server(self):
        """ Method to start the cluster nodes. This method
            will also check the startup status.
        """
        startup = self.basedir + '/bin/mysqld --defaults-file=' + self.workdir + \
            '/conf/ps.cnf --datadir=' + self.workdir + '/psnode --basedir=' + self.basedir + \
            ' --log-error=' + self.workdir + '/log/psnode.err > ' + self.workdir + \
            '/log/psnode.err 2>&1 &'

        run_cmd = subprocess.call(startup, shell=True, stderr=subprocess.DEVNULL)
        result = ("{}".format(run_cmd))
        ping_query = self.basedir + '/bin/mysqladmin --user=root ' \
                                    '--socket=/tmp/psnode.sock ping > /dev/null 2>&1'
        for startup_timer in range(120):
            time.sleep(1)
            ping_check = subprocess.call(ping_query, shell=True, stderr=subprocess.DEVNULL)
            ping_status = ("{}".format(ping_check))
            if int(ping_status) == 0:
                break  # break the loop if mysqld is running

        return int(ping_status)