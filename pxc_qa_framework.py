#!/usr/bin/env python3.7
# Created by Ramesh Sivaraman, Percona LLC.
# PXC QA framework will help us to test Percona XtraDB Cluster.

import configparser
import os
import argparse

def main():
    scriptdir = os.path.dirname(os.path.realpath(__file__))
    parser = argparse.ArgumentParser(prog='PXC QA Framework', usage='%(prog)s [options]')
    parser.add_argument('-t', '--testname', help='Specify test file location')
    parser.add_argument('-s', '--suite', default='all',
                        choices=['loadtest', 'replication', 'correctness', 'all'],
                        help='Specify test name')
    parser.add_argument('--sysbench_threads', default=2, help='Specify sysbench threads. sysbench '
                                                              'table count will be based on this value')
    parser.add_argument('--sysbench_table_size', default=1000, help='Specify sysbench table size')
    parser.add_argument('--sysbench_run_time', default=10, help='Specify sysbench oltp run time (in sec)')

    args = parser.parse_args()
    test_name = args.testname
    suite = args.suite
    config = configparser.ConfigParser()
    config.read('config.ini')

    if suite == 'replication':
        if not os.path.exists(scriptdir + '/suite/replication'):
            print('Suite ' + suite + '(' + scriptdir + '/suite/replication) does not exist')
            exit(1)
        for file in os.listdir(scriptdir + '/suite/replication'):
            if file.endswith(".py"):
                os.system(scriptdir + '/suite/replication/' + file)

    if test_name is not None:
        if not os.path.isfile(test_name):
            print(test_name + ' does not exist')
            return 1
            exit(1)
        else:
            os.system(scriptdir + '/' + test_name)


if __name__ == "__main__":
    main()
