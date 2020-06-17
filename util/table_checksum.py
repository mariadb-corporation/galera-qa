import os
from util import utility


class TableChecksum:
    def __init__(self, pt_basedir, basedir, workdir, node, socket, debug):
        self.pt_basedir = pt_basedir
        self.basedir = basedir
        self.workdir = workdir
        self.node = node
        self.socket = socket
        self.debug = debug
        self.utility_cmd = utility.Utility(debug)

    def run_query(self, query):
        query_status = os.system(query)
        if int(query_status) != 0:
            print("ERROR! Query execution failed: " + query)
            return 1
        return 0

    def sanity_check(self):
        """ Sanity check method will check
            the availability of pt-table-checksum
            binary file.
        """
        if not os.path.isfile(self.pt_basedir + '/bin/pt-table-checksum'):
            print('pt-table-checksum is missing in percona toolkit basedir')
            return 1

        version = self.utility_cmd.version_check(self.basedir)
        # Creating pt_user for database consistency check
        if int(version) < int("050700"):
            query = self.basedir + "/bin/mysql --user=root --socket=" + \
                self.socket + ' -e"create user ' \
                " pt_user@'localhost' identified by 'test';" \
                "grant all on *.* to pt_user@'localhost'" \
                ';" > /dev/null 2>&1'
        else:
            query = self.basedir + "/bin/mysql --user=root --socket=" + \
                self.socket + ' -e"create user if not exists' \
                " pt_user@'localhost' identified with " \
                " mysql_native_password by 'test';" \
                "grant all on *.* to pt_user@'localhost'" \
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
            port = self.basedir + "/bin/mysql --user=root " + \
                '--socket=' + self.workdir + '/node' + str(i) + '/mysql.sock' + \
                ' -Bse"select @@port" 2>&1'
            port = os.popen(port).read().rstrip()

            insert_query = self.basedir + "/bin/mysql --user=root " + \
                '--socket=' + self.socket + \
                ' -e"insert into percona.dsns (id,dsn) values (' + \
                str(i) + ",'h=127.0.0.1,P=" + str(port) + \
                ",u=pt_user,p=test');" \
                '"> /dev/null 2>&1'
            self.run_query(insert_query)
        return 0

    def error_status(self, error_code):
        # Checking pt-table-checksum error
        if error_code == "0":
            self.utility_cmd.check_testcase(0, "pt-table-checksum run status")
        elif error_code == "1":
            self.utility_cmd.check_testcase(1, "pt-table-checksum error code "
                                          ": A non-fatal error occurred")
        elif error_code == "2":
            self.utility_cmd.check_testcase(1, "pt-table-checksum error code "
                                          ": --pid file exists and the PID is running")
        elif error_code == "4":
            self.utility_cmd.check_testcase(1, "pt-table-checksum error code "
                                          ": Caught SIGHUP, SIGINT, SIGPIPE, or SIGTERM")
        elif error_code == "8":
            self.utility_cmd.check_testcase(1, "pt-table-checksum error code "
                                          ": No replicas or cluster nodes were found")
        elif error_code == "16":
            self.utility_cmd.check_testcase(1, "pt-table-checksum error code "
                                          ": At least one diff was found")
        elif error_code == "32":
            self.utility_cmd.check_testcase(1, "pt-table-checksum error code "
                                          ": At least one chunk was skipped")
        elif error_code == "64":
            self.utility_cmd.check_testcase(1, "pt-table-checksum error code "
                                          ": At least one table was skipped")
        else:
            self.utility_cmd.check_testcase(1, "pt-table-checksum error code "
                                          ": Fatal error occurred. Please"
                                          "check error log for more info")

    def data_consistency(self, database):
        """ Data consistency check
            method will compare the
            data between cluster nodes
        """
        port = self.basedir + "/bin/mysql --user=root --socket=" + \
            self.socket + ' -Bse"select @@port" 2>&1'
        port = os.popen(port).read().rstrip()
        version = self.utility_cmd.version_check(self.basedir)
        # Disable pxc_strict_mode for pt-table-checksum run
        if int(version) > int("050700"):
            query = self.basedir + "/bin/mysql --user=root --socket=" + \
                self.socket + ' -e"set global pxc_strict_mode=DISABLED;' \
                '" > /dev/null 2>&1'
            self.run_query(query)

        run_checksum = self.pt_basedir + "/bin/pt-table-checksum h=127.0.0.1,P=" + \
            str(port) + ",u=pt_user,p=test -d" + database + \
            " --recursion-method dsn=h=127.0.0.1,P=" + str(port) + \
            ",u=pt_user,p=test,D=percona,t=dsns >" + self.workdir + "/log/pt-table-checksum.log 2>&1; echo $?"
        checksum_status = os.popen(run_checksum).read().rstrip()
        self.error_status(checksum_status)
        if int(version) > int("050700"):
            # Enable pxc_strict_mode after pt-table-checksum run
            query = self.basedir + "/bin/mysql --user=root --socket=" + \
                self.socket + ' -e"set global pxc_strict_mode=ENFORCING;' \
                '" > /dev/null 2>&1'
            self.run_query(query)
        return 0
