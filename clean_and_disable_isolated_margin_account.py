import time
from datetime import datetime

from binance.client import Client
from helpers.parameters import parse_args, load_config
from helpers.handle_creds import load_correct_creds
# from binance_detect_moonings import use_actual_balance_for_pair_with
from db_connection import connect, table_last_sold_pairs_data_read_data

args = parse_args()
DEFAULT_CONFIG_FILE = 'config.yml'
DEFAULT_CREDS_FILE = 'creds.yml'
config_file = args.config if args.config else DEFAULT_CONFIG_FILE
creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
parsed_config = load_config(config_file)
parsed_creds = load_config(creds_file)
PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
TIME_SLEEP = 20 * 60  # 20 min

# Load creds for correct environment
access_key, secret_key = load_correct_creds(parsed_creds)
client = Client(access_key, secret_key)
connect = connect()
import json
def disable_isolated_margin_account(symbol=''):
    return client._request_margin_api('delete', 'margin/isolated/account', signed=True, data={'symbol': symbol})

# def enable_isolated_margin_account(symbol=''):
#     try:
#         client._request_margin_api('post', 'margin/isolated/create', signed=True, data={'symbol': symbol})
#     except Exception as e:
#         pass


# def transfer_and_disable():
#     if free_quote_money != '0':
#         client.transfer_isolated_margin_to_spot(asset=PAIR_WITH,
#                                                 symbol=symbol,
#                                                 amount=free_quote_money)
#     if free_base_money != '0':
#         client.transfer_isolated_margin_to_spot(asset=symbol[:-len(PAIR_WITH)],  # base coin name
#                                                 symbol=symbol,
#                                                 amount=free_base_money)
#     disable_isolated_margin_account(symbol=symbol)


# if __name__ == '__main__':
#     try:
#         # client.enable_isolated_margin_account(symbol='LSKUSDT')
#         client._request_margin_api('post', 'margin/isolated/account', True, data={'symbol':'LSKUSDT' })
#     except Exception as e:
#         print(e)
import time
from datetime import datetime

# from binance.client import Clientisolated_margin_account
from helpers.parameters import parse_args, load_config
from helpers.handle_creds import load_correct_creds
# from binance_detect_moonings import use_actual_balance_for_pair_with
from db_connection import connect, table_last_sold_pairs_data_read_data

args = parse_args()
DEFAULT_CONFIG_FILE = 'config.yml'
DEFAULT_CREDS_FILE = 'creds.yml'
config_file = args.config if args.config else DEFAULT_CONFIG_FILE
creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
parsed_config = load_config(config_file)
parsed_creds = load_config(creds_file)
PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
TIME_SLEEP = 20 * 60  # 20 min

# Load creds for correct environment# if __name__ == '__main__':
#     try:
#         # client.enable_isolated_margin_account(symbol='LSKUSDT')
#         client._request_margin_api('post', 'margin/isolated/account', True, data={'symbol':'LSKUSDT' })
#     except Exception as e:
#         print(e)

access_key, secret_key = load_correct_creds(parsed_creds)
client = Client(access_key, secret_key)
connect = connect()

def disable_isolated_margin_account(symbol=''):
    return client._request_margin_api('delete', 'margin/isolated/account', signed=True, data={'symbol': symbol})

# def enable_isolated_margin_account(symbol=''):
#     try:
#         client._request_margin_api('post', 'margin/isolated/create', signed=True, data={'symbol': symbol})
#     except Exception as e:
#         pass


# def transfer_and_disable():
#     if free_quote_money != '0':
#         client.transfer_isolated_margin_to_spot(asset=PAIR_WITH,
#                                                 symbol=symbol,
#                                                 amount=free_quote_money)
#     if free_base_money != '0':
#         client.transfer_isolated_margin_to_spot(asset=symbol[:-len(PAIR_WITH)],  # base coin name
#                                                 symbol=symbol,
#                                                 amount=free_base_money)
#     disable_isolated_margin_account(symbol=symbol)



def check_coin_for_disable(curr_coin=''):
    active_isolated_margin_accounts = [ curr_isolated_margin_account.get('symbol') for curr_isolated_margin_account in client.get_isolated_margin_account().get('assets')]
    isolated_margin_accounts_for_disable = active_isolated_margin_accounts
    coins_bought_file_path = 'coins_bought.json'
    with open(coins_bought_file_path) as coins_bought_data:
        coins_bought_dict = json.load(coins_bought_data)
        if coins_bought_dict:
            coins_in_progress = [coin_data.get('symbol') for coin_name, coin_data in coins_bought_dict.items() if
                                 coin_data.get('isolated_margin_volume')]
            isolated_margin_accounts_for_disable = list(set(active_isolated_margin_accounts) - set(coins_in_progress))
    return True if curr_coin in isolated_margin_accounts_for_disable else False


if __name__ == '__main__':
    try:
        #https://binance-docs.github.io/apidocs/spot/en/#enable-isolated-margin-account-trade
        # Enable isolated margin account for a specific symbol(Only supports activation of previously disabled accounts).
        #we can send this command a few times without any error
        # client._request_margin_api('post', 'margin/isolated/account', True, data={'symbol':'LUNAUSDT' }) # works correctly

        # this func works correctly but if we have not an opportunity to disable isolated_margin_account we will have an error:
        #APIError(code=-1003): Too many requests; current request has limited.
        # disable_isolated_margin_account(symbol='LUNAUSDT')

        active_isolated_margin_accounts = client.get_isolated_margin_account().get('assets')
        # for active_isolated_margin_accounts












    except Exception as e:
        print(e)

    # while True:
    #     for curr_id, symbol, last_sold_time in table_last_sold_pairs_data_read_data(conn=connect):
    #         # from isolated to spot
    #         account_data = client.get_isolated_margin_account(symbols=symbol)
    #         free_quote_money = account_data['assets'][0]['quoteAsset']['free']
    #         free_base_money = account_data['assets'][0]['baseAsset']['free']
    #         if free_quote_money == '0' and free_base_money == '0':
    #             continue
    #         try:
    #             transfer_and_disable()
    #         except Exception as e:
    #             if e.message == 'This isolated margin pair is disabled. Please activate it.':
    #                 enable_isolated_margin_account(symbol=symbol)
    #                 transfer_and_disable()
    #
    #     time.sleep(TIME_SLEEP)






# create_isolated_margin_account(self, **params)
    # while True:
    #     for curr_id, symbol, last_sold_time in table_last_sold_pairs_data_read_data(conn=connect):
    #         # from isolated to spot
    #         account_data = client.get_isolated_margin_account(symbols=symbol)
    #         free_quote_money = account_data['assets'][0]['quoteAsset']['free']
    #         free_base_money = account_data['assets'][0]['baseAsset']['free']
    #         if free_quote_money == '0' and free_base_money == '0':
    #             continue
    #         try:
    #             transfer_and_disable()
    #         except Exception as e:
    #             if e.message == 'This isolated margin pair is disabled. Please activate it.':
    #                 enable_isolated_margin_account(symbol=symbol)
    #                 transfer_and_disable()
    #
    #     time.sleep(TIME_SLEEP)






# create_isolated_margin_account(self, **params)