from datetime import datetime
import os
import shutil
import subprocess


class Utility:
    def printit(self, text, status):
        now = datetime.now().strftime("%H:%M:%S ")
        print(now + ' ' + f'{text:60}' + '[ ' + status + ' ]')

    def check_testcase(self, result, testcase):
        if result == 0:
            self.printit(testcase, u'\u2714')
        else:
            self.printit(testcase, u'\u2718')

    def create_ssl_certificate(self, workdir):
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

    def replication_io_status(self, basedir, socket, node, channel):
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

    def invoke_replication(self, basedir, master_socket, slave_socket, comment):
        # Setup async replication
        flush_log = basedir + "/bin/mysql --user=root --socket=" + \
            master_socket + \
            ' -Bse"flush logs" 2>&1'
        os.system(flush_log)
        master_log_file = basedir + "/bin/mysql --user=root --socket=" + \
            master_socket + \
            " -Bse'show master logs' | awk '{print $1}' | tail -1 2>&1"
        master_log_file = os.popen(master_log_file).read().rstrip()
        master_port = basedir + "/bin/mysql --user=root --socket=" + \
            master_socket + \
            ' -Bse"select @@port" 2>&1'
        master_port = os.popen(master_port).read().rstrip()
        invoke_slave = basedir + "/bin/mysql --user=root --socket=" + \
            slave_socket + ' -Bse"CHANGE MASTER TO MASTER_HOST=' + \
            "'127.0.0.1', MASTER_PORT=" + master_port + ", MASTER_USER='root'" + \
            ", MASTER_LOG_FILE='" + master_log_file + "'" + \
            ', MASTER_LOG_POS=4 ' + comment + ' ; START SLAVE;" 2>&1'
        result = os.system(invoke_slave)
        self.check_testcase(result, "Initiated replication")

