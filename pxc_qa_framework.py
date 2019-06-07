#!/usr/bin/env python3.7
# Created by Ramesh Sivaraman, Percona LLC.
# PXC QA framework will help us to test Percona XtraDB Cluster.

import configparser
import os
import argparse


def main():
    """ This function will help us to run PXC QA scripts.
        We can initiate complete test suite or individual
        testcase using this function.
    """
    scriptdir = os.path.dirname(os.path.realpath(__file__))
    parser = argparse.ArgumentParser(prog='PXC QA Framework', usage='%(prog)s [options]')
    parser.add_argument('-t', '--testname', help='Specify test file location')
    parser.add_argument('-s', '--suite', default='all',
                        choices=['loadtest', 'replication', 'correctness', 'ssl', 'all'],
                        help='Specify suite name')
    parser.add_argument('-e', '--encryption-run', action='store_true',
                        help='This option will enable encryption options')
    parser.add_argument('--sysbench_threads', default=2, help='Specify sysbench threads. sysbench '
                                                              'table count will be based on this value')
    parser.add_argument('--sysbench_table_size', default=1000, help='Specify sysbench table size')
    parser.add_argument('--sysbench_run_time', default=10, help='Specify sysbench oltp run time (in sec)')

    args = parser.parse_args()
    if args.encryption_run is True:
        encryption = '-e'
    else:
        encryption = ''
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
                os.system(scriptdir + '/suite/replication/' + file + ' ' + encryption)
    elif suite == 'correctness':
        if not os.path.exists(scriptdir + '/suite/correctness'):
            print('Suite ' + suite + '(' + scriptdir + '/suite/correctness) does not exist')
            exit(1)
        for file in os.listdir(scriptdir + '/suite/correctness'):
            if file.endswith(".py"):
                os.system(scriptdir + '/suite/correctness/' + file + ' ' + encryption)
    elif suite == 'ssl':
        if not os.path.exists(scriptdir + '/suite/ssl'):
            print('Suite ' + suite + '(' + scriptdir + '/suite/ssl) does not exist')
            exit(1)
        for file in os.listdir(scriptdir + '/suite/ssl'):
            if file.endswith(".py"):
                os.system(scriptdir + '/suite/ssl/' + file + ' ' + encryption)
    elif suite == 'loadtest':
        if not os.path.exists(scriptdir + '/suite/loadtest'):
            print('Suite ' + suite + '(' + scriptdir + '/suite/loadtest) does not exist')
            exit(1)
        for file in os.listdir(scriptdir + '/suite/loadtest'):
            if file.endswith(".py"):
                os.system(scriptdir + '/suite/loadtest/' + file + ' ' + encryption)

    if test_name is not None:
        if not os.path.isfile(test_name):
            print(test_name + ' does not exist')
            return 1
            exit(1)
        else:
            os.system(scriptdir + '/' + test_name + ' ' + encryption)


if __name__ == "__main__":
    main()
