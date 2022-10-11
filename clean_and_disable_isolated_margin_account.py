import os
import time
from datetime import datetime
from binance.client import Client
from helpers.handle_creds import load_correct_creds
from helpers.parameters import parse_args, load_config
# from binance_detect_moonings import transfer_from_margin_to_spot

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

def transfer_from_margin_to_spot(symbol=''):
    try:
        account_data = client.get_isolated_margin_account(symbols=symbol)
        free_quote_money = account_data['assets'][0]['quoteAsset']['free']
        free_base_money = account_data['assets'][0]['baseAsset']['free']
        if free_quote_money == '0' and free_base_money == '0':
            return True
        if free_quote_money != '0':
            client.transfer_isolated_margin_to_spot(asset=PAIR_WITH,
                                                    symbol=symbol,
                                                    amount=free_quote_money)
        if free_base_money != '0':
            client.transfer_isolated_margin_to_spot(asset=symbol[:-len(PAIR_WITH)],  # base coin name
                                                    symbol=symbol,
                                                    amount=free_base_money)
        return True
    except Exception as e:
        print(e)
        return False

def disable_isolated_margin_account(symbol=''):
    return client._request_margin_api('delete', 'margin/isolated/account', signed=True, data={'symbol': symbol})


def disable_active_isolated_margin_accounts():
    print('disable_active_isolated_margin_accounts')
    print('time {}'.format(datetime.now().strftime("%d/%m %H:%M:%S")))
    print('--'*8)
    active_isolated_margin_pairs = [curr_isolated_margin_account.get('symbol') for curr_isolated_margin_account in client.get_isolated_margin_account().get('assets')]
    coins_bought_file_path = 'coins_bought.json'
    for symbol in active_isolated_margin_pairs:
        if os.stat(coins_bought_file_path).st_size <= 2:  # in the empty json file we have {}
            transfer_res=transfer_from_margin_to_spot(symbol=symbol)
            if not transfer_res:
                continue
            else:
                try:
                    disable_isolated_margin_account(symbol=symbol)
                except Exception as e:
                    print(e)
                    continue
        else:
            return

if __name__ == '__main__':
    while True:
        print('sleep 5 min')
        time.sleep(5 * 60)
        try:
            disable_active_isolated_margin_accounts()
            #https://binance-docs.github.io/apidocs/spot/en/#enable-isolated-margin-account-trade
            # Enable isolated margin account for a specific symbol(Only supports activation of previously disabled accounts).
            #we can send this command a few times without any error
            # client._request_margin_api('post', 'margin/isolated/account', True, data={'symbol':'LUNAUSDT' }) # works correctly

            # this func works correctly but if we have not an opportunity to disable isolated_margin_account we will have an error:
            #APIError(code=-1003): Too many requests; current request has limited.
            # disable_isolated_margin_account(symbol='LUNAUSDT')

            # active_isolated_margin_accounts = client.get_isolated_margin_account().get('assets')
            # for active_isolated_margin_accounts

             # transfer_from_margin_to_spot(symbol='MDXUSDT') # works correctl

        except Exception as e:
            print(e)
            continue