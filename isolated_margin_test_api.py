import time
from datetime import datetime

from binance.client import Client
from helpers.parameters import parse_args, load_config
from helpers.handle_creds import load_correct_creds
# from binance_detect_moonings import use_actual_balance_for_pair_with

args = parse_args()
DEFAULT_CONFIG_FILE = 'config.yml'
DEFAULT_CREDS_FILE = 'creds.yml'
config_file = args.config if args.config else DEFAULT_CONFIG_FILE
creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
parsed_config = load_config(config_file)
parsed_creds = load_config(creds_file)

TICKERS_LIST = parsed_config['trading_options']['TICKERS_LIST']
PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
STATUS = parsed_config['script_options'].get('STATUS')
USE_CURRENT_BALANCE_FOR_PAIR_WITH = parsed_config['trading_options']['USE_CURRENT_BALANCE_FOR_PAIR_WITH']
TEST_MODE = parsed_config['script_options']['TEST_MODE']

# Load creds for correct environment
access_key, secret_key = load_correct_creds(parsed_creds)
client = Client(access_key, secret_key)

def use_actual_balance_for_pair_with():
    if STATUS == 'main' and USE_CURRENT_BALANCE_FOR_PAIR_WITH and not TEST_MODE:
        return int(float(client.get_asset_balance(asset=PAIR_WITH)['free']))
    else:
        return parsed_config['trading_options']['QUANTITY']

QUANTITY = use_actual_balance_for_pair_with()


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
        print('transaction tranId')
        print(transaction.get('tranId'))

    except Exception as e:
        print(e)


def get_isolated_margin_account_quote_asset_free_money(symbol=''):
    account_data=client.get_isolated_margin_account(symbols=symbol)
    res=account_data['assets'][0]['quoteAsset']['free']
    print(res)
    return res

def get_isolated_margin_account_base_asset_free_money(symbol=''):
    account_data = client.get_isolated_margin_account(symbols=symbol)
    res=account_data['assets'][0]['baseAsset']['free']
    print(res)
    return  res


def asset_with_correct_step_size(asset=None, symbol=''):
    info = client.get_symbol_info(symbol)
    step_size = info['filters'][2]['stepSize']
    lot_size = step_size.index('1') - 1
    if lot_size < 0:
        lot_size = 0
    # return int(asset) if lot_size == 0 else float('{:.{}f}'.format(float(asset), lot_size))
    from decimal import Decimal, ROUND_DOWN
    number = Decimal(str(asset))
    number = number.quantize(Decimal('1.{}'.format(''.join(['0' for i in range(lot_size)]))), rounding=ROUND_DOWN)
    number = float(number)
    return number

def transfer_isolated_margin_to_spot():
    '''
    https://python-binance.readthedocs.io/en/latest/margin.html#id18
    '''
    try:
        transaction = client.transfer_isolated_margin_to_spot(asset=PAIR_WITH,
                                                              symbol='{}{}'.format('LUNA', PAIR_WITH),
                                                              # amount='1.5'
                                                              amount=get_isolated_margin_account_quote_asset_free_money() # it is work
                                                              )
    except Exception as e:
        print(e)


def check_isolated_margin_symbols():
    active_isolated_margin_symbols = []
    pair_not_found_in_isolated_margin_symbols = []
    tickers = [line.strip() for line in open(TICKERS_LIST)]
    # tickers = ['MIR', 'ARRR', 'BTCST']
    for ticker in tickers:
        try:
            res = client.get_isolated_margin_symbol(symbol='{}{}'.format(ticker, PAIR_WITH))
            if res:
                active_isolated_margin_symbols.append(ticker)
                print(ticker)
        except Exception as e:
            if 'Pair not found' in e.message:
                pair_not_found_in_isolated_margin_symbols.append(ticker)
                continue
    # print(active_isolated_margin_symbols)
    print(pair_not_found_in_isolated_margin_symbols)


def get_symbol_info_min_money():
    tickers = [line.strip() for line in open(TICKERS_LIST)]
    for ticker in tickers:
        symbol = '{}{}'.format(ticker, PAIR_WITH)
        last_price = float(client.get_ticker(symbol=symbol).get('lastPrice'))
        price_usdt = float(client.get_ticker(symbol=symbol).get('lastPrice')) * QUANTITY
        info = client.get_symbol_info(symbol)
        print('symbol: {} minQty:{} last_price:{}'.format(symbol, info['filters'][2]['minQty'], last_price))
        # print('{}{} in usdt'.format(symbol, info['filters'][2]['minQty']), price_usdt)


def disable_isolated_margin_account(symbol=''):
    return client._request_margin_api('delete', 'margin/isolated/account', signed=True, data={'symbol': symbol})





def enable_isolated_margin_account(symbol=''):
    # turn on an account that already was activated but now it in the disable stage.
    try:
        # we can send this command a few times without any error
        client._request_margin_api('post', 'margin/isolated/account', True, data={'symbol': symbol})
        client.transfer_spot_to_isolated_margin(asset=PAIR_WITH,
                                                symbol=symbol,
                                                # amount=str(QUANTITY))
                                                amount=str(0.5))
        return True
    except Exception as e:
        print(e)
        return False

def activate_isolated_margin_account(symbol=''):
    try:
        client.transfer_spot_to_isolated_margin(asset=PAIR_WITH,
                                                symbol=symbol,
                                                # amount=str(QUANTITY))
                                                amount=str(0.5))
        return True
    except Exception as e:
        print(e)
        return False

