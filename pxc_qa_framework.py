#!/usr/bin/env python
# Created by Ramesh Sivaraman, Percona LLC.
# This will help us to test PXC.

import configparser
import os
import pxc_startup
import db_connection
import sysbench_run
import argparse
import consistency_check
from datetime import datetime


def printit(text, status):
    now = datetime.now().strftime("%H:%M:%S ")
    print(now + ' ' + f'{text:60}' + '[ ' + status + ' ]')


def check_testcase(result,testcase):
    if result == 0:
        printit(testcase, "Passed")
    else:
        printit(testcase, "Failed")


def sysbenchtest(basedir, workdir,
                 sysbench_user, sysbench_pass, node1_socket,
                 sysbench_db, sysbench_threads,
                 sysbench_table_size, sysbench_run_time):

    sysbench = sysbench_run.SysbenchRun(basedir, workdir,
                                        sysbench_user, sysbench_pass,
                                        node1_socket, sysbench_threads,
                                        sysbench_table_size, sysbench_db,
                                        sysbench_threads, sysbench_run_time)

    result = sysbench.sanitycheck()
    check_testcase(result, "sysbench sanity check")

    result = sysbench.sysbench_load()
    check_testcase(result, "sysbench data load check")

    result = sysbench.sysbench_oltp_read_only()
    check_testcase(result, "sysbench oltp read only run")

    result = sysbench.sysbench_oltp_read_write()
    check_testcase(result, "sysbench oltp read write run")

    result = sysbench.sysbench_oltp_write_only()
    check_testcase(result, "sysbench oltp write only run")

def checksumtest(basedir, workdir, sysbench_user,
                 sysbench_pass, node1_socket,
                 pt_basedir, sysbench_db, node):
    checksum = consistency_check.ConsistencyCheck(basedir, workdir,
                                                  sysbench_user, sysbench_pass, node1_socket,
                                                  pt_basedir, sysbench_db, int(node))
    result = checksum.sanitycheck()
    check_testcase(result, "PXC correctness sanity check")

    result = checksum.data_consistency()
    check_testcase(result, "PXC database correctness run")

def main():
    scriptdir = os.path.dirname(os.path.realpath(__file__))
    parser = argparse.ArgumentParser(prog='PXC QA Framework', usage='%(prog)s [options]')
    parser.add_argument('-t', '--testname', default='all',
                        choices=['sysbench', 'replication', 'correctness', 'all'],
                        help='Specify test name')
    parser.add_argument('--sysbench_threads', default=2, help='Specify sysbench threads. sysbench '
                                                              'table count will be based on this value')
    parser.add_argument('--sysbench_table_size', default=1000, help='Specify sysbench table size')
    parser.add_argument('--sysbench_run_time', default=10, help='Specify sysbench oltp run time (in sec)')
    args = parser.parse_args()
    testname = args.testname
    sysbench_threads = args.sysbench_threads
    sysbench_table_size = args.sysbench_table_size
    sysbench_run_time = args.sysbench_run_time

    config = configparser.ConfigParser()
    config.read('config.ini')
    workdir = config['config']['workdir']
    basedir = config['config']['basedir']
    node = config['config']['node']
    user = config['config']['user']
    node1_socket = config['config']['node1_socket']
    pt_basedir = config['config']['pt_basedir']
    sysbench_user = config['sysbench']['sysbench_user']
    sysbench_pass = config['sysbench']['sysbench_pass']
    sysbench_db = config['sysbench']['sysbench_db']

    dbconnection_check = db_connection.DbConnection(user, node1_socket)
    cluster = pxc_startup.StartCluster(scriptdir, workdir, basedir, int(node))
    result = cluster.sanitycheck()
    check_testcase(result, "Sanity check")

    result = cluster.createconfig()
    check_testcase(result, "PXC configuration file creation")

    result = cluster.initializecluster()
    check_testcase(result, "PXC database initialization")

    startup_check = cluster.startcluster()
    check_testcase(startup_check, "Cluster startup")

    result = dbconnection_check.connectioncheck()
    check_testcase(result, "Database connection")

    if testname == 'sysbench':
        sysbenchtest(basedir, workdir,
                     sysbench_user, sysbench_pass, node1_socket,
                     sysbench_db, sysbench_threads,
                     sysbench_table_size, sysbench_run_time)

    elif testname == 'correctness':
        sysbenchtest(basedir, workdir,
                     sysbench_user, sysbench_pass, node1_socket,
                     sysbench_db, sysbench_threads,
                     sysbench_table_size, sysbench_run_time)
        checksumtest(basedir, workdir,
                     sysbench_user, sysbench_pass, node1_socket,
                     pt_basedir, sysbench_db, int(node))


if __name__ == "__main__":
    main()
