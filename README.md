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
[sysbench]
sysbench_user=sysbench
sysbench_pass=sysbench
sysbench_db=sbtest
```

If we need to start Percona XtraDB Cluster with custom configuration we should add the parameters in [custom.cnf](./conf/custom.cnf)

Initializing framework
--------------------------------------------

`python3.7 pxc_qa_framework.py --testname=sysbench --sysbench_threads=20 --sysbench_table_size=55 --sysbench_run_time=30`

Script usage info
```$ python3.7 pxc_qa_framework.py --help
usage: PXC QA Framework [options]

optional arguments:
  -h, --help            show this help message and exit
  -t {sysbench,replication,correctness,all}, --testname {sysbench,replication,correctness,all}
                        Specify test name
  --sysbench_threads SYSBENCH_THREADS
                        Specify sysbench threads. sysbench table count will be
                        based on this value
  --sysbench_table_size SYSBENCH_TABLE_SIZE
                        Specify sysbench table size
  --sysbench_run_time SYSBENCH_RUN_TIME
                        Specify sysbench oltp run time (in sec)
$
```

Example output
```
$ python3.7 pxc_qa_framework.py --testname=sysbench --sysbench_threads=20 --sysbench_table_size=55 --sysbench_run_time=30
10:40:47  Sanity check                                                [ Passed ]
10:40:47  PXC configuration file creation                             [ Passed ]
10:41:03  PXC database initialization                                 [ Passed ]
10:41:22  Cluster startup                                             [ Passed ]
10:41:22  Database connection                                         [ Passed ]
10:41:22  sysbench sanity check                                       [ Passed ]
10:41:22  sysbench data load check                                    [ Passed ]
10:41:52  sysbench oltp read only run                                 [ Passed ]
10:42:22  sysbench oltp read write run                                [ Passed ]
10:42:52  sysbench oltp write only run                                [ Passed ]
$
```
