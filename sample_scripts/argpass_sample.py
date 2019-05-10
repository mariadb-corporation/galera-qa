#!/usr/bin/env python
# Created by Ramesh Sivaraman, Percona LLC.
# This will help us to test PXC.

import argparse
import os
import unittest
import pxc_startup

cwd = os.getcwd()
parser = argparse.ArgumentParser(description='Get variables')
subparser = parser.add_subparsers()
parser.add_argument('-w', '--workdir', default=cwd, help='Specify work directory')
parser.add_argument('-b', '--basedir', default=cwd, help='Specify base directory')
parser.add_argument('-t', '--testname', default='all', choices=['replication', 'correctness', 'all'],
                    help='Specify test name')

args = parser.parse_args()
workdir = args.workdir
basedir = args.basedir
testname = args.testname


node1 = pxc_startup.StartCluster(workdir, basedir)
node1.sanitycheck()
node1.initializecluster()