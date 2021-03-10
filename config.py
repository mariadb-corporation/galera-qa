import configparser

# Reading initial configuration
config = configparser.ConfigParser()
config.read('config.ini')

WORKDIR = config['config']['workdir']
BASEDIR = config['config']['basedir']
SERVER = config['config']['server']
NODE = config['config']['node']
USER = config['config']['user']
MD1_SOCKET = config['config']['md1_socket']
MD2_SOCKET = config['config']['md2_socket']
MD3_SOCKET = config['config']['md3_socket']
PT_BASEDIR = config['config']['pt_basedir']
PQUERY_BIN = config['config']['pquery_bin']
PQUERY_GRAMMER_FILE = config['config']['pquery_grammer_file']
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
GALERA_LOWER_BASE = config['upgrade']['galera_lower_base']
GALERA_UPPER_BASE = config['upgrade']['galera_upper_base']
