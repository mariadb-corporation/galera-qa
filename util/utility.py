#!/usr/bin/env python3
import os
import random
import shutil
import subprocess
import sys
import time
from datetime import datetime
from distutils.spawn import find_executable
from util import db_connection
from util import pxc_startup
from util import ps_startup


class Utility:
    def __init__(self, debug):
        self.debug = debug

    def printit(self, text, status):
        # print the testcase status
        now = datetime.now().strftime("%H:%M:%S ")
        print(now + ' ' + f'{text:100}' + '[ ' + status + ' ]')

    def check_testcase(self, result, testcase, is_terminate=None):
        # print testcase status based on success/failure output.
        now = datetime.now().strftime("%H:%M:%S ")
        if result == 0:
            print(now + ' ' + f'{testcase:100}' + '[ \u2713 ]')
        else:
            print(now + ' ' + f'{testcase:100}' + '[ \u2717 ]')
            if is_terminate is None:
                exit(1)

    def check_python_version(self):
        """ Check python version. Raise error if the
            version is 3.5 or lower
        """
        if sys.version_info < (3, 6):
            print("\nError! You should use python 3.6 or greater\n")
            exit(1)

    def version_check(self, basedir):
        # Get database version number
        version_info = os.popen(basedir + "/bin/mysqld --version 2>&1 "
                                          "| grep -oe '[0-9]\.[0-9][\.0-9]*' | head -n1").read()
        version = "{:02d}{:02d}{:02d}".format(int(version_info.split('.')[0]),
                                              int(version_info.split('.')[1]),
                                              int(version_info.split('.')[2]))
        return version

    def create_custom_cnf(self, parent_dir, workdir):
        """ Add random mysqld options
        """
        # Read 10 random mysqld options from the option file
        with open(parent_dir + '/conf/mysql_options_pxc57.txt') as f:
            lines = random.sample(f.readlines(), 10)
        cnf_name = open(workdir + '/conf/custom.cnf', 'a+')
        cnf_name.write('\n')
        # Add the random option in custom.cnf
        for x in range(len(lines)):
            cnf_name.write(lines[x])
        cnf_name.close()
        return 0

    def check_table_count(self, basedir, db, socket1, socket2):
        """ This method will compare the table
            count between two nodes
        """
        query = basedir + '/bin/mysql -uroot ' + db + ' --socket=' + \
                socket1 + ' -Bse"show tables;"'
        tables = os.popen(query).read().rstrip()
        # Compare the table checksum between node1 and node2
        for table in tables.split('\n'):
            query = basedir + '/bin/mysql -uroot --socket=' + \
                    socket1 + ' -Bse"checksum table ' + \
                    db + '.' + table + ';"'
            if self.debug == 'YES':
                print(query)
            table_count_node1 = os.popen(query).read().rstrip()
            query = basedir + '/bin/mysql -uroot --socket=' + \
                    socket2 + ' -Bse"checksum table ' + \
                    db + '.' + table + ';"'
            if self.debug == 'YES':
                print(query)
            table_count_node2 = os.popen(query).read().rstrip()
            if table_count_node1 == table_count_node2:
                return 0
            else:
                print("\tTable(" + db + '.' + table + " ) checksum is different")
                return 1

    def pxb_sanity_check(self, basedir, workdir, socket):
        """ This method will check pxb installation and
            cleanup backup directory
        """
        # Check xtrabackup installation
        if find_executable('xtrabackup') is None:
            print('\tERROR! Percona Xtrabackup is not installed.')
            exit(1)

        # Recreate backup directory
        if os.path.exists(workdir + '/backup'):
            shutil.rmtree(workdir + '/backup')
            os.mkdir(workdir + '/backup')
        else:
            os.mkdir(workdir + '/backup')

        # Check PXC version and create XB user with mysql_native_password plugin.
        version = self.version_check(basedir)
        if int(version) < int("050700"):
            create_user = basedir + "/bin/mysql --user=root " \
                                    "--socket=" + socket + ' -e"create user xbuser' \
                                                           "@'localhost' identified by 'test" \
                                                           "';grant all on *.* to xbuser@'localhost'" \
                                                           ';" > /dev/null 2>&1'
        else:
            create_user = basedir + "/bin/mysql --user=root " \
                                    "--socket=" + socket + ' -e"create user xbuser' \
                                                           "@'localhost' identified with  mysql_native_password by 'test" \
                                                           "';grant all on *.* to xbuser@'localhost'" \
                                                           ';" > /dev/null 2>&1'
        if self.debug == 'YES':
            print(create_user)
        query_status = os.system(create_user)
        if int(query_status) != 0:
            print("ERROR!: Could not create xtrabackup user user : xbuser")
            exit(1)

    def pxb_backup(self, workdir, source_datadir, socket, encryption, dest_datadir=None):
        """ This method will backup PXC/PS data directory
            with the help of xtrabackup.
        """
        # Enable keyring file plugin if it is encryption run
        if encryption == 'YES':
            backup_extra = " --keyring-file-data=" + source_datadir + \
                           "/keyring --early-plugin-load='keyring_file=keyring_file.so'"
        else:
            backup_extra = ''

        # Backup data using xtrabackup
        backup_cmd = "xtrabackup --user=xbuser --password='test' --backup " \
                     " --target-dir=" + workdir + "/backup -S" + \
                     socket + " --datadir=" + source_datadir + " " + backup_extra + " --lock-ddl >" + \
                     workdir + "/log/xb_backup.log 2>&1"
        if self.debug == 'YES':
            print(backup_cmd)
        os.system(backup_cmd)

        # Prepare backup for node startup
        prepare_backup = "xtrabackup --prepare --target_dir=" + \
                         workdir + "/backup " + backup_extra + " --lock-ddl >" + \
                         workdir + "/log/xb_backup_prepare.log 2>&1"
        if self.debug == 'YES':
            print(prepare_backup)
        os.system(prepare_backup)

        # copy backup directory to destination
        if dest_datadir is not None:
            copy_backup = "xtrabackup --copy-back --target-dir=" + \
                          workdir + "/backup --datadir=" + \
                          dest_datadir + " " + backup_extra + " --lock-ddl >" + \
                          workdir + "/log/copy_backup.log 2>&1"
            if self.debug == 'YES':
                print(copy_backup)
            os.system(copy_backup)

        # Copy keyring file to destination directory for encryption startup
        if encryption == 'YES':
            os.system("cp " + source_datadir + "/keyring " + dest_datadir)

    def replication_io_status(self, basedir, socket, node, channel):
        """ This will check replication IO thread
            running status
        """
        if channel == 'none':
            channel = ""  # channel name is to identify the replication source
        # Get slave status
        version = self.version_check(basedir)
        if int(version) < int("050700"):
            io_status = basedir + "/bin/mysql --user=root --socket=" + \
                        socket + ' -Bse"SHOW SLAVE STATUS\G" 2>&1 ' \
                                 '| grep "Slave_IO_Running:" ' \
                                 "| awk '{ print $2 }'"
            if self.debug == 'YES':
                print(io_status)
            io_status = os.popen(io_status).read().rstrip()
            if io_status == "Yes":
                check_slave_status = 'ON'
            else:
                check_slave_status = 'OFF'
        else:
            check_slave_status = basedir + "/bin/mysql --user=root --socket=" + \
                                 socket + ' -Bse"SELECT SERVICE_STATE ' \
                                          'FROM performance_schema.replication_connection_status' \
                                          " where channel_name='" + channel + "'" + '" 2>&1'
            if self.debug == 'YES':
                print(check_slave_status)
            check_slave_status = os.popen(check_slave_status).read().rstrip()
        if check_slave_status != 'ON':
            self.check_testcase(1, node + ": IO thread slave status")
            print("\tERROR!: Slave IO thread is not running, check slave status")
            exit(1)
        else:
            self.check_testcase(0, node + ": IO thread slave status")

    def replication_sql_status(self, basedir, socket, node, channel):
        """ This will check replication SQL thread
            running status
        """
        if channel == 'none':
            channel = ""  # channel name is to identify the replication source
        # Get slave status
        version = self.version_check(basedir)
        if int(version) < int("050700"):
            sql_status = basedir + "/bin/mysql --user=root --socket=" + \
                         socket + ' -Bse"SHOW SLAVE STATUS\G" 2>&1 ' \
                                  '| grep "Slave_SQL_Running:" ' \
                                  "| awk '{ print $2 }'"
            if self.debug == 'YES':
                print(sql_status)
            sql_status = os.popen(sql_status).read().rstrip()
            if sql_status == "Yes":
                check_slave_status = 'ON'
            else:
                check_slave_status = 'OFF'
        else:
            check_slave_status = basedir + "/bin/mysql --user=root --socket=" + \
                                 socket + ' -Bse"SELECT SERVICE_STATE ' \
                                          'FROM performance_schema.replication_applier_status' \
                                          " where channel_name='" + channel + "'" + '" 2>&1'
            if self.debug == 'YES':
                print(check_slave_status)
            check_slave_status = os.popen(check_slave_status).read().rstrip()
        if check_slave_status != 'ON':
            self.check_testcase(1, node + ": SQL thread slave status")
            print("\tERROR!: Slave SQL thread is not running, check slave status")
            exit(1)
        else:
            self.check_testcase(0, node + ": SQL thread slave status")

    def invoke_replication(self, basedir, master_socket, slave_socket, repl_mode, comment):
        """ This method will invoke replication.
        :param basedir: PXC/PS base directory
        :param master_socket: Master Server socket
        :param slave_socket: Slave server socket
        :param repl_mode: Three mode will support now
                          GTID : GTID replication
                          NON-GTID : Non GTID replication
                          backup_slave : This will start replication
                                         from XB backup and it uses
                                         non-gtid replication
        :param comment: Replication channel details
        """
        if comment == 'none':
            comment = ""  # channel name is to identify the replication source
        # Setup async replication
        flush_log = basedir + "/bin/mysql --user=root --socket=" + \
            master_socket + ' -Bse "flush logs" 2>&1'
        if self.debug == 'YES':
            print(flush_log)
        os.system(flush_log)
        if repl_mode == 'backup_slave':
            data_dir = basedir + "/bin/mysql --user=root --socket=" + \
                       slave_socket + " -Bse 'select @@datadir';"
            if self.debug == 'YES':
                print(data_dir)
            data_dir = os.popen(data_dir).read().rstrip()
            query = "cat " + data_dir + "xtrabackup_binlog_pos_innodb | awk '{print $1}'"
            master_log_file = os.popen(query).read().rstrip()
            query = "cat " + data_dir + "xtrabackup_binlog_pos_innodb | awk '{print $2}'"
            master_log_pos = os.popen(query).read().rstrip()
        else:
            master_log_file = basedir + "/bin/mysql --user=root --socket=" + \
                              master_socket + \
                              " -Bse 'show master logs' | awk '{print $1}' | tail -1 2>&1"
            if self.debug == 'YES':
                print(master_log_file)
            master_log_file = os.popen(master_log_file).read().rstrip()
            master_log_pos = 4

        master_port = basedir + "/bin/mysql --user=root --socket=" + \
                      master_socket + \
                      ' -Bse "select @@port" 2>&1'
        master_port = os.popen(master_port).read().rstrip()
        if repl_mode == 'GTID':
            invoke_slave = basedir + "/bin/mysql --user=root --socket=" + \
                           slave_socket + ' -Bse"CHANGE MASTER TO MASTER_HOST=' + \
                           "'127.0.0.1', MASTER_PORT=" + master_port + ", MASTER_USER='root'" + \
                           ", MASTER_AUTO_POSITION=1 " + comment + ' ; START SLAVE;" 2>&1'
        else:
            invoke_slave = basedir + "/bin/mysql --user=root --socket=" + \
                           slave_socket + ' -Bse"CHANGE MASTER TO MASTER_HOST=' + \
                           "'127.0.0.1', MASTER_PORT=" + master_port + ", MASTER_USER='root'" + \
                           ", MASTER_LOG_FILE='" + master_log_file + "'" + \
                           ', MASTER_LOG_POS=' + str(master_log_pos) + ' ' \
                           + comment + ';START SLAVE;" 2>&1'
        if self.debug == 'YES':
            print(invoke_slave)
        result = os.system(invoke_slave)
        self.check_testcase(result, "Initiated replication")

    def start_pxc(self, parent_dir, workdir, basedir, node, socket, user, encryption, my_extra):
        # Start PXC cluster
        dbconnection_check = db_connection.DbConnection(user, socket)
        server_startup = pxc_startup.StartCluster(parent_dir, workdir, basedir, int(node), self.debug)
        result = server_startup.sanity_check()
        self.check_testcase(result, "Startup sanity check")
        if encryption == 'YES':
            result = server_startup.create_config('encryption')
            self.check_testcase(result, "Configuration file creation")
        else:
            result = server_startup.create_config('none')
            self.check_testcase(result, "Configuration file creation")
        result = server_startup.initialize_cluster()
        self.check_testcase(result, "Initializing cluster")
        result = server_startup.start_cluster('--max-connections=1500 ' + my_extra)
        self.check_testcase(result, "Cluster startup")
        result = dbconnection_check.connection_check()
        self.check_testcase(result, "Database connection")

    def start_ps(self, parent_dir, workdir, basedir, node, socket, user, encryption, my_extra):
        """ Start Percona Server. This method will
            perform sanity checks for PS startup
        """
        # Start PXC cluster for replication test
        dbconnection_check = db_connection.DbConnection(user, socket)
        server_startup = ps_startup.StartPerconaServer(parent_dir, workdir, basedir, int(node))
        result = server_startup.sanity_check()
        self.check_testcase(result, "PS: Startup sanity check")
        if encryption == 'YES':
            result = server_startup.create_config('encryption')
            self.check_testcase(result, "PS: Configuration file creation")
        else:
            result = server_startup.create_config()
            self.check_testcase(result, "PS: Configuration file creation")
        result = server_startup.initialize_cluster()
        self.check_testcase(result, "PS: Initializing cluster")
        result = server_startup.start_server('--max-connections=1500 ' + my_extra)
        self.check_testcase(result, "PS: Cluster startup")
        result = dbconnection_check.connection_check()
        self.check_testcase(result, "PS: Database connection")

    def stop_pxc(self, workdir, basedir, node):
        # Stop PXC cluster
        for i in range(int(node), 0, -1):
            shutdown_node = basedir + '/bin/mysqladmin --user=root --socket=' + \
                            workdir + '/node' + str(i) + '/mysql.sock shutdown > /dev/null 2>&1'
            if self.debug == 'YES':
                print(shutdown_node)
            result = os.system(shutdown_node)
            self.check_testcase(result, "PXC: shutting down cluster node" + str(i))

    def stop_ps(self, workdir, basedir, node):
        # Stop Percona Server
        for i in range(int(node), 0, -1):
            shutdown_node = basedir + '/bin/mysqladmin --user=root --socket=/tmp/psnode' + \
                            str(i) + '.sock shutdown > /dev/null 2>&1'
            if self.debug == 'YES':
                print(shutdown_node)
            result = os.system(shutdown_node)
            self.check_testcase(result, "PS: shutting down cluster node" + str(i))

    def pxc_startup_check(self, basedir, workdir, cluster_node):
        """ This method will check the node
            startup status.
        """
        query_cluster_status = basedir + '/bin/mysql --user=root --socket=' + \
            workdir + '/node' + str(cluster_node) + \
            '/mysql.sock -Bse"show status like \'wsrep_local_state_comment\';"' \
            ' 2>/dev/null | awk \'{print $2}\''
        ping_query = basedir + '/bin/mysqladmin --user=root --socket=' + \
            workdir + '/node' + str(cluster_node) + \
            '/mysql.sock ping > /dev/null 2>&1'
        for startup_timer in range(300):
            time.sleep(1)
            cluster_status = os.popen(query_cluster_status).read().rstrip()
            if cluster_status == 'Synced':
                self.check_testcase(0, "Node startup is successful")
                break
            if startup_timer > 298:
                self.check_testcase(0, "Warning! Node is not synced with cluster. "
                                       "Check the error log to get more info")
                ping_check = subprocess.call(ping_query, shell=True, stderr=subprocess.DEVNULL)
                ping_status = ("{}".format(ping_check))
                if int(ping_status) == 0:
                    self.check_testcase(int(ping_status), "Node startup is successful "
                                                          "(Node status:" + cluster_status + ")")
                    break  # break the loop if mysqld is running

    def node_joiner(self, workdir, basedir, donor_node, joiner_node):
        # Add new node to existing cluster
        donor = 'node' + donor_node     # Donor node
        joiner = 'node' + joiner_node   # Joiner node
        shutil.copy(workdir + '/conf/' + donor + '.cnf',
                    workdir + '/conf/' + joiner + '.cnf')
        query = basedir + '/bin/mysql --user=root --socket=' + workdir + '/node' + donor_node + \
            '/mysql.sock -Bse"show variables like \'wsrep_cluster_address\';"' \
            ' 2>/dev/null | awk \'{print $2}\''
        wsrep_cluster_addr = os.popen(query).read().rstrip()    # Get cluster address
        query = basedir + "/bin/mysql --user=root --socket=" + \
            workdir + '/node' + donor_node + '/mysql.sock -Bse"select @@port" 2>&1'
        port_no = os.popen(query).read().rstrip()   # Port number from Donor
        wsrep_port_no = int(port_no) + 108          # New wsrep port number
        port_no = int(port_no) + 100                # New Joiner port number
        
        # Create new cnf for joiner
        os.system("sed -i 's#" + donor + "#" + joiner + "#g' " + workdir +
                  '/conf/' + joiner + '.cnf')
        os.system("sed -i '/wsrep_sst_auth=root:/d' " + workdir +
                  '/conf/' + joiner + '.cnf')
        os.system("sed -i  '0,/^[ \\t]*wsrep_cluster_address[ \\t]*=.*$/s|"
                  "^[ \\t]*wsrep_cluster_address[ \\t]*=.*$|wsrep_cluster_address="
                  + wsrep_cluster_addr + "127.0.0.1:" + str(wsrep_port_no) + "|' "
                  + workdir + '/conf/' + joiner + '.cnf')
        os.system("sed -i  '0,/^[ \\t]*port[ \\t]*=.*$/s|"
                  "^[ \\t]*port[ \\t]*=.*$|port="
                  + str(port_no) + "|' " + workdir + '/conf/' + joiner + '.cnf')
        os.system('sed -i  "0,/^[ \\t]*wsrep_provider_options[ \\t]*=.*$/s|'
                  "^[ \\t]*wsrep_provider_options[ \\t]*=.*$|wsrep_provider_options="
                  "'gmcast.listen_addr=tcp://127.0.0.1:" + 
                  str(wsrep_port_no) + "'"
                  '|" ' + workdir + '/conf/' + joiner + '.cnf')
        os.system("sed -i  '0,/^[ \\t]*server_id[ \\t]*=.*$/s|"
                  "^[ \\t]*server_id[ \\t]*=.*$|server_id="
                  "14|' " + workdir + '/conf/' + joiner + '.cnf')

        # Create startup script for joiner.
        shutil.copy(workdir + '/log/startup' + donor_node + '.sh',
                    workdir + '/log/startup' + joiner_node + '.sh')
        os.system("sed -i 's#" + donor + "#" + joiner + "#g' " + workdir +
                  '/log/startup' + joiner_node + '.sh')
        os.system("rm -rf " + workdir + '/' + joiner)
        os.mkdir(workdir + '/' + joiner)
        joiner_startup = "bash " + workdir + \
                         '/log/startup' + joiner_node + '.sh'
        if self.debug == 'YES':
            print(joiner_startup)
        # Invoke joiner
        result = os.system(joiner_startup)
        self.check_testcase(result, "Starting cluster " + joiner)
        self.pxc_startup_check(basedir, workdir, joiner_node)
