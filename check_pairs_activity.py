import time
from datetime import datetime

from db_connection import (connect,
                           table_last_sold_pairs_data_read_data_by_pair_name,
                           table_last_sold_pairs_data_read_data,
                           table_last_sold_pairs_data_del_old_data
                           )

activity_time = 2 * 60 * 60  # 2 hours in secs


def check_coin_pair_activity(connect=None, pair_names=None):
    data_list = table_last_sold_pairs_data_read_data_by_pair_name(conn=connect,
                                                                  pair_names=pair_names)  # list of lists [[id, pair_name, last_sold_time]]
    if data_list:
        if data_list == 'error in the table for store last_sold_pairs_data_by_pair_name':
            return False
        try:
            data_list = [[curr_id, pair_name, int(last_sold_time)] for curr_id, pair_name, last_sold_time in data_list]
            # find the most new line with the current coin pair
            data_list.sort(key=lambda x: x[2])
            most_new_data = data_list[-1]
            curr_id, pair_name, last_sold_time = most_new_data
            curr_unix_time = time.mktime(datetime.now().timetuple())
            if last_sold_time <= curr_unix_time - activity_time:  # last selling of this coin pair was more than 2 hours ago
                return True
            else:
                return False
        except Exception as e:
            return False
    else:
        # coin pair are not present in the db table (2 cases.
        # 1. script doesn't  use this pair any time.
        # 2.  data of this pair  was deleted automatically -- it was too old.
        # in both of cases we can use  this pair  now again)
        return True


def del_coin_pair_with_old_activity(connect=None):
    data_list = table_last_sold_pairs_data_read_data(conn=connect)
    if data_list:
        if data_list == 'error in the table for store last_sold_pairs_data':
            return False
        try:
            data_list = [[curr_id, pair_name, int(last_sold_time)] for curr_id, pair_name, last_sold_time in data_list]
            curr_unix_time = time.mktime(datetime.now().timetuple())
            out_ids = []
            for curr_data in data_list:
                curr_id, pair_name, last_sold_time = curr_data
                if last_sold_time <= curr_unix_time - activity_time:  # last selling of this coin pair was more than 2 hours ago
                    out_ids.append(curr_id)
            if out_ids:
                table_last_sold_pairs_data_del_old_data(conn=connect, ids=out_ids)
        except Exception as e:
            print(e)
            return False

def core_func():
    # check_coin_pair_activity(connect=connect, pair_names=['BNBUSDT'])
    while True:
        del_coin_pair_with_old_activity(connect=connect)
        time.sleep(3600)



connect = connect()
if __name__ == '__main__':
    core_func()
