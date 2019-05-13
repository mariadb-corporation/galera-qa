#!/usr/bin/env python
# Created by Ramesh Sivaraman, Percona LLC.
# This will help us to test PXC.

import configparser
import os
import pxc_startup
import db_connection
import sysbench_run

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
if result == 0:
    print("Sanity check passed!")
else:
    print("Sanity check failed!")
cluster.createconfig()

result = cluster.initializecluster()
if result == 0:
    print("Database initialization passed!")
else:
    print("Database initialization failed!")

startup_check = cluster.startcluster()
if startup_check == 0:
    print("Cluster started successfully!")
else:
    print("Cluster startup failed!")

result = dbconnection_check.connectioncheck()
if result == 0:
    print("Database connection passed!")
else:
    print("Database connection failed!")


sysbench = sysbench_run.SysbenchRun(basedir,
                                        workdir,
                                        sysbench_user,
                                        sysbench_pass,
                                        '/tmp/node1.sock',
                                        '10',
                                        '100',
                                        'sbtest',
                                        '2',
                                        '10')

result = sysbench.sanitycheck()
if result == 0:
    print("sysbench sanity check passed!")
else:
    print("sysbench sanity check failed!")

result = sysbench.sysbench_load()
if result == 0:
    print("sysbench data load passed!")
else:
    print("sysbench data load failed!")

result = sysbench.sysbench_oltp_read_only()
if result == 0:
    print("sysbench oltp read only run passed!")
else:
    print("sysbench oltp read only run failed!")

result = sysbench.sysbench_oltp_read_write()
if result == 0:
    print("sysbench oltp read write run passed!")
else:
    print("sysbench oltp read write run failed!")

result = sysbench.sysbench_oltp_write_only()
if result == 0:
    print("sysbench oltp write only run passed!")
else:
    print("sysbench oltp write only run failed!")
