#!/usr/bin/env python3.7
import os
import sys
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from util import pxc_startup
from util import db_connection
from util import sysbench_run
from util import utility
from util import createsql
import configparser

# Reading initial configuration
config = configparser.ConfigParser()
config.read(parent_dir + '/config.ini')
workdir = config['config']['workdir']
basedir = config['config']['basedir']
node = config['config']['node']
user = config['config']['user']
socket = config['config']['node1_socket']
pt_basedir = config['config']['pt_basedir']
sysbench_user = config['sysbench']['sysbench_user']
sysbench_pass = config['sysbench']['sysbench_pass']
sysbench_db = config['sysbench']['sysbench_db']
sysbench_threads = 10
sysbench_table_size = 1000
sysbench_run_time = 10
utility_cmd = utility.Utility()


class ConsistencyCheck:
    def __init__(self, basedir, workdir, user, socket, pt_basedir, node):
        self.workdir = workdir
        self.basedir = basedir
        self.user = user
        self.socket = socket
        self.pt_basedir = pt_basedir
        self.node = node

    def run_query(self, query):
        query_status = os.system(query)
        if int(query_status) != 0:
            return 1
            print("ERROR! Query execution failed: " + query)
            exit(1)
        return 0

    def start_pxc(self):
        # Start PXC cluster for replication test
        dbconnection_check = db_connection.DbConnection(user, '/tmp/node1.sock')
        server_startup = pxc_startup.StartCluster(parent_dir, workdir, basedir, int(node))
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "Startup sanity check")
        result = server_startup.create_config()
        utility_cmd.check_testcase(result, "Configuration file creation")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "Initializing cluster")
        result = server_startup.start_cluster()
        utility_cmd.check_testcase(result, "Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "Database connection")

    def sanity_check(self):
        """ Sanity check method will check
            the availability of pt-table-checksum
            binary file.
        """

        if os.path.isfile(self.pt_basedir + '/bin/pt-table-checksum'):
            pt_binary = self.pt_basedir + '/bin/pt-table-checksum'
        else:
            print('pt-table-checksum is missing in percona toolkit basedir')
            return 1
            exit(1)

        # Creating pt_user for database consistency check
        query = self.basedir + "/bin/mysql --user=root --socket=" + \
            self.socket + ' -e"create user if not exists' \
            " pt_user@'%' identified with " \
            " mysql_native_password by 'test';" \
            "grant all on *.* to pt_user@'%'" \
            ';" > /dev/null 2>&1'
        self.run_query(query)

        # Creating percona db for cluster data checksum
        query = self.basedir + "/bin/mysql --user=root --socket=" + \
            self.socket + ' -e"drop database if exists percona;' \
            'create database percona;' \
            'drop table if exists percona.dsns;' \
            'create table percona.dsns(id int,' \
            'parent_id int,dsn varchar(100), ' \
            'primary key(id));" > /dev/null 2>&1'
        self.run_query(query)

        for i in range(1, int(self.node) + 1):
            port = self.basedir + "/bin/mysql --user=root --socket=" + \
                "/tmp/node" + str(i) + ".sock" + \
                ' -Bse"select @@port" 2>&1'
            port = os.popen(port).read().rstrip()

            insert_query = self.basedir + "/bin/mysql --user=root --socket=" + \
                "/tmp/node" + str(i) + ".sock" + \
                ' -e"insert into percona.dsns (id,dsn) values (' + \
                str(i) + ",'h=127.0.0.1,P=" + str(port) + \
                ",u=pt_user,p=test');" \
                '"> /dev/null 2>&1'

            query_status = os.system(insert_query)
            if int(query_status) != 0:
                return 1
                print("ERROR!: Could not create percona toolkit user : pt_user")
                exit(1)
        return 0

    def sysbench_run(self, socket, db):
        sysbench = sysbench_run.SysbenchRun(basedir, workdir,
                                            sysbench_user, sysbench_pass,
                                            socket, sysbench_threads,
                                            sysbench_table_size, db,
                                            sysbench_threads, sysbench_run_time)

        result = sysbench.sanity_check()
        utility_cmd.check_testcase(result, "Replication QA sysbench run sanity check")
        result = sysbench.sysbench_load()
        utility_cmd.check_testcase(result, "Replication QA sysbench data load")

    def data_load(self, db, socket ):
        if os.path.isfile(parent_dir + '/util/createsql.py'):
            generate_sql = createsql.GenerateSQL('/tmp/dataload.sql', 1000)
            generate_sql.OutFile()
            generate_sql.CreateTable()
            sys.stdout = sys.__stdout__
            create_db = self.basedir + "/bin/mysql --user=root --socket=" + \
                socket + ' -Bse"drop database if exists ' + db + \
                ';create database ' + db + ';" 2>&1'
            result = os.system(create_db)
            utility_cmd.check_testcase(result, "Sample DB creation")
            data_load_query = self.basedir + "/bin/mysql --user=root --socket=" + \
                socket + ' ' + db + ' -f <  /tmp/dataload.sql >/dev/null 2>&1'
            result = os.system(data_load_query)
            utility_cmd.check_testcase(result, "Sample data load")

    def data_consistency(self, database):
        """ Data consistency check
            method will compare the
            data between cluster nodes
        """
        port = self.basedir + "/bin/mysql --user=root --socket=" + \
            self.socket + ' -Bse"select @@port" 2>&1'

        port = os.popen(port).read().rstrip()

        query = self.basedir + "/bin/mysql --user=root --socket=" + \
            self.socket + ' -e"set global pxc_strict_mode=DISABLED;" > /dev/null 2>&1'

        self.run_query(query)

        run_checksum = self.pt_basedir + "/bin/pt-table-checksum h=127.0.0.1,P=" + \
            str(port) + ",u=pt_user,p=test -d" + database + \
            " --recursion-method dsn=h=127.0.0.1,P=" + str(port) + \
            ",u=pt_user,p=test,D=percona,t=dsns >" + self.workdir + "/log/pt-table-checksum.log 2>&1"
        checksum_status = os.system(run_checksum)
        print("")
        utility_cmd.check_testcase(checksum_status, "pt-table-checksum run")
        query = self.basedir + "/bin/mysql --user=root --socket=" + \
            self.socket + ' -e"set global pxc_strict_mode=ENFORCING;" > /dev/null 2>&1'
        self.run_query(query)
        return 0


consistency_run = ConsistencyCheck(basedir, workdir, user, socket, pt_basedir, node)
consistency_run.start_pxc()
consistency_run.sysbench_run(socket, 'test')
consistency_run.sanity_check()
consistency_run.data_load('pxc_dataload_db', socket)
consistency_run.data_consistency('test,pxc_dataload_db')
