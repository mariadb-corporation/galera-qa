import os
import itertools
from util import utility
utility_cmd = utility.Utility()

class SysbenchRun:
    def __init__(self, basedir, workdir, scriptdir , user, password, socket):
        self.basedir = basedir
        self.workdir = workdir
        self.scriptdir = scriptdir
        self.user = user
        self.password = password
        self.socket = socket
        self.export_lua_path = 'export SBTEST_SCRIPTDIR="' + scriptdir + \
            '/sysbench_lua"; export LUA_PATH="' + scriptdir + \
            '/sysbench_lua/?;' + scriptdir + '/sysbench_lua/?.lua"'

    def sanity_check(self, db):
        # Sanity check for sysbench run
        check_sybench = os.system('which sysbench >/dev/null 2>&1')
        if check_sybench != 0:
            print("ERROR!: sysbench package is not installed")
            return 1

        query = self.basedir + "/bin/mysql --user=root --socket=" + \
            self.socket + " -e'drop database if exists " + \
            db + "; create database " + \
            db + ";' > /dev/null 2>&1"
        query_status = os.system(query)
        if int(query_status) != 0:
            #return 1
            print("ERROR!: Could not create sysbench test database(sbtest)")
            exit(1)
        version = utility_cmd.version_check(self.basedir)
        if int(version) < int("050700"):
            create_user = self.basedir + "/bin/mysql --user=root " \
                "--socket=" + self.socket + ' -e"create user ' + \
                self.user + "@'localhost' identified by '" + self.password + \
                "';grant all on *.* to " + self.user + "@'localhost'" \
                ';" > /dev/null 2>&1'
        else:
            create_user = self.basedir + "/bin/mysql --user=root --socket=" + \
                self.socket + ' -e"create user if not exists ' + \
                self.user + "@'localhost' identified with  mysql_native_password by '" + \
                self.password + "';grant all on *.* to " + self.user + "@'localhost'" \
                ';" > /dev/null 2>&1'
        query_status = os.system(create_user)
        if int(query_status) != 0:
            print("ERROR!: Could not create sysbench user : sysbench")
            return 1
        return 0

    def sysbench_load(self, db, tables, threads, table_size):
        # Sysbench data load
        query = self.export_lua_path + ";sysbench " + self.scriptdir + \
            "/sysbench_lua/oltp_insert.lua" \
            " --table-size=" + str(table_size) + \
            " --tables=" + str(tables) + \
            " --threads=" + str(threads) + \
            " --mysql-db=" + db + \
            " --mysql-user=" + self.user + \
            " --mysql-password=" + self.password + \
            " --mysql-socket=" + self.socket + \
            " --db-driver=mysql prepare >" + \
            self.workdir + "/log/sysbench_prepare.log"
        query_status = os.system(query)
        if int(query_status) != 0:
            print("ERROR!: sysbench data load run is failed")
            return 1
        return 0

    def sysbench_custom_load(self, db, table_count, thread, table_size):
        # Create sysbench table structure
        result = self.sysbench_load(db, table_count, table_count, 0)
        utility_cmd.check_testcase(result, "Sysbench data load")
        rand_types = ['uniform', 'gaussian', 'special', 'pareto']
        delete_inserts = [10, 20, 30, 40, 50]
        index_updates = [10, 20, 30, 40, 50]
        non_index_updates = [10, 20, 30, 40, 50]
        for rand_type, delete_insert, index_update, non_index_update in \
                itertools.product(rand_types, delete_inserts, index_updates, non_index_updates):
            query = self.export_lua_path + ";sysbench " + self.scriptdir + \
                "/sysbench_lua/oltp_read_write.lua" \
                " --table-size=" + str(table_size) + \
                " --tables=" + str(3) + \
                " --threads=" + str(thread) + \
                " --mysql-db=" + db + \
                " --mysql-user=" + self.user + \
                " --mysql-password=" + self.password + \
                " --mysql-socket=" + self.socket + \
                " --rand_type=" + rand_type + \
                " --delete_inserts=" + str(delete_insert) + \
                " --index_updates=" + str(index_update) + \
                " --non_index_updates=" + str(non_index_update) + \
                " --db-driver=mysql run >" + \
                self.workdir + "/log/sysbench_oltp_read_write.log"
            print(query)
            query_status = os.system(query)
            combination = "rand_type:" + rand_type + \
                          ", delete_inserts:" + str(delete_insert) + \
                          ",index_updates:" + str(index_update) + \
                          ", non_index_updates:" + str(non_index_update)
            if int(query_status) != 0:
                print("ERROR!: sysbench oltp(combination:" + combination + ") run is failed")
            else:
                utility_cmd.check_testcase(query_status, "Sysbench oltp(combination:" + combination + ") run")

    def sysbench_cleanup(self, db, tables, threads, table_size):
        # Sysbench data cleanup
        query = "sysbench /usr/share/sysbench/oltp_insert.lua" \
            " --table-size=" + str(table_size) + \
            " --tables=" + str(tables) + \
            " --threads=" + str(threads) + \
            " --mysql-db=" + db + \
            " --mysql-user=" + self.user + \
            " --mysql-password=" + self.password + \
            " --mysql-socket=" + self.socket + \
            " --db-driver=mysql cleanup >" + \
            self.workdir + "/log/sysbench_cleanup.log"
        query_status = os.system(query)
        if int(query_status) != 0:
            print("ERROR!: sysbench cleanup run is failed")
            return 1
        return 0

    def sysbench_oltp_read_write(self, db, tables, threads, table_size, time):
        # Sysbench OLTP read write run
        query = "sysbench /usr/share/sysbench/oltp_read_write.lua" \
            " --table-size=" + str(table_size) + \
            " --tables=" + str(tables) + \
            " --threads=" + str(threads) + \
            " --mysql-db=" + db + \
            " --mysql-user=" + self.user + \
            " --mysql-password=" + self.password + \
            " --mysql-socket=" + self.socket + \
            " --time=" + str(time) + \
            " --db-driver=mysql --db-ps-mode=disable run >" + \
            self.workdir + "/log/sysbench_read_write_" + str(threads) + ".log"
        query_status = os.system(query)
        if int(query_status) != 0:
            print("ERROR!: sysbench read write run is failed")
            return 1
        return 0

    def sysbench_oltp_read_only(self, db, tables, threads, table_size, time):
        # Sysbench OLTP read only run
        query = "sysbench /usr/share/sysbench/oltp_read_only.lua" \
            " --table-size=" + str(table_size) + \
            " --tables=" + str(tables) + \
            " --threads=" + str(threads) + \
            " --mysql-db=" + db + \
            " --mysql-user=" + self.user + \
            " --mysql-password=" + self.password + \
            " --mysql-socket=" + self.socket + \
            " --time=" + str(time) + \
            " --db-driver=mysql --db-ps-mode=disable run >" + \
            self.workdir + "/log/sysbench_read_only.log &"
        query_status = os.system(query)
        if int(query_status) != 0:
            print("ERROR!: sysbench read only run is failed")
            return 1
        return 0

    def sysbench_oltp_write_only(self, db, tables, threads, table_size, time):
        # Sysbench OLTP write only run
        query = "sysbench /usr/share/sysbench/oltp_write_only.lua" \
            " --table-size=" + str(table_size) + \
            " --tables=" + str(tables) + \
            " --threads=" + str(threads) + \
            " --mysql-db=" + db + \
            " --mysql-user=" + self.user + \
            " --mysql-password=" + self.password + \
            " --mysql-socket=" + self.socket + \
            " --time=" + str(time) + \
            " --db-driver=mysql --db-ps-mode=disable run >" + \
            self.workdir + "/log/sysbench_write_only.log &"
        query_status = os.system(query)
        if int(query_status) != 0:
            print("ERROR!: sysbench write only run is failed")
            return 1
        return 0

    def sysbench_custom_table(self, db):
        table_format = ['DEFAULT', 'DYNAMIC', 'FIXED', 'COMPRESSED', 'REDUNDANT', 'COMPACT']
        # table_compression = ['ZLIB', 'LZ4', 'NONE']
        if not os.path.exists(self.scriptdir + '/sysbench_lua'):
            print("ERROR!: Cannot access 'sysbench_lua': No such directory")
            exit(1)
        for tbl_format in table_format:
            query = self.basedir + "/bin/mysql --user=root --socket=" + \
                    self.socket + " -e'drop database if exists " + \
                    db + "_" + tbl_format + "; create database " + \
                    db + "_" + tbl_format + ";' > /dev/null 2>&1"
            query_status = os.system(query)
            if int(query_status) != 0:
                # return 1
                print("ERROR!: Could not create sysbench test database(" + db + "_" + tbl_format + ")")
                exit(1)
            add_mysqld_option = 'sed -i ' \
                "'s#mysql_table_options = " \
                '.*."#mysql_table_options = "row_format=' + \
                tbl_format + '"#g' + "' " + self.scriptdir + \
                '/sysbench_lua/oltp_custom_common.lua'
            os.system(add_mysqld_option)
            self.sysbench_load(db + "_" + tbl_format)
        return 0
