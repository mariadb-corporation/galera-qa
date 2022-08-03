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
from util import galera_startup
from util import md_startup


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
                                          "| grep -oe '10\.[1-9][0]*' | head -n1").read()
        version = "{:02d}{:02d}".format(int(version_info.split('.')[0]),
                                        int(version_info.split('.')[1]))
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

    def check_gtid_consistency(self, basedir, socket1, socket2):
        """ Compare the table count between two nodes
        """
        query = basedir + '/bin/mysql -uroot --socket=' + \
            socket1 + ' -Bse"SELECT @@gtid_binlog_state;"'
        gtid_binlog_state_1 = os.popen(query).read().rstrip()
        if self.debug == 'YES':
            print(query)
            print('GTID binlog state ' + gtid_binlog_state_1)
        query = basedir + '/bin/mysql -uroot --socket=' + \
            socket2 + ' -Bse"SELECT @@gtid_binlog_state;"'
        gtid_binlog_state_2 = os.popen(query).read().rstrip()
        if self.debug == 'YES':
            print(query)
            print('GTID binlog state ' + gtid_binlog_state_2)
        if gtid_binlog_state_1 == gtid_binlog_state_2:
            return 0
        else:
            print("\tGTID binlog state is different")
            print("Node1 GTID binlog state:" + gtid_binlog_state_1 +
                  " , Node2 GTID binlog state:" + gtid_binlog_state_2)
            return 1

    def check_table_count(self, basedir, db, socket1, socket2):
        """ Compare the table count between two nodes
        """
        query = basedir + '/bin/mysql -uroot ' + db + ' --socket=' + \
                socket1 + ' -Bse"show tables;"'
        tables = os.popen(query).read().rstrip()
        # Compare the table checksum between node1 and node2
        for table in tables.split('\n'):
            query = basedir + '/bin/mysql -uroot --socket=' + \
                socket1 + ' -Bse"checksum table ' + \
                db + '.' + table + ';"'
            table_count_node1 = os.popen(query).read().rstrip()
            if self.debug == 'YES':
                print(query)
                print('Table count ' + table_count_node1)
            query = basedir + '/bin/mysql -uroot --socket=' + \
                socket2 + ' -Bse"checksum table ' + \
                db + '.' + table + ';"'
            table_count_node2 = os.popen(query).read().rstrip()
            if self.debug == 'YES':
                print(query)
                print('Table count ' + table_count_node2)
            if table_count_node1 == table_count_node2:
                return 0
            else:
                print("\tTable(" + db + '.' + table + " ) checksum is different")
                return 1

    def pxb_sanity_check(self, basedir, workdir, socket):
        """ Check pxb installation and cleanup backup directory
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
        create_user = basedir + "/bin/mysql --user=root "
        "--socket=" + socket + ' -e"create user xbuser'
        "@'localhost' identified by 'test"
        "';grant all on *.* to xbuser@'localhost'"
        ';" > /dev/null 2>&1'
        if self.debug == 'YES':
            print(create_user)
        query_status = os.system(create_user)
        if int(query_status) != 0:
            print("ERROR!: Could not create xtrabackup user user : xbuser")
            exit(1)

    def pxb_backup(self, workdir, source_datadir, socket, encryption, dest_datadir=None):
        """ Backup PXC/PS data directory with the help of xtrabackup.
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

    def replication_io_status(self, basedir, socket, node, comment, channel_name):
        """ This will check replication IO thread
            running status
        """
        if comment == 'msr':
            io_status = basedir + "/bin/mysql --user=root --socket=" + \
                 socket + " -Bse\"SHOW SLAVE '" + channel_name + "' STATUS\G\" 2>&1 " \
                 '| grep "Slave_IO_Running:" ' \
                 "| awk '{ print $2 }'"
        else:
            io_status = basedir + "/bin/mysql --user=root --socket=" + \
                 socket + " -Bse\"SHOW SLAVE STATUS\G\" 2>&1 " \
                 '| grep "Slave_IO_Running:" ' \
                 "| awk '{ print $2 }'"

        if self.debug == 'YES':
            print(io_status)
        io_status = os.popen(io_status).read().rstrip()
        if io_status == "Yes":
            check_slave_status = 'ON'
        else:
            check_slave_status = 'OFF'

        if check_slave_status != 'ON':
            self.check_testcase(1, node + ": IO thread slave status")
            print("\tERROR!: Slave IO thread is not running, check slave status")
            exit(1)
        else:
            self.check_testcase(0, node + ": IO thread slave status")

    def replication_sql_status(self, basedir, socket, node, comment, channel_name):
        """ This will check replication SQL thread
            running status
        """
        if comment == 'msr':
            sql_status = basedir + "/bin/mysql --user=root --socket=" + \
                socket + " -Bse\"SHOW SLAVE '" + channel_name + "' STATUS\G\" 2>&1 " \
                '| grep "Slave_SQL_Running:" ' \
                "| awk '{ print $2 }'"
        else:
            sql_status = basedir + "/bin/mysql --user=root --socket=" + \
                socket + " -Bse\"SHOW SLAVE STATUS\G\" 2>&1 " \
                '| grep "Slave_SQL_Running:" ' \
                "| awk '{ print $2 }'"

        if self.debug == 'YES':
            print(sql_status)
        sql_status = os.popen(sql_status).read().rstrip()
        if sql_status == "Yes":
            check_slave_status = 'ON'
        else:
            check_slave_status = 'OFF'

        if check_slave_status != 'ON':
            self.check_testcase(1, node + ": SQL thread slave status")
            print("\tERROR!: Slave SQL thread is not running, check slave status")
            exit(1)
        else:
            self.check_testcase(0, node + ": SQL thread slave status")

    def rpl_flush_log(self, basedir, socket):
        # Run FLUSH LOGS command in given server
        flush_log = basedir + "/bin/mysql --user=root --socket=" + \
            socket + ' -Bse "flush logs" 2>&1'
        if self.debug == 'YES':
            print(flush_log)
        os.system(flush_log)

    def rpl_master_log_file(self, basedir, socket):
        # get latest master log file from the server
        master_log_file = basedir + "/bin/mysql --user=root --socket=" + \
            socket + " -Bse 'show master logs' | awk '{print $1}' | tail -1 2>&1"
        if self.debug == 'YES':
            print(master_log_file)
        return os.popen(master_log_file).read().rstrip()

    def rpl_master_log_pos(self, basedir, socket):
        # get latest master log position from the server
        master_log_pos = basedir + "/bin/mysql --user=root --socket=" + \
            socket + " -Bse 'show master logs' | awk '{print $2}' | tail -1 2>&1"
        if self.debug == 'YES':
            print(master_log_pos)
        return os.popen(master_log_pos).read().rstrip()

    def get_port(self, basedir, socket):
        # get the port from the server
        server_port = basedir + "/bin/mysql --user=root --socket=" + \
            socket + ' -Bse "select @@port" 2>&1'
        if self.debug == 'YES':
            print(server_port)
        return os.popen(server_port).read().rstrip()

    def rpl_binlog_gtid_pos(self, basedir, socket, master_log_file, master_log_pos):
        binlog_gtid_pos = basedir + "/bin/mysql --user=root --socket=" + \
            socket + " -Bse \"select binlog_gtid_pos('" + master_log_file + \
            "'," + master_log_pos + ")\" | awk '{print $1}' | tail -1 2>&1"
        if self.debug == 'YES':
            print(binlog_gtid_pos)
        return os.popen(binlog_gtid_pos).read().rstrip()

    def invoke_replication(self, basedir, master_socket, slave_socket, repl_mode, comment):
        """ This method will invoke replication.
        :param basedir: MariaDB Galera Cluster/Server base directory
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
        # flush logs
        self.rpl_flush_log(basedir, master_socket)
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
            # get master log file and position
            master_log_file = self.rpl_master_log_file(basedir, master_socket)
            master_log_pos = self.rpl_master_log_pos(basedir, master_socket)

        # get master port number
        master_port = self.get_port(basedir, master_socket)
        if repl_mode == 'GTID':
            binlog_gtid_pos = basedir + "/bin/mysql --user=root --socket=" + \
                              master_socket + " -Bse \"select binlog_gtid_pos('" + master_log_file + \
                              "'," + master_log_pos + ")\" | awk '{print $1}' | tail -1 2>&1"
            if self.debug == 'YES':
                print(binlog_gtid_pos)
            binlog_gtid_pos = os.popen(binlog_gtid_pos).read().rstrip()
            apply_gtid_slave_pos = basedir + "/bin/mysql --user=root --socket=" + \
                slave_socket + " -Bse\"set global gtid_slave_pos='" + binlog_gtid_pos + "';\" 2>&1"
            if self.debug == 'YES':
                print(apply_gtid_slave_pos)
            #result = os.system(apply_gtid_slave_pos)
            #self.check_testcase(result, "Updated GTID slave position")
            invoke_slave = basedir + "/bin/mysql --user=root --socket=" + \
                slave_socket + " -Bse\"CHANGE MASTER " + comment + " TO MASTER_HOST=" + \
                "'127.0.0.1', MASTER_PORT=" + master_port + ", MASTER_USER='root'" + \
                ", MASTER_USE_GTID=slave_pos ; START SLAVE " + comment + ";\" 2>&1"
        else:
            invoke_slave = basedir + "/bin/mysql --user=root --socket=" + \
               slave_socket + " -Bse\"CHANGE MASTER " + comment + " TO MASTER_HOST=" + \
               "'127.0.0.1', MASTER_PORT=" + master_port + ", MASTER_USER='root'" + \
               ", MASTER_LOG_FILE='" + master_log_file + "'" + \
               ', MASTER_LOG_POS=' + str(master_log_pos) + ' ' \
               ";START SLAVE " + comment + ";\" 2>&1"
        if self.debug == 'YES':
            print(invoke_slave)
        result = os.system(invoke_slave)
        self.check_testcase(result, "Initiated replication")

    def change_master(self,basedir, socket, port, log_file, log_position , repl_mode, comment):
        """ This method will replication.
        :param basedir: MariaDB Galera Cluster/Server base directory
        :param socket: Replication Server socket
        :param port: Master port number
        :param log_file: Master log file name
        :param log_position : Master log file position
        :param repl_mode: Two modes
                          GTID : GTID replication
                          NON-GTID : Non GTID replication
        :param comment: Replication channel details
        """
        if repl_mode == "GTID":
            log_pos = "MASTER_USE_GTID=slave_pos"
        else:
            log_pos = "MASTER_LOG_POS=" + str(log_position)

        invoke_replication = basedir + "/bin/mysql --user=root --socket=" + \
            socket + " -Bse\"CHANGE MASTER " + comment + " TO MASTER_HOST=" + \
            "'127.0.0.1', MASTER_PORT=" + port + ", MASTER_USER='root'" + \
            ", MASTER_LOG_FILE='" + log_file + "', " + str(log_pos) + \
            " ;START SLAVE " + comment + ";\" 2>&1"
        if self.debug == 'YES':
            print(invoke_replication)
        result = os.system(invoke_replication)
        self.check_testcase(result, "Initiated replication")

    def invoke_master_master_replication(self, basedir, master_socket, slave_socket, repl_mode, comment):
        """ This method will invoke master master replication.
        :param basedir: MariaDB Galera Cluster/Server base directory
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
        if comment == 'none' or comment == 'master_master':
            comment = ""  # channel name is to identify the replication source
        # Setup async replication
        # flush logs
        self.rpl_flush_log(basedir, master_socket)
        # get master log file, position and port number
        master_log_file = self.rpl_master_log_file(basedir, master_socket)
        master_log_pos = self.rpl_master_log_file(basedir, master_socket)
        master_port = self.get_port(basedir, master_socket)
        self.change_master(basedir, slave_socket, master_port, master_log_file, master_log_pos, repl_mode, comment)
        # flush logs
        self.rpl_flush_log(basedir, slave_socket)
        # get master log file, position and port number
        master_log_file = self.rpl_master_log_file(basedir, slave_socket)
        master_log_pos = self.rpl_master_log_file(basedir, slave_socket)
        master_port = self.get_port(basedir, slave_socket)
        self.change_master(basedir, master_socket, master_port, master_log_file, master_log_pos, repl_mode, comment)

    def invoke_msr_replication(self, basedir, master1_socket, master2_socket, slave_socket, repl_mode):
        # Setup async replication
        self.rpl_flush_log(basedir, master1_socket)
        self.rpl_flush_log(basedir, master2_socket)
        master1_log_file = self.rpl_master_log_file(basedir, master1_socket)
        master2_log_file = self.rpl_master_log_file(basedir, master2_socket)
        master1_log_pos = self.rpl_master_log_pos(basedir, master1_socket)
        master2_log_pos = self.rpl_master_log_pos(basedir, master2_socket)
        master1_port = self.get_port(basedir, master1_socket)
        master2_port = self.get_port(basedir, master2_socket)

        if repl_mode == 'GTID':
            binlog1_gtid_pos = self.rpl_binlog_gtid_pos(basedir, master1_socket, master1_log_file, master1_log_pos)
            binlog2_gtid_pos = self.rpl_binlog_gtid_pos(basedir, master2_socket, master2_log_file, master2_log_pos)
            apply_gtid_slave_pos = basedir + "/bin/mysql --user=root --socket=" + \
                slave_socket + " -Bse\"set global gtid_slave_pos='" + binlog1_gtid_pos + \
                "," + binlog2_gtid_pos + "';\" 2>&1"
            if self.debug == 'YES':
                print(apply_gtid_slave_pos)
            result = os.system(apply_gtid_slave_pos)
            self.check_testcase(result, "Updated GTID slave position")
            invoke_slave = basedir + "/bin/mysql --user=root --socket=" + \
                slave_socket + " -Bse\"CHANGE MASTER 'master1' TO MASTER_HOST=" + \
                "'127.0.0.1', MASTER_PORT=" + master1_port + ", MASTER_USER='root'" + \
                ", MASTER_USE_GTID=slave_pos ; CHANGE MASTER 'master2' TO MASTER_HOST=" + \
                "'127.0.0.1', MASTER_PORT=" + master2_port + ", MASTER_USER='root'" + \
                ", MASTER_USE_GTID=slave_pos ; START SLAVE 'master1'; START SLAVE 'master2';\" 2>&1"
        else:
            invoke_slave = basedir + "/bin/mysql --user=root --socket=" + \
               slave_socket + " -Bse\"CHANGE MASTER 'master1' TO MASTER_HOST=" + \
               "'127.0.0.1', MASTER_PORT=" + master1_port + ", MASTER_USER='root'" + \
               ", MASTER_LOG_FILE='" + master1_log_file + "'" + \
               ', MASTER_LOG_POS=' + str(master1_log_pos) + ' ' \
               ";CHANGE MASTER 'master2' TO MASTER_HOST=" + \
               "'127.0.0.1', MASTER_PORT=" + master2_port + ", MASTER_USER='root'" + \
               ", MASTER_LOG_FILE='" + master2_log_file + "'" + \
               ', MASTER_LOG_POS=' + str(master2_log_pos) + ' ' \
               ";START SLAVE 'master1';START SLAVE 'master2';\" 2>&1"
        if self.debug == 'YES':
            print(invoke_slave)
        result = os.system(invoke_slave)
        self.check_testcase(result, "Initiated replication from master1 and master2")

    def start_galera(self, parent_dir, workdir, basedir, node, socket, user, encryption, my_extra):
        # Start MariaDB Galera cluster
        dbconnection_check = db_connection.DbConnection(user, socket)
        server_startup = galera_startup.StartCluster(parent_dir, workdir, basedir, int(node), self.debug)
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

    def start_md(self, parent_dir, workdir, basedir, node, socket, user, encryption, my_extra):
        """ Start MariaDB Server. This method will
            perform sanity checks for PS startup
        """
        # Start MariaDB Galera cluster for replication test
        dbconnection_check = db_connection.DbConnection(user, socket)
        server_startup = md_startup.StartPerconaServer(parent_dir, workdir, basedir, int(node))
        result = server_startup.sanity_check()
        self.check_testcase(result, "MD: Startup sanity check")
        if encryption == 'YES':
            result = server_startup.create_config('encryption')
            self.check_testcase(result, "MD: Configuration file creation")
        else:
            result = server_startup.create_config()
            self.check_testcase(result, "MD: Configuration file creation")
        result = server_startup.initialize_cluster()
        self.check_testcase(result, "MD: Initializing cluster")
        result = server_startup.start_server('--max-connections=1500 ' + my_extra)
        self.check_testcase(result, "MD: Cluster startup")
        result = dbconnection_check.connection_check()
        self.check_testcase(result, "MD: Database connection")

    def stop_galera(self, workdir, basedir, node):
        # Stop MariaDB Galera cluster
        for i in range(int(node), 0, -1):
            shutdown_node = basedir + '/bin/mysqladmin --user=root --socket=' + \
                            workdir + '/node' + str(i) + '/mysql.sock shutdown > /dev/null 2>&1'
            if self.debug == 'YES':
                print(shutdown_node)
            result = os.system(shutdown_node)
            self.check_testcase(result, "Galera: shutting down cluster node" + str(i))

    def stop_md(self, workdir, basedir, node):
        # Stop Percona Server
        for i in range(int(node), 0, -1):
            shutdown_node = basedir + '/bin/mysqladmin --user=root --socket=/tmp/mdnode' + \
                            str(i) + '.sock shutdown > /dev/null 2>&1'
            if self.debug == 'YES':
                print(shutdown_node)
            result = os.system(shutdown_node)
            self.check_testcase(result, "MD: shutting down MariaDB Server" + str(i))

    def galera_startup_check(self, basedir, workdir, cluster_node):
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
        donor = 'node' + donor_node  # Donor node
        joiner = 'node' + joiner_node  # Joiner node
        shutil.copy(workdir + '/conf/' + donor + '.cnf',
                    workdir + '/conf/' + joiner + '.cnf')
        query = basedir + '/bin/mysql --user=root --socket=' + workdir + '/node' + donor_node + \
                '/mysql.sock -Bse"show variables like \'wsrep_cluster_address\';"' \
                ' 2>/dev/null | awk \'{print $2}\''
        wsrep_cluster_addr = os.popen(query).read().rstrip()  # Get cluster address
        query = basedir + "/bin/mysql --user=root --socket=" + \
                workdir + '/node' + donor_node + '/mysql.sock -Bse"select @@port" 2>&1'
        if self.debug == 'YES':
            print(query)
        port_no = os.popen(query).read().rstrip()  # Port number from Donor
        wsrep_port_no = int(port_no) + 108  # New wsrep port number
        port_no = int(port_no) + 100  # New Joiner port number

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
        self.galera_startup_check(basedir, workdir, joiner_node)

