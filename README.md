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
pt_basedir = /dev/shm/qa/percona-toolkit-3.0.13

[sysbench]
sysbench_user=sysbench
sysbench_pass=sysbench
sysbench_db=sbtest
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
  -s {loadtest,replication,correctness,all}, --suite {loadtest,replication,correctness,all}
                        Specify suite name
  --sysbench_threads SYSBENCH_THREADS
                        Specify sysbench threads. sysbench table count will be
                        based on this value
  --sysbench_table_size SYSBENCH_TABLE_SIZE
                        Specify sysbench table size
  --sysbench_run_time SYSBENCH_RUN_TIME
                        Specify sysbench oltp run time (in sec)
```

Example output (Replication suite)
```
$ python3.7 pxc_qa_framework.py --suite=replication

NON-GTID PXC Node as Master and PS node as Slave
---------------------------------------
01:40:09  PXC: Startup sanity check                                   [ ✔ ]
01:40:09  PXC: Configuration file creation                            [ ✔ ]
01:40:09  PXC: Adding custom configuration                            [ ✔ ]
01:40:25  PXC: Initializing cluster                                   [ ✔ ]
01:40:44  PXC: Cluster startup                                        [ ✔ ]
01:40:44  PXC: Database connection                                    [ ✔ ]
01:40:44  PS: Startup sanity check                                    [ ✔ ]
01:40:44  PS: Configuration file creation                             [ ✔ ]
01:40:44  PS: Adding custom configuration                             [ ✔ ]
01:40:52  PS: Initializing cluster                                    [ ✔ ]
01:40:53  PS: Cluster startup                                         [ ✔ ]
01:40:53  PS: Database connection                                     [ ✔ ]
01:40:53  PS: Slave started                                           [ ✔ ]
01:40:53  PXC: Replication QA sysbench run sanity check               [ ✔ ]
01:40:53  PXC: Replication QA sysbench data load                      [ ✔ ]
01:40:53  PXC: Replication QA sample DB creation                      [ ✔ ]
01:40:53  PXC: Replication QA sample data load                        [ ✔ ]
01:40:53  PS: Slave status after data load                            [ ✔ ]

NON-GTID PXC Node as Slave and PS node as Master
---------------------------------------
01:40:53  PXC: Startup sanity check                                   [ ✔ ]
[..]

GTID PXC/PS Node as master and Slave
---------------------------------------
01:43:48  PXC: Startup sanity check                                   [ ✔ ]
01:43:48  PXC: Configuration file creation                            [ ✔ ]
01:43:48  PXC: Adding custom configuration                            [ ✔ ]
01:44:03  PXC: Initializing cluster                                   [ ✔ ]
01:44:21  PXC: Cluster startup                                        [ ✔ ]
01:44:21  PXC: Database connection                                    [ ✔ ]
01:44:21  PS: Startup sanity check                                    [ ✔ ]
01:44:21  PS: Configuration file creation                             [ ✔ ]
01:44:21  PS: Adding custom configuration                             [ ✔ ]
01:44:29  PS: Initializing cluster                                    [ ✔ ]
01:44:30  PS: Cluster startup                                         [ ✔ ]
01:44:30  PS: Database connection                                     [ ✔ ]
01:44:30  PS: Slave started                                           [ ✔ ]
01:44:30  PS: Slave started                                           [ ✔ ]
01:44:30  PS: Replication QA sysbench run sanity check                [ ✔ ]
01:44:31  PS: Replication QA sysbench data load                       [ ✔ ]
01:44:31  PS: Replication QA sample DB creation                       [ ✔ ]
01:44:31  PS: Replication QA sample data load                         [ ✔ ]
01:44:31  PXC: Replication QA sysbench run sanity check               [ ✔ ]
01:44:31  PXC: Replication QA sysbench data load                      [ ✔ ]
01:44:31  PXC: Replication QA sample DB creation                      [ ✔ ]
01:44:31  PXC: Replication QA sample data load                        [ ✔ ]
01:44:31  PS: Slave status after data load                            [ ✔ ]
01:44:31  PS: Slave status after data load                            [ ✔ ]
$
```
Example output (Correctness)
```
$ python3.7 pxc_qa_framework.py --suite=correctness 
05:48:24  Startup sanity check                                        [ ✔ ]
05:48:24  Configuration file creation                                 [ ✔ ]
05:48:39  Initializing cluster                                        [ ✔ ]
05:48:57  Cluster startup                                             [ ✔ ]
05:48:57  Database connection                                         [ ✔ ]
05:48:57  Replication QA sysbench run sanity check                    [ ✔ ]
05:48:58  Replication QA sysbench data load                           [ ✔ ]
05:48:58  Sample DB creation                                          [ ✔ ]
05:48:58  Sample data load                                            [ ✔ ]
05:48:58  pt-table-checksum run                                       [ ✔ ]
$
```
