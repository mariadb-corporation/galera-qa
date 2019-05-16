#!/usr/bin/env python
# Created by Ramesh Sivaraman, Percona LLC.
# This will help us to test PXC.

import argparse
import os

cwd = os.getcwd()
parser = argparse.ArgumentParser(prog='PXC QA Framework', usage='%(prog)s [options]')
parser.add_argument('-t', '--testname', default='all',
                    choices=['sysbench', 'replication', 'correctness', 'all'],
                    help='Specify test name')
parser.add_argument('--sysbench_threads', default=2, help='Specify sysbench threads. sysbench '
                                                          'table count will be based on this value')
parser.add_argument('--sysbench_table_size', default=1000, help='Specify sysbench table size')
args = parser.parse_args()
testname = args.testname
sysbench_threads = args.sysbench_threads
sysbench_table_size = args.sysbench_table_size
print(args)


