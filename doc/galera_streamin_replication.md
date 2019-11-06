Streaming Replication QA script
---------------------
This suite will test streaming replication feature.

Streaming replication run log
-----------------------------
```
$ python3 qa_framework.py --testname=suite/galera_sr/galera_basic_sr_qa.py
--------------------------------

PXC Streaming Replication test
--------------------------------
01:12:22  Startup sanity check                                                                                [ ✓ ]
01:12:22  Configuration file creation                                                                         [ ✓ ]
01:13:16  Initializing cluster                                                                                [ ✓ ]
01:14:47  Cluster startup                                                                                     [ ✓ ]
01:14:47  Database connection                                                                                 [ ✓ ]
01:14:48  Sysbench run sanity check                                                                           [ ✓ ]
01:17:04  Sysbench data load (threads : 10)                                                                   [ ✓ ]
01:17:04  Creating streaming replication data insert procedure                                                [ ✓ ]
01:17:05  SR testcase( DML row count 100, fragment_unit : bytes, fragment_size : 1 )                          [ ✓ ]
01:17:24  SR testcase( DML row count 1000, fragment_unit : bytes, fragment_size : 1 )                         [ ✓ ]
01:18:01  SR testcase( DML row count 10000, fragment_unit : bytes, fragment_size : 1 )                        [ ✓ ]
01:24:02  SR testcase( DML row count 100000, fragment_unit : bytes, fragment_size : 1 )                       [ ✓ ]
01:24:42  SR testcase( DML row count 100, fragment_unit : bytes, fragment_size : 2 )                          [ ✓ ]
01:25:32  SR testcase( DML row count 1000, fragment_unit : bytes, fragment_size : 2 )                         [ ✓ ]
01:26:32  SR testcase( DML row count 10000, fragment_unit : bytes, fragment_size : 2 )                        [ ✓ ]
[..]
```