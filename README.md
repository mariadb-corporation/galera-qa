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
ramesh@qaserver-05:~/work/ptest/pxc-qa$ python3.7 pxc_qa_framework.py
Sanity check passed!
Database initialization passed!
Cluster started successfully!
Database connection passed!
sysbench sanity check passed!
sysbench data load passed!
sysbench oltp read only run passed!
sysbench oltp read write run passed!
sysbench oltp write only run passed!
ramesh@qaserver-05:~/work/ptest/pxc-qa$
```
