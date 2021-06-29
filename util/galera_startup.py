#!/usr/bin/env python
# Created by Ramesh Sivaraman, Percona LLC.
# This will help us to start Percona XtraDB Cluster

import os
import subprocess
import random
import shutil
import time
from util import sanity


class StartCluster:
    def __init__(self, scriptdir, workdir, basedir, node, debug):
        self.scriptdir = scriptdir
        self.workdir = workdir
        self.basedir = basedir
        self.node = node
        self.debug = debug

    def sanity_check(self):
        """ Sanity check method will remove existing
            cluster data directories and forcefully kill
            running mysqld processes. This will also check
            the availability of mysqld binary file.
        """
        # kill existing mysqld process
        os.system("ps -ef | grep '" + self.workdir + "/conf/node[0-9].cnf' | grep -v grep | "
                                                     "awk '{print $2}' | xargs kill -9 >/dev/null 2>&1")
        if not os.path.exists(self.workdir + '/log'):
            os.mkdir(self.workdir + '/log')

        if not os.path.exists(self.workdir + '/conf'):
            os.mkdir(self.workdir + '/conf')

        if not os.path.isfile(self.basedir + '/bin/mysqld'):
            print(self.basedir + '/bin/mysqld does not exist')
            return 1
        return 0

    def create_config(self, wsrep_extra, wsrep_provider_option=None):
        """ Method to create cluster configuration file
            based on the node count. To create configuration
            file it will take default values from conf/mdg.cnf.
            For customised configuration please add your values
            in conf/custom.conf.
        """
        if wsrep_provider_option is None:
            wsrep_provider_option = ''
        version = sanity.version_check(self.basedir)
        port = random.randint(44, 55) * 100
        port_list = []
        addr_list = ''
        for j in range(1, int(self.node) + 1):
            port_list += [port + (j * 100)]
            addr_list = addr_list + '127.0.0.1:' + str(port + (j * 100) + 8) + ','
        if not os.path.isfile(self.scriptdir + '/conf/mdg.cnf'):
            print('Default mdg.cnf is missing in ' + self.scriptdir + '/conf')
            return 1
        else:
            shutil.copy(self.scriptdir + '/conf/custom.cnf', self.workdir + '/conf/custom.cnf')
        for i in range(1, self.node + 1):
            shutil.copy(self.scriptdir + '/conf/mdg.cnf',
                        self.workdir + '/conf/node' + str(i) + '.cnf')
            cnf_name = open(self.workdir + '/conf/node' + str(i) + '.cnf', 'a+')
            if self.debug == 'YES':
                cnf_name.write('wsrep-debug=1\n')
            cnf_name.write('wsrep_cluster_address=gcomm://' + addr_list + '\n')
            cnf_name.write('port=' + str(port_list[i - 1]) + '\n')
            if wsrep_extra != "none":
                cnf_name.write("wsrep_provider_options='gmcast.listen_addr=tcp://127.0.0.1:"
                               + str(port_list[i - 1] + 8) + ';' + wsrep_provider_option + 'socket.ssl_key='
                               + self.workdir + '/cert/server-key.pem;socket.ssl_cert='
                               + self.workdir + '/cert/server-cert.pem;socket.ssl_ca='
                               + self.workdir + "/cert/ca.pem'\n")
                cnf_name.write('!include ' + self.workdir + '/conf/ssl.cnf\n')
                sanity.create_ssl_certificate(self.workdir)
                sanity.add_ssl_config(self.workdir, wsrep_extra)
            else:
                cnf_name.write("wsrep_provider_options='gmcast.listen_addr=tcp://127.0.0.1:"
                               + str(port_list[i - 1] + 8) + ';' + wsrep_provider_option + "'\n")
            cnf_name.write('wsrep-provider = ' + self.basedir + '/lib/libgalera_smm.so\n')
            cnf_name.write('basedir = ' + self.basedir + '\n')
            cnf_name.write('datadir = ' + self.workdir + '/node' + str(i) + '\n')
            cnf_name.write('socket = ' + self.workdir + '/node' + str(i) + '/mysql.sock\n')
            cnf_name.write('log_error = ' + self.workdir + '/node' + str(i) + '/node' + str(i) + '.err\n')
            cnf_name.write('server_id=' + str(10 + i) + '\n')
            if wsrep_extra == "gtid":
                cnf_name.write('gtid_domain_id=' + str(20 + i) + '\n')
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
        config_file = config_file
        cnf_name = open(self.workdir + '/conf/custom.cnf', 'a+')
        cnf_name.write('\n')
        cnf_name.write('!include ' + config_file + '\n')
        cnf_name.close()
        return 0

    def initialize_cluster(self, init_extra=None):
        """ Method to initialize the cluster database
            directories. This will initialize the cluster
            using --initialize-insecure option for
            passwordless authentication.
        """
        result = ""
        if init_extra is None:
            init_extra = ''
        # This is for encryption testing. Encryption features are not fully supported
        # if wsrep_extra == "encryption":
        #    init_opt = '--innodb_undo_tablespaces=2 '
        for i in range(1, self.node + 1):
            if os.path.exists(self.workdir + '/node' + str(i)):
                os.system('rm -rf ' + self.workdir + '/node' + str(i) + '>/dev/null 2>&1')
            if not os.path.isfile(self.workdir + '/conf/node' + str(i) + '.cnf'):
                print('Could not find config file /conf/node' + str(i) + '.cnf')
                exit(1)
            version = sanity.version_check(self.basedir)
            if int(version) < int("1004"):
                os.mkdir(self.workdir + '/node' + str(i))
                initialize_node = self.basedir + '/scripts/mysql_install_db --no-defaults --force ' \
                                                 '--basedir=' + self.basedir + ' --datadir=' + \
                                                 self.workdir + '/node' + str(i) + ' > ' + \
                                                 self.workdir + '/log/startup' + str(i) + '.log 2>&1'
            else:
                initialize_node = self.basedir + '/scripts/mariadb-install-db --no-defaults --force ' \
                                ' --auth-root-authentication-method=normal ' + init_extra + \
                                ' --basedir=' + self.basedir + \
                                ' --datadir=' + self.workdir + '/node' + str(i) + ' > ' + \
                                self.workdir + '/log/startup' + str(i) + '.log 2>&1'
            if self.debug == 'YES':
                print(initialize_node)
            run_query = subprocess.call(initialize_node, shell=True, stderr=subprocess.DEVNULL)
            result = ("{}".format(run_query))
        return int(result)

    def start_cluster(self, my_extra=None):
        """ Method to start the cluster nodes. This method
            will also check the startup status.
        """
        ping_status = ""
        rr_check = "NO"
        if my_extra is None:
            my_extra = ''
        for i in range(1, self.node + 1):
            if i == 1:
                if rr_check == "NO":
                    startup = self.basedir + '/bin/mysqld --defaults-file=' + self.workdir + '/conf/node' + str(i) + \
                          '.cnf ' + my_extra + ' --wsrep-new-cluster > ' + self.workdir + \
                          '/node' + str(i) + '/node' + str(i) + '.err 2>&1 &'
                else:
                    if os.path.exists(self.workdir + '/rr'):
                        os.system('rm -rf ' + self.workdir + '/rr >/dev/null 2>&1')
                    os.mkdir(self.workdir + '/rr')
                    startup = 'export_RR_TRACE_DIR = "' + self.workdir + '/rr' \
                              '" ; /usr/bin/rr record --chaos ' + \
                              self.basedir + '/bin/mysqld --defaults-file=' + self.workdir + '/conf/node' + str(i) + \
                              '.cnf ' + my_extra + ' --wsrep-new-cluster > ' + self.workdir + \
                              '/node' + str(i) + '/node' + str(i) + '.err 2>&1 &'
            else:
                #if rr_check is None:
                startup = self.basedir + '/bin/mysqld --defaults-file=' + self.workdir + '/conf/node' + str(i) + \
                        '.cnf ' + my_extra + ' > ' + self.workdir + '/node' + str(i) + '/node' + \
                        str(i) + '.err 2>&1 &'
                #else:
                #    startup = 'export_RR_TRACE_DIR = "' + self.workdir + '/rr_node' + str(i) + \
                #              '" ; /usr/bin/rr record --chaos ' + \
                #              self.basedir + '/bin/mysqld --defaults-file=' + self.workdir + '/conf/node' + str(i) + \
                #              '.cnf ' + my_extra + ' > ' + self.workdir + '/node' + str(i) + '/node' + \
                #              str(i) + '.err 2>&1 &'

            save_startup = 'echo "' + startup + '" > ' + self.workdir + \
                           '/log/startup' + str(i) + '.sh'
            os.system(save_startup)
            if self.debug == 'YES':
                print(startup)
            subprocess.call(startup, shell=True, stderr=subprocess.DEVNULL)
            ping_query = self.basedir + '/bin/mysqladmin --user=root --socket=' + self.workdir + \
                '/node' + str(i) + '/mysql.sock ping > /dev/null 2>&1'
            for startup_timer in range(120):
                ping_check = subprocess.call(ping_query, shell=True, stderr=subprocess.DEVNULL)
                ping_status = ("{}".format(ping_check))
                if int(ping_status) == 0:
                    query = self.basedir + '/bin/mysql --user=root ' \
                                           '--socket=' + self.workdir + '/node' + str(i) + '/mysql.sock -Bse"' \
                                           "delete from mysql.user where user='';" \
                                           '" > /dev/null 2>&1'
                    if self.debug == 'YES':
                        print(query)
                    os.system(query)
                    break  # break the loop if mysqld is running
                time.sleep(1)

        return int(ping_status)
