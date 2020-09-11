#!/usr/bin/env python3
import os
import sys
import argparse
import random
import time
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from config import *
from util import pxc_startup
from util import db_connection
from util import sysbench_run
from util import utility

# Read argument
parser = argparse.ArgumentParser(prog='PXC chaosmonkey test', usage='%(prog)s [options]')
parser.add_argument('-e', '--encryption-run', action='store_true',
                    help='This option will enable encryption options')
parser.add_argument('-d', '--debug', action='store_true',
                    help='This option will enable debug logging')

args = parser.parse_args()
if args.encryption_run is True:
    encryption = 'YES'
else:
    encryption = 'NO'
if args.debug is True:
    debug = 'YES'
else:
    debug = 'NO'
# Initial configuration
node = '6'

utility_cmd = utility.Utility(debug)
utility_cmd.check_python_version()


class ChaosMonkeyQA:
    def startup(self):
        # Start PXC cluster for ChaosMonkey test
        dbconnection_check = db_connection.DbConnection(USER, WORKDIR + '/node1/mysql.sock')
        server_startup = pxc_startup.StartCluster(parent_dir, WORKDIR, BASEDIR, int(node), debug)
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "Startup sanity check")
        if encryption == 'YES':
            result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "Configuration file creation")
        else:
            result = server_startup.create_config('none')
            utility_cmd.check_testcase(result, "Configuration file creation")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "Initializing cluster")
        result = server_startup.start_cluster()
        utility_cmd.check_testcase(result, "Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "Database connection")

    def sysbench_run(self, socket, db):
        # Sysbench dataload for consistency test
        sysbench = sysbench_run.SysbenchRun(BASEDIR, WORKDIR,
                                            socket, debug)

        result = sysbench.sanity_check(db)
        utility_cmd.check_testcase(result, "Sysbench run sanity check")
        result = sysbench.sysbench_load(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS, SYSBENCH_NORMAL_TABLE_SIZE)
        utility_cmd.check_testcase(result, "Sysbench data load")
        if encryption == 'YES':
            for i in range(1, int(SYSBENCH_TABLE_COUNT) + 1):
                encrypt_table = BASEDIR + '/bin/mysql --user=root ' \
                    '--socket=' + socket + ' -e "' \
                    ' alter table ' + db + '.sbtest' + str(i) + \
                    " encryption='Y'" \
                    '"; > /dev/null 2>&1'
                if debug == 'YES':
                    print(encrypt_table)
                os.system(encrypt_table)
        result = sysbench.sysbench_oltp_read_write(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS,
                                                   SYSBENCH_NORMAL_TABLE_SIZE, SYSBENCH_RUN_TIME, 'Yes')
        utility_cmd.check_testcase(result, "Initiated sysbench oltp run")

    def multi_recovery_test(self):
        """ This method will kill 2 random nodes from
            6 node cluster while sysbench is in progress
            and check data consistency after restart.
        """
        nodes = [2, 3, 4, 5, 6]
        rand_nodes = random.choices(nodes, k=2)
        self.sysbench_run(WORKDIR + '/node1/mysql.sock', 'test')
        query = 'pidof sysbench'
        sysbench_pid = os.popen(query).read().rstrip()
        for j in rand_nodes:
            query = 'cat `' + BASEDIR + \
                    '/bin/mysql  --user=root --socket=' + WORKDIR + \
                        '/node' + str(j) + '/mysql.sock -Bse"select @@pid_file"  2>&1`'
            time.sleep(1)
            pid = os.popen(query).read().rstrip()
            if debug == 'YES':
                print("Terminating mysqld : " + 'kill -9 ' + pid)
            result = os.system('kill -9 ' + pid)
            utility_cmd.check_testcase(result, "Killed Cluster Node" + str(j) + " for ChaosMonkey QA")

        kill_sysbench = "kill -9 " + sysbench_pid
        if debug == 'YES':
            print("Terminating sysbench run : " + kill_sysbench)
        result = os.system(kill_sysbench)
        utility_cmd.check_testcase(result, "Killed sysbench oltp run")
        time.sleep(10)

        for j in rand_nodes:
            query = 'bash ' + WORKDIR + \
                    '/log/startup' + str(j) + '.sh'
            if debug == 'YES':
                print(query)
            result = os.system(query)
            utility_cmd.check_testcase(result, "Restarting Cluster Node" + str(j))
            time.sleep(5)


print("\nPXC ChaosMonkey Style test")
print("----------------------------")
chaosmonkey_qa = ChaosMonkeyQA()
chaosmonkey_qa.startup()
chaosmonkey_qa.multi_recovery_test()
version = utility_cmd.version_check(BASEDIR)
time.sleep(10)
result = utility_cmd.check_table_count(BASEDIR, 'test', WORKDIR + '/node1/mysql.sock',
                                       WORKDIR + '/node2/mysql.sock')
utility_cmd.check_testcase(result, "Checksum run for DB: test")
