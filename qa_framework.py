#!/usr/bin/env python3
# Created by Ramesh Sivaraman, Percona LLC.
# QA framework will help us to test Percona XtraDB Cluster and Percona Server.

import os
import argparse
import sys
from config import *

def main():
    """ This function will help us to run PS/PXC QA scripts.
        We can initiate complete test suite or individual
        testcase using this function.
    """
    tc_output = open('qa_framework_tc_status.out', 'w')
    scriptdir = os.path.dirname(os.path.realpath(__file__))
    parser = argparse.ArgumentParser(prog='QA Framework', usage='%(prog)s [options]')
    parser.add_argument('-t', '--testname', help='Specify test file location')
    parser.add_argument('-p', '--product', default='pxc', choices=['pxc', 'ps'],
                        help='Specify product(PXC/PS) name to test')
    parser.add_argument('-s', '--suite', default='',
                        choices=['sysbench_run', 'loadtest', 'replication', 'correctness', 'ssl', 'upgrade',
                                 'random_qa', 'galera_sr'], required=True,
                        help='Specify suite name', nargs='*')
    parser.add_argument('-e', '--encryption-run', action='store_true',
                        help='This option will enable encryption options')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='This option will enable debug logging')
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    if args.encryption_run is True:
        encryption = '-e'
    else:
        encryption = ''
    if args.debug is True:
        debug = '-d'
    else:
        debug = ''
    test_name = args.testname
    suite = args.suite
    if len(suite) != 0:
        if not os.path.exists(WORKDIR + '/failed_logs'):
            os.mkdir(WORKDIR + '/failed_logs')
        else:
            os.rmdir(WORKDIR + '/failed_logs')
            os.mkdir(WORKDIR + '/failed_logs')
    for i in suite:
        if i:
            if not os.path.exists(scriptdir + '/suite/' + i):
                print('Suite ' + i + '(' + scriptdir + '/suite/' + i + ') does not exist')
                exit(1)
            print("Running " + i + " QA framework")
            for file in os.listdir(scriptdir + '/suite/' + i):
                if file.endswith(".py"):
                    result = os.system(scriptdir + '/suite/' + i + '/' + file + ' ' + encryption + ' ' + debug)
                    if result == 0:
                        tc_output.write('Test run ' + f'{file:50}' + 'passed\n')
                    else:
                        tc_output.write('Test run ' + f'{file:50}' + 'failed\n')
                        os.system('tar -czf ' + WORKDIR + '/failed_logs/' + i + '_' +
                                  file + '.tar.gz ' + WORKDIR + '/log/*')

    tc_output.close()
    if test_name is not None:
        if not os.path.isfile(test_name):
            print(test_name + ' does not exist')
            exit(1)
        else:
            os.system(scriptdir + '/' + test_name + ' ' + encryption + ' ' + debug)


if __name__ == "__main__":
    main()
