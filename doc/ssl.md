SSL QA script
-------------

This script will enable SSL configurations for SST, data transfer and client server connection. 
We can also enable encryption options with `--encryption-run`

SSL QA run log
--------------
```
$ python3.7 pxc_qa_framework.py --suite=ssl
09:48:10  Startup sanity check                                        [ ✔ ]
09:48:10  Configuration file creation                                 [ ✔ ]
09:48:25  Initializing cluster                                        [ ✔ ]
09:48:43  Cluster startup                                             [ ✔ ]
09:48:43  Database connection                                         [ ✔ ]
09:48:43  SSL QA sysbench run sanity check                            [ ✔ ]
09:48:43  SSL QA sysbench data load                                   [ ✔ ]
09:48:43  SSL QA sample DB creation                                   [ ✔ ]
09:48:44  SSL QA sample data load                                     [ ✔ ]
09:48:44  RQG data load                                               [ ✔ ]
09:48:44  SSL QA table test.sbtest1 checksum between nodes            [ ✔ ]
09:48:44  SSL QA table pxc_dataload_db.t1 checksum between nodes      [ ✔ ]
0
09:48:44  pt-table-checksum run                                       [ ✔ ]
$
```
