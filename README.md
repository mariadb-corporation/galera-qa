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

`python3.7 pxc_qa_framework.py`

Example output
```
ramesh@qaserver-05:~/work/ptest/pxc-qa$ python3.7 pxc_qa_framework.py --testname=sysbench
02:33:13  Sanity check                                                [ Passed ]
02:33:28  Database initialization                                     [ Passed ]
02:33:48  Cluster startup                                             [ Passed ]
02:33:48  Database connection                                         [ Passed ]
02:33:48  sysbench sanity check                                       [ Passed ]
02:33:48  sysbench data load check                                    [ Passed ]
02:33:58  sysbench oltp read only run                                 [ Passed ]
02:34:08  sysbench oltp read write run                                [ Passed ]
02:34:18  sysbench oltp write only run                                [ Passed ]
ramesh@qaserver-05:~/work/ptest/pxc-qa$
```
