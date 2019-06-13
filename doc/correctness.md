Correctness QA script
---------------------
This script will check data consistency between cluster nodes.
We can also enable encryption options with the argument `--encryption-run`

Correctness QA run log
----------------------
```
$ python3 pxc_qa_framework.py  --suite=correctness
---------------------------------------------------
Crash recovery QA using forceful mysqld termination
---------------------------------------------------
07:33:21  Startup sanity check                                                                                [ ✔ ]
07:33:21  Configuration file creation                                                                         [ ✔ ]
07:33:56  Initializing cluster                                                                                [ ✔ ]
07:34:17  Cluster startup                                                                                     [ ✔ ]
07:34:17  Database connection                                                                                 [ ✔ ]
07:34:18  Sysbench run sanity check                                                                           [ ✔ ]
07:34:19  Sysbench data load                                                                                  [ ✔ ]
07:34:19  Initiated sysbench oltp run                                                                         [ ✔ ]
07:34:29  Killed cluster node for crash recovery                                                              [ ✔ ]
07:34:54  Cluster recovery is successful                                                                      [ ✔ ]
07:34:55  pt-table-checksum error code : --pid file exists and the PID is running                             [ ✘ ]
-------------------------------
Crash recovery QA using single restart
-------------------------------
07:34:55  Startup sanity check                                                                                [ ✔ ]
07:34:55  Configuration file creation                                                                         [ ✔ ]
07:35:30  Initializing cluster                                                                                [ ✔ ]
07:35:51  Cluster startup                                                                                     [ ✔ ]
07:35:51  Database connection                                                                                 [ ✔ ]
07:35:51  Sysbench run sanity check                                                                           [ ✔ ]
07:35:53  Sysbench data load                                                                                  [ ✔ ]
07:35:53  Initiated sysbench oltp run                                                                         [ ✔ ]
07:36:03  Shutdown cluster node for crash recovery                                                            [ ✔ ]
07:36:12  Cluster recovery is successful                                                                      [ ✔ ]
07:36:13  pt-table-checksum error code : --pid file exists and the PID is running                             [ ✘ ]
----------------------------------------
Crash recovery QA using multiple restart
----------------------------------------
07:36:13  Startup sanity check                                                                                [ ✔ ]
07:36:13  Configuration file creation                                                                         [ ✔ ]
07:36:48  Initializing cluster                                                                                [ ✔ ]
07:37:09  Cluster startup                                                                                     [ ✔ ]
07:37:09  Database connection                                                                                 [ ✔ ]
07:37:09  Sysbench run sanity check                                                                           [ ✔ ]
07:37:11  Sysbench data load                                                                                  [ ✔ ]
07:37:11  Initiated sysbench oltp run                                                                         [ ✔ ]
07:37:21  Restarted cluster node for crash recovery                                                           [ ✔ ]
07:37:30  Cluster recovery is successful                                                                      [ ✔ ]
07:37:39  Restarted cluster node for crash recovery                                                           [ ✔ ]
07:37:48  Cluster recovery is successful                                                                      [ ✔ ]
07:37:48  pt-table-checksum error code : --pid file exists and the PID is running                             [ ✘ ]

PXC data consistency test between nodes
----------------------------------------
07:37:48  Startup sanity check                                                                                [ ✔ ]
07:37:48  Configuration file creation                                                                         [ ✔ ]
07:38:24  Initializing cluster                                                                                [ ✔ ]
07:38:45  Cluster startup                                                                                     [ ✔ ]
07:38:45  Database connection                                                                                 [ ✔ ]
07:38:45  Replication QA sysbench run sanity check                                                            [ ✔ ]
07:38:47  Replication QA sysbench data load                                                                   [ ✔ ]
07:38:47  Sample DB creation                                                                                  [ ✔ ]
07:38:49  Sample data load                                                                                    [ ✔ ]
07:39:00  RQG data load                                                                                       [ ✔ ]
07:39:00  pt-table-checksum error code : --pid file exists and the PID is running                             [ ✘ ]

PXC ChaosMonkey Style test
----------------------------
07:39:00  Startup sanity check                                                                                [ ✔ ]
07:39:00  Configuration file creation                                                                         [ ✔ ]
07:40:46  Initializing cluster                                                                                [ ✔ ]
07:42:24  Cluster startup                                                                                     [ ✔ ]
07:42:24  Database connection                                                                                 [ ✔ ]
07:42:24  Sysbench run sanity check                                                                           [ ✔ ]
07:42:26  Sysbench data load                                                                                  [ ✔ ]
07:42:26  Initiated sysbench oltp run                                                                         [ ✔ ]
07:42:27  Killed Cluster Node3 for ChaosMonkey QA                                                             [ ✔ ]
07:42:28  Killed Cluster Node2 for ChaosMonkey QA                                                             [ ✔ ]
07:42:28  Killed sysbench oltp run                                                                            [ ✔ ]
07:42:38  Restarting Cluster Node3                                                                            [ ✔ ]
07:42:43  Restarting Cluster Node2                                                                            [ ✔ ]
07:42:50  pt-table-checksum run status                                                                        [ ✔ ]
$
```
