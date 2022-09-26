import time
from datetime import datetime

from binance.client import Client
from helpers.parameters import parse_args, load_config
from helpers.handle_creds import load_correct_creds

args = parse_args()
DEFAULT_CONFIG_FILE = 'config.yml'
DEFAULT_CREDS_FILE = 'creds.yml'
config_file = args.config if args.config else DEFAULT_CONFIG_FILE
creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
parsed_config = load_config(config_file)
parsed_creds = load_config(creds_file)

TICKERS_LIST = parsed_config['trading_options']['TICKERS_LIST']
PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
# Load creds for correct environment
access_key, secret_key = load_correct_creds(parsed_creds)
client = Client(access_key, secret_key)


# https://python-binance.readthedocs.io/en/latest/margin.html

def create_isolated_margin_account():
    tickers = [line.strip() for line in open(TICKERS_LIST)]
    for ticker in tickers:
        try:
            account = client.create_isolated_margin_account(base=ticker, quote=PAIR_WITH)
            print('success for creating account {}{}'.format(ticker, PAIR_WITH))
        except Exception as e:
            print(e)
            print('base={}'.format(ticker))
            continue


def transfer_spot_to_isolated_margin():
    '''
    https://python-binance.readthedocs.io/en/latest/margin.html#id17
    '''
    try:
        before_unix_time = int(time.mktime(datetime.now().timetuple()))
        transaction = client.transfer_spot_to_isolated_margin(asset=PAIR_WITH,
                                                              symbol='{}{}'.format('LUNA', PAIR_WITH), amount='0.5')
        after_unix_time = int(time.mktime(datetime.now().timetuple()))
        processing_time = after_unix_time - before_unix_time
        print("before_time = {}".format(before_unix_time))
        print("after_time = {}".format(after_unix_time))
        print("processing_time = {}".format(processing_time))

    except Exception as e:
        print(e)


def transfer_isolated_margin_to_spot():
    '''
    https://python-binance.readthedocs.io/en/latest/margin.html#id18
    '''
    try:
        transaction = client.transfer_isolated_margin_to_spot(asset=PAIR_WITH,
                                                              symbol='{}{}'.format('LUNA', PAIR_WITH),
                                                              amount='1.5')
    except Exception as e:
        print(e)


if __name__ == '__main__':
    pass
    # Your request is no longer supported. Margin account creation can be completed directly through Margin account transfer.
    # create_isolated_margin_account()
    #transfer_spot_to_isolated_margin()  # it is work   processing_time  less than 1 sec
     # transfer_isolated_margin_to_spot()  # it is work
