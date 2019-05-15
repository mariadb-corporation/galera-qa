import os
import time


class ConsistencyCheck:

    def __init__(self, basedir, workdir, user, password, socket, pt_basedir, database, node):
        self.workdir = workdir
        self.basedir = basedir
        self.user = user
        self.password = password
        self.socket = socket
        self.pt_basedir = pt_basedir
        self.database = database
        self.node = node

    def runquery(self, query):
        querystatus = os.system(query)
        if int(querystatus) != 0:
            return 1
            print("ERROR! Query execution failed: " + query)
            exit(1)
        return 0

    def sanitycheck(self):
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
        self.runquery(query)

        # Creating percona db for cluster data checksum
        query = self.basedir + "/bin/mysql --user=root --socket=" + \
            self.socket + ' -e"drop database if exists percona;' \
                                'create database percona;' \
                                'drop table if exists percona.dsns;' \
                                'create table percona.dsns(id int,' \
                                'parent_id int,dsn varchar(100), ' \
                                'primary key(id));" > /dev/null 2>&1'
        self.runquery(query)

        for i in range(1, int(self.node) + 1):
            getport = self.basedir + "/bin/mysql --user=root --socket=" + \
                "/tmp/node" + str(i) + ".sock" + \
                ' -Bse"select @@port" 2>&1'
            port = os.popen(getport).read().rstrip()

            insertquery = self.basedir + "/bin/mysql --user=root --socket=" + \
                "/tmp/node" + str(i) + ".sock" + \
                ' -e"insert into percona.dsns (id,dsn) values (' + \
                str(i) + ",'h=127.0.0.1,P=" + str(port) + \
                ",u=pt_user,p=test');" \
                '"> /dev/null 2>&1'

            querystatus = os.system(insertquery)
            if int(querystatus) != 0:
                return 1
                print("ERROR!: Could not create percona toolkit user : pt_user")
                exit(1)
        return 0

    def data_consistency(self):
        """ Data consistency check
            method will compare the
            data between cluster nodes
        """
        getport = self.basedir + "/bin/mysql --user=root --socket=" + \
            self.socket + ' -Bse"select @@port" 2>&1'

        port = os.popen(getport).read().rstrip()

        query = self.basedir + "/bin/mysql --user=root --socket=" + \
            self.socket + ' -e"set global pxc_strict_mode=DISABLED;" > /dev/null 2>&1'

        self.runquery(query)

        run_checksum = self.pt_basedir + "/bin/pt-table-checksum h=127.0.0.1,P=" + \
            str(port) + ",u=root -d" + self.database + \
            " --recursion-method dsn=h=127.0.0.1,P=" + \
            str(port) + ",u=root,D=percona,t=dsns >" + \
            self.workdir + "/log/pt-table-checksum.log 2>&1"
        time.sleep(5)
        checksumstatus = os.system(run_checksum)
        if int(checksumstatus) != 0:
            return 1
            print("ERROR!: Could not execute pt-table-checksum")
            exit(1)

        query = self.basedir + "/bin/mysql --user=root --socket=" + \
            self.socket + ' -e"set global pxc_strict_mode=ENFORCING;" > /dev/null 2>&1'

        self.runquery(query)
        return 0
