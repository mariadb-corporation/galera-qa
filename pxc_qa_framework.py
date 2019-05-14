#!/usr/bin/env python
# Created by Ramesh Sivaraman, Percona LLC.
# This will help us to test PXC.

import configparser
import os
import pxc_startup
import db_connection
import sysbench_run
import argparse
from datetime import datetime


def printit(text, status):
    now = datetime.now().strftime("%H:%M:%S ")
    print(now + ' ' + f'{text:60}' + '[ ' + status + ' ]')


def check_testcase(result,testcase):
    if result == 0:
        printit(testcase, "Passed")
    else:
        printit(testcase, "Failed")


def sysbenchtest(basedir, workdir, sysbench_user, sysbench_pass,sysbench_db):
    sysbench = sysbench_run.SysbenchRun(basedir, workdir, sysbench_user, sysbench_pass,
                                            '/tmp/node1.sock', '10', '100',
                                            sysbench_db, '2', '10')

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


def main():
    parser = argparse.ArgumentParser(description='Get variables')
    parser.add_subparsers()
    parser.add_argument('-t', '--testname', default='all', choices=['sysbench', 'replication', 'correctness', 'all'],
                        help='Specify test name')
    args = parser.parse_args()
    testname = args.testname

    config = configparser.ConfigParser()
    config.read('config.ini')
    scriptdir = os.path.dirname(os.path.realpath(__file__))
    workdir = config['config']['workdir']
    basedir = config['config']['basedir']
    node = config['config']['node']
    sysbench_user = config['sysbench']['sysbench_user']
    sysbench_pass = config['sysbench']['sysbench_pass']
    sysbench_db = config['sysbench']['sysbench_db']

    dbconnection_check = db_connection.DbConnection('root', '/tmp/node1.sock')
    cluster = pxc_startup.StartCluster(scriptdir, workdir, basedir, int(node))
    result = cluster.sanitycheck()
    check_testcase(result, "Sanity check ")
    cluster.createconfig()

    result = cluster.initializecluster()
    check_testcase(result, "Database initialization")

    startup_check = cluster.startcluster()
    check_testcase(startup_check, "Cluster startup")

    result = dbconnection_check.connectioncheck()
    check_testcase(result, "Database connection")

    if testname == 'sysbench':
        sysbenchtest(basedir, workdir, sysbench_user, sysbench_pass, sysbench_db)

if __name__ == "__main__":
    main()
