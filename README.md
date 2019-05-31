PXC QA
==============================================================================

This suite will help us to test Percona XtraDB Cluster using different functionalities. We can also customize the testcases 
using configuration files without disturbing main code.

Configuration details
------------------------------------------------------------------------------

Basic configuration details are available in [config.ini](./config.ini) file. We need to change the configurations as per our environment.

config.ini
```
[config]
workdir = /dev/shm/qa
basedir = /dev/shm/qa/Percona-XtraDB-Cluster-5.7.25-rel28-31.35.1.Linux.x86_64.ssl100
node = 2
user = root
node1_socket = /tmp/node1.sock
node2_socket = /tmp/node2.sock
node3_socket = /tmp/node3.sock
ps1_socket = /tmp/psnode1.sock
ps2_socket = /tmp/psnode2.sock
ps3_socket = /tmp/psnode3.sock
pt_basedir = /dev/shm/qa/percona-toolkit-3.0.10

[sysbench]
sysbench_user=sysbench
sysbench_pass=sysbench
```

If we need to start Percona XtraDB Cluster with custom configuration we should add the parameters in [custom.cnf](./conf/custom.cnf)

Initializing framework
--------------------------------------------

`python3.7 pxc_qa_framework.py --testname=suite/replication/replication.py`

Script usage info
```$ python3.7 pxc_qa_framework.py --help
usage: PXC QA Framework [options]

optional arguments:
  -h, --help            show this help message and exit
  -t TESTNAME, --testname TESTNAME
                        Specify test file location
  -s {loadtest,replication,correctness,ssl,all}, --suite {loadtest,replication,correctness,ssl,all}
                        Specify suite name
  -e, --encryption-run  This option will enable encryption options
  --sysbench_threads SYSBENCH_THREADS
                        Specify sysbench threads. sysbench table count will be
                        based on this value
  --sysbench_table_size SYSBENCH_TABLE_SIZE
                        Specify sysbench table size
  --sysbench_run_time SYSBENCH_RUN_TIME
                        Specify sysbench oltp run time (in sec)
```
