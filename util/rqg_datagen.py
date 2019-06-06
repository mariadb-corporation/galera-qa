import os
import configparser
from util import utility


# Reading initial configuration
config = configparser.ConfigParser()
script_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(script_dir, '../'))
config.read(parent_dir + '/config.ini')
workdir = config['config']['workdir']
basedir = config['config']['basedir']
user = config['config']['user']
node1_socket = config['config']['node1_socket']

utility_cmd = utility.Utility()


class RQGDataGen:
    def __init__(self, basedir, workdir, module, user):
        self.basedir = basedir
        self.workdir = workdir
        self.module = parent_dir + '/randgen/conf/' + module
        self.user = user

    def initiate_rqg(self, db, socket):
        """ Method to initiate RQD data load against
            Percona XtraDB cluster.
        """
        master_port = self.basedir + "/bin/mysql --user=root --socket=" + socket + \
            ' -Bse"select @@port" 2>&1'
        port = os.popen(master_port).read().rstrip()
        create_db = self.basedir + "/bin/mysql --user=root --socket=" + socket + \
            ' -Bse"drop database if exists ' + db + \
            ';create database ' + db + ';" 2>&1'
        os.system(create_db)
        os.chdir(parent_dir + '/randgen')
        if not os.path.exists(self.module):
            print(self.module + ' does not exist in RQG')
            exit(1)
        for file in os.listdir(self.module):
            if file.endswith(".zz"):
                rqg_command = "perl " + parent_dir + "/randgen/gendata.pl " \
                              "--dsn=dbi:mysql:host=127.0.0.1:port=" \
                              + port + ":user=" + self.user + \
                              ":database=" + db + " --spec=" + \
                              self.module + '/' + file + " > " + \
                              self.workdir + "/log/rqg_run.log 2>&1"
                result = os.system(rqg_command)
                utility_cmd.check_testcase(result, "RQG data load")

