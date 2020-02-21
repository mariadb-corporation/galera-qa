PQA Framework
==============================================================================

This suite will help us to test Percona XtraDB Cluster/Percona Server with various testcases. 
You can customize the testcases 
using configuration files without disturbing main code.

Configuration details
------------------------------------------------------------------------------

Basic configuration details are available in [config.ini](./config.ini) file. You need to change the configurations as 
per your environment.

config.ini
```
[config]
workdir = /dev/shm/qa
basedir = /dev/shm/qa/Percona-XtraDB-Cluster-5.7.25-rel28-31.35.1.Linux.x86_64.ssl100
server=pxc
node = 3
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
sysbench_db=sbtest
sysbench_table_count = 10
sysbench_threads = 10
sysbench_normal_table_size = 1000
sysbench_run_time = 300
sysbench_load_test_table_size = 100000
sysbench_random_load_table_size = 1000
sysbench_random_load_run_time = 100
sysbench_oltp_test_table_size = 10000000
sysbench_read_qa_table_size = 100000
sysbench_customized_dataload_table_size = 1000


[upgrade]
pxc_lower_base = /dev/shm/qa/Percona-XtraDB-Cluster-5.6.44-rel86.0-28.34-debug..Linux.x86_64
pxc_upper_base = /dev/shm/qa/Percona-XtraDB-Cluster-5.7.25-rel28-31.35.1.Linux.x86_64.ssl100
```

If you need to start Percona XtraDB Cluster/Percona Server with custom configuration you should add the parameters 
in [custom.cnf](./conf/custom.cnf)

Initializing framework
--------------------------------------------

`python3 qa_framework.py --testname=suite/replication/replication.py`

Script usage info
```$ python3 qa_framework.py  --help
usage: QA Framework [options]

optional arguments:
  -h, --help            show this help message and exit
  -t TESTNAME, --testname TESTNAME
                        Specify test file location
  -p {pxc,ps}, --product {pxc,ps}
                        Specify product(PXC/PS) name to test
  -s {sysbench_loadtest,replication,correctness,ssl,upgrade,random_qa,galera_sr}, --suite {sysbench_loadtest,replication,correctness,ssl,upgrade,random_qa,galera_sr}
                        Specify suite name
  -e, --encryption-run  This option will enable encryption options

```
