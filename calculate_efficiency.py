from datetime import datetime
import time

CHECKING_TIME = 3600  # in sec
STANDARD_COEFF = 3 / 1
MIN_NUM_RESULTS = 4

def calculate_positive_negative():
    now_unix_time = int(time.mktime(datetime.now().timetuple()))
    # int(line_data.strip().split('\t')[0])  -- unix time
    # last 1 hour  data
    last_data_list = [line_data.strip() for line_data in open("efficiency_log.txt", 'r')
                      if now_unix_time - int(float(line_data.strip().split('\t')[0])) <= CHECKING_TIME]
    positive_res = 0
    negative_res = 0
    for last_data in last_data_list:
        curr_unix_time, curr_res, human_date, coef = last_data.split('\t')
        if curr_res == '+':
            positive_res += 1
        else:
            negative_res += 1
    return positive_res, negative_res


def calculate_efficiency():
    positive_res, negative_res = calculate_positive_negative()
    sum_results = positive_res + negative_res
    if sum_results < MIN_NUM_RESULTS:
        return 'It is too little number of results  during last 1 hour: {0}'.format(sum_results)
    curr_coeff = positive_res / negative_res / STANDARD_COEFF
    return "curr_coeff : {0}\t positive_res : {1}\tnegative_res : {2}".format(curr_coeff, positive_res, negative_res)


def calculate_efficiency_lib(curr_res):
    positive_res, negative_res = calculate_positive_negative()
    if curr_res == "+":
        positive_res += 1
    elif curr_res == "-":
        negative_res += 1
    sum_results = positive_res + negative_res
    if sum_results < MIN_NUM_RESULTS:
        return 'It is too little number of results  during last 1 hour: {0}'.format(sum_results)
    curr_coeff = positive_res / negative_res / STANDARD_COEFF
    return curr_coeff


if __name__ == '__main__':
    try:
        print(calculate_efficiency())
    except Exception as e:
        print(e)
