Correctness QA script
---------------------
This script will check data consistency between cluster nodes.
We can also enable encryption options with the argument `--encryption-run`

Correctness QA run log
----------------------
```
$ python3.7 pxc_qa_framework.py --suite=correctness
10:03:13  Startup sanity check                                        [ ✔ ]
10:03:13  Configuration file creation                                 [ ✔ ]
10:03:29  Initializing cluster                                        [ ✔ ]
10:03:47  Cluster startup                                             [ ✔ ]
10:03:47  Database connection                                         [ ✔ ]
10:03:47  Replication QA sysbench run sanity check                    [ ✔ ]
10:03:47  Replication QA sysbench data load                           [ ✔ ]
10:03:47  Sample DB creation                                          [ ✔ ]
10:03:47  Sample data load                                            [ ✔ ]
0
10:03:48  pt-table-checksum run                                       [ ✔ ]
$
```
