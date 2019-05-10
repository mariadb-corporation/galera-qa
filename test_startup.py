import configparser
import unittest
import pxc_startup
import db_connection

config = configparser.ConfigParser()
config.read('config.ini')
config.sections()
workdir = config['config']['workdir']
basedir = config['config']['basedir']

cluster = pxc_startup.StartCluster(workdir, basedir, 2)
connection_check = db_connection.DbConnection('root', '/tmp/node1.sock')
connection_check.connectioncheck()

class TestStartup(unittest.TestCase):

    def test_sanitycheck(self):
        self.assertEqual(cluster.sanitycheck(), 0,
                         'work/base directory have some issues')
        print('PXC Sanity check')

    def test_initializecluster(self):
        self.assertIsNot(cluster.initializecluster(), 1,
                         'Could not initialize database directory. '
                         'Please check error log')

    def test_startcluster(self):
        self.assertIsNot(cluster.startcluster(), 1,
                         'Could not start cluster, '
                         'Please check error log')
        print('Starting Cluster')

    def test_connectionchecl(self):
        self.assertIsNot(connection_check.connectioncheck(), 1,
                         'Could not establish DB connection')
        print('Checking DB connection')


if __name__ == '__main__':
    unittest.main()
