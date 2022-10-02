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


def disable_isolated_margin_account(symbol=''):
    return client._request_margin_api('delete', 'margin/isolated/account', signed=True, data={'symbol': symbol})


if __name__ == '__main__':
    while True:
        for curr_id, symbol, last_sold_time in table_last_sold_pairs_data_read_data(conn=connect):
            # from isolated to spot
            account_data = client.get_isolated_margin_account(symbols=symbol)
            free_quote_money = account_data['assets'][0]['quoteAsset']['free']
            free_base_money = account_data['assets'][0]['baseAsset']['free']

            client.transfer_isolated_margin_to_spot(asset=PAIR_WITH,
                                                    symbol=symbol,
                                                    amount=free_quote_money)

            client.transfer_isolated_margin_to_spot(asset=symbol[:-len(PAIR_WITH)],  # base coin name
                                                    symbol=symbol,
                                                    amount=free_base_money)

            disable_isolated_margin_account(symbol=symbol)

        time.sleep(TIME_SLEEP)
