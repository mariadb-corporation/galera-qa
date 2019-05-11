#!/usr/bin/env python
# Created by Ramesh Sivaraman, Percona LLC.
# This will help us to test PXC.

import configparser
import os
import pxc_startup
import db_connection

config = configparser.ConfigParser()
config.read('config.ini')
scriptdir = os.path.dirname(os.path.realpath(__file__))
workdir = config['config']['workdir']
basedir = config['config']['basedir']
node = config['config']['node']

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


