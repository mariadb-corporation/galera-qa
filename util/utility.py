from datetime import datetime
import os
import sys
import shutil
import subprocess
from distutils.spawn import find_executable


class Utility:
    def printit(self, text, status):
        now = datetime.now().strftime("%H:%M:%S ")
        print(now + ' ' + f'{text:100}' + '[ ' + status + ' ]')

    def check_testcase(self, result, testcase):
        if result == 0:
            self.printit(testcase, u'\u2714')
        else:
            self.printit(testcase, u'\u2718')

    def check_python_version(self):
        """ Check python version. Raise error if the
            version is 3.7 or greater
        """
        if sys.version_info < (3, 7):
            print("\nError! You should use python 3.7 or greater\n")
            exit(1)

    def version_check(self, basedir):
        # Get database version number
        version_info = os.popen(basedir +
                                "/bin/mysqld --version 2>&1 "
                                "| grep -oe '[0-9]\.[0-9][\.0-9]*' | head -n1").read()
        version = "{:02d}{:02d}{:02d}".format(int(version_info.split('.')[0]),
                                              int(version_info.split('.')[1]),
                                              int(version_info.split('.')[2]))
        return version

    def create_ssl_certificate(self, workdir):
        """ This will create SSL certificate
            to test SSL and encryption features
        """
        if os.path.exists(workdir + '/cert'):
            shutil.rmtree(workdir + '/cert')
            os.mkdir(workdir + '/cert')
        else:
            os.mkdir(workdir + '/cert')
        cwd = os.getcwd()
        os.chdir(workdir + '/cert')
        key_query = "openssl genrsa 2048 > ca-key.pem "
        subprocess.call(key_query, shell=True, stderr=subprocess.DEVNULL)
        key_query = "openssl req -new -x509 -nodes -days 3600 " \
                    "-key ca-key.pem -out ca.pem -subj" \
                    " '/CN=www.percona.com/O=Database Performance./C=US' "
        subprocess.call(key_query, shell=True, stderr=subprocess.DEVNULL)
        key_query = "openssl req -newkey rsa:2048 -days 3600 " \
                    "-nodes -keyout server-key.pem -out server-req.pem -subj " \
                    "'/CN=www.fb.com/O=Database Performance./C=AU' "
        subprocess.call(key_query, shell=True, stderr=subprocess.DEVNULL)
        key_query = "openssl rsa -in server-key.pem -out server-key.pem "
        subprocess.call(key_query, shell=True, stderr=subprocess.DEVNULL)
        key_query = "openssl x509 -req -in server-req.pem " \
                    "-days 3600 -CA ca.pem -CAkey ca-key.pem " \
                    "-set_serial 01 -out server-cert.pem "
        subprocess.call(key_query, shell=True, stderr=subprocess.DEVNULL)
        key_query = "openssl req -newkey rsa:2048 -days 3600 -nodes -keyout " \
                    "client-key.pem -out client-req.pem -subj " \
                    "'/CN=www.percona.com/O=Database Performance./C=IN' "
        subprocess.call(key_query, shell=True, stderr=subprocess.DEVNULL)
        key_query = "openssl rsa -in client-key.pem -out client-key.pem "
        subprocess.call(key_query, shell=True, stderr=subprocess.DEVNULL)
        key_query = "openssl x509 -req -in client-req.pem -days " \
                    "3600 -CA ca.pem -CAkey ca-key.pem " \
                    "-set_serial 01 -out client-cert.pem "
        subprocess.call(key_query, shell=True, stderr=subprocess.DEVNULL)
        if os.path.isfile(workdir + '/conf/ssl.cnf'):
            os.remove(workdir + '/conf/ssl.cnf')
        cnf_name = open(workdir + '/conf/ssl.cnf', 'a+')
        cnf_name.write('\n')
        cnf_name.write('[mysqld]\n')
        cnf_name.write('ssl-ca = ' + workdir + '/cert/ca.pem\n')
        cnf_name.write('ssl-cert = ' + workdir + '/cert/server-cert.pem\n')
        cnf_name.write('ssl-key = ' + workdir + '/cert/server-key.pem\n')
        cnf_name.write('[client]\n')
        cnf_name.write('ssl-ca = ' + workdir + '/cert/ca.pem\n')
        cnf_name.write('ssl-cert = ' + workdir + '/cert/client-cert.pem\n')
        cnf_name.write('ssl-key = ' + workdir + '/cert/client-key.pem\n')
        cnf_name.write('[sst]\n')
        cnf_name.write('encrypt = 4\n')
        cnf_name.write('ssl-ca = ' + workdir + '/cert/ca.pem\n')
        cnf_name.write('ssl-cert = ' + workdir + '/cert/server-cert.pem\n')
        cnf_name.write('ssl-key = ' + workdir + '/cert/server-key.pem\n')
        cnf_name.close()
        os.chdir(cwd)
        return 0

    def check_table_count(self, basedir, db, table, socket1, socket2):
        """ This method will compare the table
            count between two nodes
        """
        query = basedir + '/bin/mysql -uroot --socket=' + \
            socket1 + ' -Bse"checksum table ' + \
            db + '.' + table + ';"'
        table_count_node1 = os.popen(query).read().rstrip()
        query = basedir + '/bin/mysql -uroot --socket=' + \
            socket2 + ' -Bse"checksum table ' + \
            db + '.' + table + ';"'
        table_count_node2 = os.popen(query).read().rstrip()
        if table_count_node1 == table_count_node2:
            return 0
        else:
            return 1

    def pxb_sanity_check(self, workdir):
        """ This method will check pxb installation and
            cleanup backup directory
        """
        if find_executable('xtrabackup') is None:
            print('\tERROR! Percona Xtrabackup is not installed.')
            exit(1)
        if os.path.exists(workdir + '/backup'):
            shutil.rmtree(workdir + '/backup')
            os.mkdir(workdir + '/backup')
        else:
            os.mkdir(workdir + '/backup')

    def pxb_backup(self, workdir, source_datadir, socket, dest_datadir=None):
        """ This method will backup PXB/PS data directory
            with the help of xtrabackup.
        """
        backup_cmd = "xtrabackup --user=root --password='' --backup " \
                     "--target-dir=" + workdir + "/backup -S " + \
                     socket + " --datadir=" + source_datadir + " --lock-ddl >" + \
                     workdir + "/log/xb_backup.log 2>&1"
        os.system(backup_cmd)
        prepare_backup = "xtrabackup --prepare --target_dir=" + \
                         workdir + "/backup --lock-ddl >" + \
                         workdir + "/log/xb_backup_prepare.log 2>&1"
        os.system(prepare_backup)
        if dest_datadir is not None:
            copy_backup = "xtrabackup --copy-back --target-dir=" + \
                          workdir + "/backup --datadir=" + \
                          dest_datadir + " --lock-ddl >" + \
                          workdir + "/log/copy_backup.log 2>&1"
            os.system(copy_backup)

    def replication_io_status(self, basedir, socket, node, channel):
        """ This will check replication IO thread
            running status
        """
        if channel == 'none':
            channel = ""
        version = self.version_check(basedir)
        if int(version) < int("050700"):
            io_status = basedir + "/bin/mysql --user=root --socket=" + \
                         socket + ' -Bse"SHOW SLAVE STATUS\G" 2>&1 ' \
                                  '| grep "Slave_IO_Running:" ' \
                                  "| awk '{ print $2 }'"
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
            channel = ""
        version = self.version_check(basedir)
        if int(version) < int("050700"):
            sql_status = basedir + "/bin/mysql --user=root --socket=" + \
                                 socket + ' -Bse"SHOW SLAVE STATUS\G" 2>&1 ' \
                                 '| grep "Slave_SQL_Running:" ' \
                                 "| awk '{ print $2 }'"
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
            comment = ""
        # Setup async replication
        flush_log = basedir + "/bin/mysql --user=root --socket=" + \
            master_socket + \
            ' -Bse "flush logs" 2>&1'
        os.system(flush_log)
        if repl_mode == 'backup_slave':
            data_dir = basedir + "/bin/mysql --user=root --socket=" + \
                slave_socket + " -Bse 'select @@datadir';"
            data_dir = os.popen(data_dir).read().rstrip()
            query = "cat " + data_dir + "xtrabackup_binlog_pos_innodb | awk '{print $1}'"
            master_log_file = os.popen(query).read().rstrip()
            query = "cat " + data_dir + "xtrabackup_binlog_pos_innodb | awk '{print $2}'"
            master_log_pos = os.popen(query).read().rstrip()
        else:
            master_log_file = basedir + "/bin/mysql --user=root --socket=" + \
                master_socket + \
                " -Bse 'show master logs' | awk '{print $1}' | tail -1 2>&1"
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
        result = os.system(invoke_slave)
        self.check_testcase(result, "Initiated replication")