def activate_or_enable_isolated_margin_account(symbol=''):
    if activate_isolated_margin_account(symbol=symbol):
        return True
    else:
        return enable_isolated_margin_account(symbol=symbol)


def get_sma(symbol='', period=7, interval=Client.KLINE_INTERVAL_1MINUTE, depth=0):
    """
    https://python-binance.readthedocs.io/en/latest/binance.html?highlight=get_historical_klines#binance.client.Client.get_historical_klines
    # list of OHLCV values (Open time, Open, High, Low, Close, Volume, Close time, Quote asset volume, Number of trades, Taker buy base asset volume, Taker buy quote asset volume, Ignore)
     """
    klines = client.get_historical_klines(symbol,  interval, '1 hour ago UTC')
    # print(klines)
    #last candles(period)data
    if depth == 0:
        period_klines = klines[-(period):]
    else:
        period_klines = klines[-(period) - depth:-depth]
    period_klines_close_data = [float(kline_data[4]) for kline_data in period_klines]
    # print(period_klines_close_data)
    return sum(period_klines_close_data)/period


def sma_based_buy_sell_signal(symbol='', interval=Client.KLINE_INTERVAL_1MINUTE):
    klines_data = client.get_historical_klines(symbol, interval, '1 hour ago UTC')
    curr_price = float(klines_data[-2][4])
    price_prev = float(klines_data[-3][4])
    curr_sma = get_sma(symbol=symbol, depth=1)
    sma_prev = get_sma(symbol=symbol, depth=2)
    # buy
    if curr_price == curr_sma and price_prev == sma_prev:
        return False
    elif curr_price >= curr_sma and price_prev <= sma_prev:
        return 'buy'
    elif curr_price <= curr_sma and price_prev >= sma_prev:
        return 'sell'
    else:
        return False

if __name__ == '__main__':
    # activate_or_enable_isolated_margin_account(symbol='PUNDIXUSDT')
    # pass
    # print(get_sma(symbol='PUNDIXUSDT'))
    while True:
        print(sma_based_buy_sell_signal(symbol='BNBUSDT'))
        print(datetime.now().strftime("%d/%m %H:%M:%S"))
        time.sleep(5)

        # klines_data = client.get_historical_klines('BNBUSDT', Client.KLINE_INTERVAL_1MINUTE, '1 hour ago UTC')
        # curr_price = float(klines_data[-1][4])
        # price_prev = float(klines_data[-2][4])
        # curr_sma = get_sma(symbol='BNBUSDT')
        # sma_prev = get_sma(symbol='BNBUSDT', depth=1)
        #
        # print('curr_price', curr_price)
        # print('price_prev', price_prev)
        # print('curr_sma', curr_sma)
        # print('sma_prev', sma_prev)
        # time.sleep(5)





    # Your request is no longer supported. Margin account creation can be completed directly through Margin account transfer.
    # create_isolated_margin_account()
    # transfer_spot_to_isolated_margin()  # it is work   processing_time  less than 1 sec
     # transfer_isolated_margin_to_spot()  # it is work

    # print(client.get_isolated_margin_account(symbols='{}{}'.format('LUNA', PAIR_WITH))) # it is work
    # new_res = {'assets': [{'baseAsset': {'asset': 'LUNA',
    #                                      'borrowEnabled': True,
    #                                      'borrowed'client.get_isolated_margin_account(symbols='{}{}'.format('LUNA', PAIR_WITH)): '0',
    #                                      'free': '0',
    #                                      'interest': '0',
    #                                      'locked': '0',
    #                                      'netAsset': '0',
    #                                      'netAssetOfBtc': '0',
    #                                      'repayEnabled': True,
    #                                      'totalAsset': '0'},
    #
    #                        'quoteAsset': {'asset': 'USDT',
    #                                       'borrowEnabled': True,
    #                                       'borrowed': '0',
    #                                       'free': '0.5',   #  important data
    #                                       'interest': '0',
    #                                       'locked': '0',
    #                                       'netAsset': '0.5',
    #                                       'netAssetOfBtc': '0.0000265',
    #                                       'repayEnabled': True,
    #                                       'totalAsset': '0.5'},
    #                        'symbol': 'LUNAUSDT',
    #                        'isolatedCreated': True,
    #                        'marginLevel': '999',
    #                        'marginLevelStatus': 'EXCESSIVE',
    #                        'marginRatio': '5',
    #                        'indexPrice': '2.21903125',
    #                        'liquidatePrice': '0',
    #                        'liquidateRate': '0',
    #                        'tradeEnabled': True,transfer_isolated_margin_to_spot()
    #                        'enabled': True}]}
    # print(get_isolated_margin_account_quote_asset_free_money()) # it is isolated_margin_symbolwork
    # transfer_isolated_margin_to_spot()
# print(client.get_isolated_margin_symbol(symbol='{}{}'.format('MIR', PAIR_WITH)))
# check_isolated_margin_symbols()
#     get_symbol_info_min_money()



    # print(asset_with_correct_step_size(asset=get_isolated_margin_account_base_asset_free_money(symbol='LUNAUSDT'),
    #                              symbol='LUNAUSDT') )
    #
    # print(asset_with_correct_step_size(asset=get_isolated_margin_account_quote_asset_free_money(symbol='LUNAUSDT'),
    #                              symbol='LUNAUSDT'))
    # disable_isolated_margin_account(symbol='LUNAUSDT')
