GALERA QA Framework
==============================================================================

This suite will help us to test MariaDB Galera Cluster with various testcases. 
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
basedir = /dev/shm/qa/GAL_MD240221-mariadb-10.6.0-linux-x86_64-opt
server=mdg
node = 3
user = root
md1_socket = /tmp/mdnode1.sock
md2_socket = /tmp/mdnode2.sock
md3_socket = /tmp/mdnode3.sock
pt_basedir = /dev/shm/qa/percona-toolkit-3.0.10
pquery_bin = /dev/shm/qa/pquery2-md
pquery_grammer_file = /dev/shm/qa/grammer.sql

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
galera_lower_base = /dev/shm/qa/GAL_MD240221-mariadb-10.5.10-linux-x86_64-opt
galera_upper_base = /dev/shm/qa/GAL_MD240221-mariadb-10.6.0-linux-x86_64-opt
```

If you need to start MariaDB Galera Cluster with custom configuration you should add the parameters 
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
  -p {mdg,md}, --product {mdg,md}
                        Specify product(mdg/md) name to test
  -s [{sysbench_run,loadtest,replication,correctness,ssl,upgrade,random_qa,galera_sr} [{sysbench_run,loadtest,replication,correctness,ssl,upgrade,random_qa,galera_sr} ...]], --suite [{sysbench_run,loadtest,replication,correctness,ssl,upgrade,random_qa,galera_sr} [{sysbench_run,loadtest,replication,correctness,ssl,upgrade,random_qa,galera_sr} ...]]
                        Specify suite name
  -e, --encryption-run  This option will enable encryption options
  -d, --debug           This option will enable debug logging

```
