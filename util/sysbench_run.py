import os
import itertools
import configparser
import sys
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../'))
sys.path.insert(0, parent_dir)
from util import utility
utility_cmd = utility.Utility()
# Reading initial configuration
config = configparser.ConfigParser()
config.read(parent_dir + '/config.ini')
sysbench_user = config['sysbench']['sysbench_user']
sysbench_pass = config['sysbench']['sysbench_pass']
SYSBENCH_DB_CONNECT = " --mysql-user=" + sysbench_user + \
    " --mysql-password=" + sysbench_pass + " --db-driver=mysql "
EXPORT_LUA_PATH = 'export SBTEST_SCRIPTDIR="' + parent_dir + \
            '/sysbench_lua"; export LUA_PATH="' + parent_dir + \
            '/sysbench_lua/?;' + parent_dir + '/sysbench_lua/?.lua"'

class SysbenchRun:
    def __init__(self, basedir, workdir, socket):
        self.basedir = basedir
        self.workdir = workdir
        self.socket = socket

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
                sysbench_user + "@'localhost' identified by '" + sysbench_pass + \
                "';grant all on *.* to " + sysbench_user + "@'localhost'" \
                ';" > /dev/null 2>&1'
        else:
            create_user = self.basedir + "/bin/mysql --user=root --socket=" + \
                self.socket + ' -e"create user if not exists ' + \
                sysbench_user + "@'localhost' identified with  mysql_native_password by '" + \
                sysbench_pass + "';grant all on *.* to " + sysbench_user + "@'localhost'" \
                ';" > /dev/null 2>&1'
        query_status = os.system(create_user)
        if int(query_status) != 0:
            print("ERROR!: Could not create sysbench user : sysbench")
            return 1
        return 0

    def sysbench_load(self, db, tables, threads, table_size):
        # Sysbench data load
        query = EXPORT_LUA_PATH + ";sysbench " + parent_dir + \
            "/sysbench_lua/oltp_insert.lua" \
            " --table-size=" + str(table_size) + \
            " --tables=" + str(tables) + \
            " --threads=" + str(threads) + \
            " --mysql-db=" + db + " " + SYSBENCH_DB_CONNECT + \
            " --mysql-socket=" + self.socket + " prepare >" + \
            self.workdir + "/log/sysbench_prepare.log"
        query_status = os.system(query)
        if int(query_status) != 0:
            print("ERROR!: sysbench data load run is failed")
            return 1
        return 0

    def sysbench_custom_oltp_load(self, db, table_count, thread, table_size):
        # Create sysbench table structure
        result = self.sysbench_load(db, table_count, table_count, 0)
        utility_cmd.check_testcase(result, "Sysbench data load")
        rand_types = ['uniform', 'gaussian', 'special', 'pareto']
        delete_inserts = [10, 20, 30, 40, 50]
        index_updates = [10, 20, 30, 40, 50]
        non_index_updates = [10, 20, 30, 40, 50]
        for rand_type, delete_insert, index_update, non_index_update in \
                itertools.product(rand_types, delete_inserts, index_updates, non_index_updates):
            query = EXPORT_LUA_PATH + ";sysbench " + parent_dir + \
                "/sysbench_lua/oltp_read_write.lua" \
                " --table-size=" + str(table_size) + \
                " --tables=" + str(table_count) + \
                " --threads=" + str(thread) + \
                " --mysql-db=" + db + " " + SYSBENCH_DB_CONNECT + \
                " --mysql-socket=" + self.socket + \
                " --rand_type=" + rand_type + \
                " --delete_inserts=" + str(delete_insert) + \
                " --index_updates=" + str(index_update) + \
                " --non_index_updates=" + str(non_index_update) + " run >" + \
                self.workdir + "/log/sysbench_oltp_read_write.log"
            query_status = os.system(query)
            combination = "rand_type:" + rand_type + \
                          ", delete_inserts:" + str(delete_insert) + \
                          ",idx_updates:" + str(index_update) + \
                          ", non_idx_updates:" + str(non_index_update)
            if int(query_status) != 0:
                print("ERROR!: sysbench oltp(" + combination + ") run is failed")
            else:
                utility_cmd.check_testcase(query_status, "Sysbench oltp(" + combination + ") run")

    def sysbench_custom_read_qa(self, db, table_count, thread, table_size):
        # Create sysbench table structure
        result = self.sysbench_load(db, table_count, table_count, table_size)
        utility_cmd.check_testcase(result, "Sysbench data load")
        sum_ranges = [2, 4, 6]
        distinct_ranges = [3, 5, 7]
        simple_ranges = [1, 3, 5]
        order_ranges = [2, 5, 8]
        point_selects = [10, 20, 30]
        for sum_range, distinct_range, simple_range, order_range, point_select in \
                itertools.product(sum_ranges, distinct_ranges, simple_ranges, order_ranges, point_selects):
            query = EXPORT_LUA_PATH + ";sysbench " + parent_dir + \
                "/sysbench_lua/oltp_read_only.lua" \
                " --table-size=" + str(table_size) + \
                " --tables=" + str(table_count) + \
                " --threads=" + str(thread) + \
                " --mysql-db=" + db + " " + SYSBENCH_DB_CONNECT + \
                " --mysql-socket=" + self.socket + \
                " --distinct_ranges=" + str(distinct_range) + \
                " --sum_ranges=" + str(sum_range) + \
                " --simple_ranges=" + str(simple_range) + \
                " --order_ranges=" + str(order_range) + \
                " --point_selects=" + str(point_select) + \
                " run >" + self.workdir + "/log/sysbench_oltp_read_only.log"
            query_status = os.system(query)
            combination = "distinct_rng:" + str(distinct_range) + \
                          ", sum_rng:" + str(sum_range) + \
                          ", simple_rng:" + str(simple_range) + \
                          ", point_selects:" + str(point_select) + \
                          ", order_rng:" + str(order_range)
            if int(query_status) != 0:
                print("ERROR!: sysbench read only(" + combination + ") run is failed")
                exit(1)
            else:
                utility_cmd.check_testcase(query_status, "Sysbench read only(" + combination + ") run")

    def sysbench_cleanup(self, db, tables, threads, table_size):
        # Sysbench data cleanup
        query = "sysbench /usr/share/sysbench/oltp_insert.lua" \
            " --table-size=" + str(table_size) + \
            " --tables=" + str(tables) + \
            " --threads=" + str(threads) + \
            " --mysql-db=" + db + " " + SYSBENCH_DB_CONNECT + \
            " --mysql-socket=" + self.socket + \
            " cleanup >" + self.workdir + "/log/sysbench_cleanup.log"
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
            " --mysql-db=" + db + " " + SYSBENCH_DB_CONNECT + \
            " --mysql-socket=" + self.socket + \
            " --time=" + str(time) + \
            " --db-ps-mode=disable run >" + \
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
            " --mysql-db=" + db + " " + SYSBENCH_DB_CONNECT + \
            " --mysql-socket=" + self.socket + \
            " --time=" + str(time) + \
            " --db-ps-mode=disable run >" + \
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
            " --mysql-db=" + db + " " + SYSBENCH_DB_CONNECT + \
            " --mysql-socket=" + self.socket + \
            " --time=" + str(time) + \
            " --db-ps-mode=disable run >" + \
            self.workdir + "/log/sysbench_write_only.log &"
        query_status = os.system(query)
        if int(query_status) != 0:
            print("ERROR!: sysbench write only run is failed")
            return 1
        return 0

    def sysbench_custom_table(self, db):
        table_format = ['DEFAULT', 'DYNAMIC', 'FIXED', 'COMPRESSED', 'REDUNDANT', 'COMPACT']
        # table_compression = ['ZLIB', 'LZ4', 'NONE']
        if not os.path.exists(parent_dir + '/sysbench_lua'):
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
                tbl_format + '"#g' + "' " + parent_dir + \
                '/sysbench_lua/oltp_custom_common.lua'
            os.system(add_mysqld_option)
            self.sysbench_load(db + "_" + tbl_format)
        return 0
