import time
from datetime import datetime
from db_connection import (connect,
                           table_script_management_read_data,
                           table_script_management_write_data,
                           table_calculate_efficiency_read_data,
                           table_calculate_efficiency_write_data,
                           table_last_sold_pairs_data_write_new_data,
                           table_last_sold_pairs_data_read_data_by_pair_name,

                           table_margin_buy_sell_custom_signal_read_data,
                           table_margin_buy_sell_custom_signal_set_default_value,
                           table_margin_buy_sell_custom_signal_write_data
                           )
from binance_detect_moonings import check_pair_name_from_table_margin_buy_sell_custom_signal
from check_pairs_activity import check_coin_pair_activity

connect = connect()
curr_unix_time = int(time.mktime(datetime.now().timetuple()))
curr_minus_delta_time = curr_unix_time - 20 * 60

def processing_coins_data_from_db():
    '''
    return: coins list
    '''
    return []

def check_efficiency(coin=''):
    # coin = check_pair_name_from_table_margin_buy_sell_custom_signal()
    # if coin:
    if check_coin_pair_activity(connect=connect, pair_names=[coin]):
        efficiency_coef, positive_set, efficiency_coef_processed_time, positive_set_processed_time = table_calculate_efficiency_read_data(
            conn=connect)
        if (float(efficiency_coef) > 0.8 and int(efficiency_coef_processed_time) >= curr_minus_delta_time) or \
                (positive_set and int(positive_set_processed_time) >= curr_minus_delta_time):
            return True
    return False

while True:
    for coin in processing_coins_data_from_db():
        check_efficiency(coin=coin)
        time.sleep(1)




# https://github.com/TechDivisions/python-binance-streamer/blob/main/binance-streamer.py
# https://www.youtube.com/watch?v=HdZLDXtF_rQ
#https://www.youtube.com/watch?v=Q4c2wCACRL8

 # we need to cpose and reopen ws  each 23 hours
# https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md#general-wss-information


# https://stackoverflow.com/questions/71279168/how-to-stop-python-websocket-connection-after-some-seconds
# https://stackoverflow.com/questions/52692736/how-to-manually-close-a-websocket

