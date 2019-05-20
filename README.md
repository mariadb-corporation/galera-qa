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

Example output
```
$ python3.7 pxc_qa_framework.py --testname=suite/replication/replication.py
PXC Node as Master and PS node as Slave
---------------------------------------

09:12:29  PXC: Startup sanity check                                   [ ✔ ]
09:12:29  PXC: Configuration file creation                            [ ✔ ]
09:12:29  PXC: Adding custom configuration                            [ ✔ ]
09:12:44  PXC: Initializing cluster                                   [ ✔ ]
09:13:03  PXC: Cluster startup                                        [ ✔ ]
09:13:03  PXC: Database connection                                    [ ✔ ]
09:13:03  PS: Startup sanity check                                    [ ✔ ]
09:13:03  PS: Configuration file creation                             [ ✔ ]
09:13:03  PS: Adding custom configuration                             [ ✔ ]
09:13:11  PS: Initializing cluster                                    [ ✔ ]
09:13:12  PS: Cluster startup                                         [ ✔ ]
09:13:12  PS: Database connection                                     [ ✔ ]
09:13:12  PS: Slave started                                           [ ✔ ]
09:13:12  PXC: sysbench run sanity check                              [ ✔ ]
09:13:12  PXC: sysbench data load check                               [ ✔ ]
09:13:12  PS: Slave status after data load                            [ ✔ ]
PXC Node as Slave and PS node as Master
---------------------------------------

09:13:12  PXC: Startup sanity check                                   [ ✔ ]
09:13:12  PXC: Configuration file creation                            [ ✔ ]
09:13:12  PXC: Adding custom configuration                            [ ✔ ]
09:13:28  PXC: Initializing cluster                                   [ ✔ ]
09:13:47  PXC: Cluster startup                                        [ ✔ ]
09:13:47  PXC: Database connection                                    [ ✔ ]
09:13:47  PS: Startup sanity check                                    [ ✔ ]
09:13:47  PS: Configuration file creation                             [ ✔ ]
09:13:47  PS: Adding custom configuration                             [ ✔ ]
09:13:55  PS: Initializing cluster                                    [ ✔ ]
09:13:56  PS: Cluster startup                                         [ ✔ ]
09:13:56  PS: Database connection                                     [ ✔ ]
09:13:56  PS: Slave started                                           [ ✔ ]
09:13:56  PXC: sysbench run sanity check                              [ ✔ ]
09:13:56  PXC: sysbench data load check                               [ ✔ ]
09:13:56  PS: Slave status after data load                            [ ✔ ]
$
```
