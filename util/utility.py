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
        if os.path.isfile(workdir + '/cert/ssl.cnf'):
            os.remove(workdir + '/cert/ssl.cnf')
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
