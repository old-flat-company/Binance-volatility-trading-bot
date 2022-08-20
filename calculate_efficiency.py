import os
import time
from datetime import datetime

# CHECKING_TIME = 3600  # in sec
# STANDARD_COEFF = 3 / 1
# MIN_NUM_RESULTS = 4
# LAST_RESULT_SET=3

# Load helper modules
from helpers.parameters import (
    parse_args, load_config
)

# Load arguments then parse settings
args = parse_args()
DEFAULT_CONFIG_FILE = 'config.yml'
config_file = args.config if args.config else DEFAULT_CONFIG_FILE
parsed_config = load_config(config_file)

TEST_MODE = parsed_config['script_options']['TEST_MODE']
EFFICIENCY_FILE = parsed_config['script_options']['EFFICIENCY_FILE']

CHECKING_TIME = parsed_config['calculate_efficiency_options']['CHECKING_TIME']
STANDARD_COEFF = parsed_config['calculate_efficiency_options']['STANDARD_COEFF']
MIN_NUM_RESULTS = parsed_config['calculate_efficiency_options']['MIN_NUM_RESULTS']
LAST_RESULT_SET = parsed_config['calculate_efficiency_options']['LAST_RESULT_SET']


def calculate_positive_negative(last_data_list=[]):
    positive_res = 0
    negative_res = 0
    for last_data in last_data_list:
        curr_unix_time, curr_res, human_date, coef = last_data.split('\t')
        if curr_res == '+':
            positive_res += 1
        else:
            negative_res += 1
    return positive_res, negative_res


def calculate_last_positive_negative():
    now_unix_time = int(time.mktime(datetime.now().timetuple()))
    # last results
    last_data_list = [line_data.strip() for line_data in open(efficiency_log_path(), 'r')
                      if now_unix_time - int(float(line_data.strip().split('\t')[0])) <= CHECKING_TIME]
    if len(last_data_list) >= LAST_RESULT_SET:
        last_data_list = last_data_list[::-1][:LAST_RESULT_SET]
        positive_res, negative_res = calculate_positive_negative(last_data_list=last_data_list)
        return (True, now_unix_time) if positive_res >= LAST_RESULT_SET else (False, now_unix_time)
    return (False, now_unix_time)


def calculate_positive_negative_checking_time():
    now_unix_time = int(time.mktime(datetime.now().timetuple()))
    # int(line_data.strip().split('\t')[0])  -- unix time
    # last 1 hour  data
    last_data_list = [line_data.strip() for line_data in open(efficiency_log_path(), 'r')
                      if now_unix_time - int(float(line_data.strip().split('\t')[0])) <= CHECKING_TIME]

    return calculate_positive_negative(last_data_list=last_data_list)


def calculate_efficiency():
    positive_res, negative_res = calculate_positive_negative_checking_time()
    sum_results = positive_res + negative_res
    if sum_results < MIN_NUM_RESULTS:
        return 'It is too little number of results  during last 1 hour: {0}'.format(sum_results)
    curr_coeff = positive_res / negative_res / STANDARD_COEFF
    return "curr_coeff : {0}\t positive_res : {1}\tnegative_res : {2}".format(curr_coeff, positive_res, negative_res)


def calculate_efficiency_lib(curr_res):
    positive_res, negative_res = calculate_positive_negative_checking_time()
    curr_unix_time = int(time.mktime(datetime.now().timetuple()))
    if curr_res == "+":
        positive_res += 1
    elif curr_res == "-":
        negative_res += 1
    sum_results = positive_res + negative_res
    if sum_results < MIN_NUM_RESULTS:
        return '0.0', str(curr_unix_time)  # 'It is too little number of results  during last 1 hour: {0}'.format(sum_results)
    if negative_res:
        curr_coeff = positive_res / negative_res / STANDARD_COEFF
    else:
        curr_coeff = positive_res / STANDARD_COEFF

    return str(curr_coeff), str(curr_unix_time)



def efficiency_log_path():
    efficiency_log_path = 'test_' + EFFICIENCY_FILE if TEST_MODE else EFFICIENCY_FILE
    if not os.path.exists(efficiency_log_path):
        with open(efficiency_log_path, 'w') as file:  # create a file
            file.close()
    return efficiency_log_path


def efficiency_log(curr_unix_time=int(), efficiency_result='', efficiency_coeff=None):
    curr_time = datetime.utcfromtimestamp(curr_unix_time).strftime('%Y-%m-%d %H:%M:%S')
    with open(efficiency_log_path(), 'a+') as f:
        out_line = '{0}\t{1}\t{2}\t{3}\n'.format(curr_unix_time, efficiency_result, curr_time, efficiency_coeff)
        f.write(out_line)


if __name__ == '__main__':
    try:
        print(calculate_efficiency())
    except Exception as e:
        print(e)
