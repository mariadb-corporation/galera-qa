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
    parser.add_argument('-s', '--suite', default='replication',
                        choices=['sysbench_loadtest', 'replication', 'correctness', 'ssl', 'upgrade',
                                 'random_qa', 'galera_sr'],
                        help='Specify suite name')
    parser.add_argument('-e', '--encryption-run', action='store_true',
                        help='This option will enable encryption options')

    args = parser.parse_args()
    if args.encryption_run is True:
        encryption = '-e'
    else:
        encryption = ''
    test_name = args.testname
    suite = args.suite
    config = configparser.ConfigParser()
    config.read('config.ini')

    if suite:
        if not os.path.exists(scriptdir + '/suite/replication'):
            print('Suite ' + suite + '(' + scriptdir + '/suite/' + suite + ') does not exist')
            exit(1)
        for file in os.listdir(scriptdir + '/suite/' + suite):
            if file.endswith(".py"):
                os.system(scriptdir + '/suite/' + suite + '/' + file + ' ' + encryption)

    if test_name is not None:
        if not os.path.isfile(test_name):
            print(test_name + ' does not exist')
            exit(1)
        else:
            os.system(scriptdir + '/' + test_name + ' ' + encryption)


if __name__ == "__main__":
    main()
