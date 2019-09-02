import configparser

# Reading initial configuration
config = configparser.ConfigParser()
config.read('config.ini')

WORKDIR = config['config']['workdir']
BASEDIR = config['config']['basedir']
NODE = config['config']['node']
USER = config['config']['user']
NODE1_SOCKET = config['config']['node1_socket']
NODE2_SOCKET = config['config']['node2_socket']
NODE3_SOCKET = config['config']['node3_socket']
PS1_SOCKET = config['config']['ps1_socket']
PS2_SOCKET = config['config']['ps2_socket']
PS3_SOCKET = config['config']['ps3_socket']
PT_BASEDIR = config['config']['pt_basedir']
SYSBENCH_USER = config['sysbench']['sysbench_user']
SYSBENCH_PASS = config['sysbench']['sysbench_pass']
SYSBENCH_DB = config['sysbench']['sysbench_db']
SYSBENCH_TABLE_COUNT = config['sysbench']['sysbench_table_count']
SYSBENCH_THREADS = config['sysbench']['sysbench_threads']
SYSBENCH_NORMAL_TABLE_SIZE = config['sysbench']['sysbench_normal_table_size']
SYSBENCH_RUN_TIME = config['sysbench']['sysbench_run_time']
SYSBENCH_LOAD_TEST_TABLE_SIZE = config['sysbench']['sysbench_load_test_table_size']
SYSBENCH_RANDOM_LOAD_TABLE_SIZE = config['sysbench']['sysbench_random_load_table_size']
SYSBENCH_RANDOM_LOAD_RUN_TIME = config['sysbench']['sysbench_random_load_run_time']
SYSBENCH_OLTP_TEST_TABLE_SIZE = config['sysbench']['sysbench_oltp_test_table_size']
SYSBENCH_READ_QA_TABLE_SIZE = config['sysbench']['sysbench_read_qa_table_size']
SYSBENCH_CUSTOMIZED_DATALOAD_TABLE_SIZE = config['sysbench']['sysbench_customized_dataload_table_size']
PXC_LOWER_BASE = config['upgrade']['pxc_lower_base']
PXC_UPPER_BASE = config['upgrade']['pxc_upper_base']
