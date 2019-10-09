#!/usr/bin/env python3
# Created by Ramesh Sivaraman, Percona LLC.
# QA framework will help us to test Percona Server and Percona XtraDB Cluster.

import os
import argparse


def main():
    """ This function will help us to run PS/PXC QA scripts.
        We can initiate complete test suite or individual
        testcase using this function.
    """
    scriptdir = os.path.dirname(os.path.realpath(__file__))
    parser = argparse.ArgumentParser(prog='QA Framework', usage='%(prog)s [options]')
    parser.add_argument('-t', '--testname', help='Specify test file location')
    parser.add_argument('-p', '--product', default='pxc', choices=['pxc', 'ps'],
                        help='Specify product(PXC/PS) name to test')
    parser.add_argument('-s', '--suite', default='',
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

    if suite:
        if not os.path.exists(scriptdir + '/suite/' + suite):
            print('Suite ' + suite + '(' + scriptdir + '/suite/' + suite + ') does not exist')
            exit(1)
        print("Running " + suite + " QA framework")
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
