"""
Disclaimer

All investment strategies and investments involve risk of loss.
Nothing contained in this program, scripts, code or repositoy should be
construed as investment advice.Any reference to an investment's past or
potential performance is not, and should not be construed as, a recommendation
or as a guarantee of any specific outcome or profit.

By using this program you accept all liabilities,
and that no claims can be made against the developers,
or others connected with the program.
"""


# use for environment variables
import os

from decimal import Decimal, ROUND_DOWN

# use if needed to pass args to external modules
import sys

# used to create threads & dynamic loading of modules
import threading
import importlib

# used for directory handling
import glob

# Needed for colorful console output Install with: python3 -m pip install colorama (Mac/Linux) or pip install colorama (PC)
from colorama import init
init()

# needed for the binance API / websockets / Exception handling
from binance.client import Client
from binance.exceptions import BinanceAPIException
from requests.exceptions import ReadTimeout, ConnectionError

# used for dates
from datetime import date, datetime, timedelta
import time

# used to repeatedly execute the code
from itertools import count

# used to store trades and sell assets
import json

# Load helper modules
from helpers.parameters import (
    parse_args, load_config
)

# Load creds modules
from helpers.handle_creds import (
    load_correct_creds, test_api_key
)

from calculate_efficiency import (efficiency_log,
                                  calculate_efficiency_lib,
                                  calculate_last_positive_negative)
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

from check_pairs_activity import check_coin_pair_activity

# for colourful logging to the console
class txcolors:
    BUY = '\033[92m'
    WARNING = '\033[93m'
    SELL_LOSS = '\033[91m'
    SELL_PROFIT = '\033[32m'
    DIM = '\033[2m\033[35m'
    DEFAULT = '\033[39m'


# tracks profit/loss each session
global session_profit
session_profit = 0

connect = connect()

# print with timestamps
old_out = sys.stdout
class St_ampe_dOut:
    """Stamped stdout."""
    nl = True
    def write(self, x):
        """Write function overloaded."""
        if x == '\n':
            old_out.write(x)
            self.nl = True
        elif self.nl:
            old_out.write(f'{txcolors.DIM}[{str(datetime.now().replace(microsecond=0))}]{txcolors.DEFAULT} {x}')
            self.nl = False
        else:
            old_out.write(x)

    def flush(self):
        pass

sys.stdout = St_ampe_dOut()
#-----------custom indicators ------------------
def get_sma(symbol='', period=7, interval=Client.KLINE_INTERVAL_1MINUTE):
    """
    https://python-binance.readthedocs.io/en/latest/binance.html?highlight=get_historical_klines#binance.client.Client.get_historical_klines
    # list of OHLCV values (Open time, Open, High, Low, Close, Volume, Close time, Quote asset volume, Number of trades, Taker buy base asset volume, Taker buy quote asset volume, Ignore)
     """
    klines = client.get_historical_klines(symbol,  interval, '1 hour ago UTC')
    # print(klines)
    #last candles(period)data
    period_klines=klines[-(period):]
    period_klines_close_data = [float(kline_data[4]) for kline_data in period_klines]
    # print(period_klines_close_data)
    return sum(period_klines_close_data)/period
#-----------------------------------------------

def get_price(add_to_historical=True):
    '''Return the current price for all coins on binance'''

    global historical_prices, hsp_head

    initial_price = {}
    prices = client.get_all_tickers()

    for coin in prices:

        if CUSTOM_LIST:
            if any(item + PAIR_WITH == coin['symbol'] for item in tickers) and all(item not in coin['symbol'] for item in FIATS):
                initial_price[coin['symbol']] = { 'price': coin['price'], 'time': datetime.now()}
        else:
            if PAIR_WITH in coin['symbol'] and all(item not in coin['symbol'] for item in FIATS):
                initial_price[coin['symbol']] = { 'price': coin['price'], 'time': datetime.now()}

    if add_to_historical:
        hsp_head += 1

        if hsp_head == RECHECK_INTERVAL:
            hsp_head = 0

        historical_prices[hsp_head] = initial_price

    return initial_price


def wait_for_price():
    '''calls the initial price and ensures the correct amount of time has passed
    before reading the current price again'''

    global historical_prices, hsp_head, volatility_cooloff

    volatile_coins = {}
    externals = {}

    coins_up = 0
    coins_down = 0
    coins_unchanged = 0

    pause_bot()

    if historical_prices[hsp_head]['BNB' + PAIR_WITH]['time'] > datetime.now() - timedelta(minutes=float(TIME_DIFFERENCE / RECHECK_INTERVAL)):

        # sleep for exactly the amount of time required
        time.sleep((timedelta(minutes=float(TIME_DIFFERENCE / RECHECK_INTERVAL)) - (datetime.now() - historical_prices[hsp_head]['BNB' + PAIR_WITH]['time'])).total_seconds())

    #get price each 1 sec
    # time.sleep(1)
    # print(f'Working...Session profit:{session_profit:.2f}% Est:${(QUANTITY * session_profit)/100:.2f}')
    # retreive latest prices
    get_price()

    # calculate the difference in prices
    for coin in historical_prices[hsp_head]:

        # minimum and maximum prices over time period
        min_price = min(historical_prices, key = lambda x: float("inf") if x is None else float(x[coin]['price']))
        max_price = max(historical_prices, key = lambda x: -1 if x is None else float(x[coin]['price']))

        threshold_check = (-1.0 if min_price[coin]['time'] > max_price[coin]['time'] else 1.0) * (float(max_price[coin]['price']) - float(min_price[coin]['price'])) / float(min_price[coin]['price']) * 100

        # each coin with higher gains than our CHANGE_IN_PRICE is added to the volatile_coins dict if less than MAX_COINS is not reached.
        if threshold_check > CHANGE_IN_PRICE:
            coins_up +=1

            if coin not in volatility_cooloff:
                volatility_cooloff[coin] = datetime.now() - timedelta(minutes=TIME_DIFFERENCE)

            # only include coin as volatile if it hasn't been picked up in the last TIME_DIFFERENCE minutes already
            if datetime.now() >= volatility_cooloff[coin] + timedelta(minutes=TIME_DIFFERENCE):
                volatility_cooloff[coin] = datetime.now()

                if len(coins_bought) + len(volatile_coins) < MAX_COINS or MAX_COINS == 0:
                    volatile_coins[coin] = round(threshold_check, 3)
                    print(f'{coin} has gained {volatile_coins[coin]}% within the last {TIME_DIFFERENCE} minutes, calculating volume in {PAIR_WITH}')

                else:
                    print(f'{txcolors.WARNING}{coin} has gained {round(threshold_check, 3)}% within the last {TIME_DIFFERENCE} minutes, but you are holding max number of coins{txcolors.DEFAULT}')

        elif threshold_check < CHANGE_IN_PRICE:
            coins_down +=1

        else:
            coins_unchanged +=1

    # Disabled until fix
    #print(f'Up: {coins_up} Down: {coins_down} Unchanged: {coins_unchanged}')

    # Here goes new code for external signalling
    # externals = external_signals()
    # exnumber = 0
    #
    # for excoin in externals:
    #     if excoin not in volatile_coins and excoin not in coins_bought and \
    #             (len(coins_bought) + exnumber + len(volatile_coins)) < MAX_COINS:
    #         volatile_coins[excoin] = 1
    #         exnumber +=1
    #         print(f'External signal received on {excoin}, calculating volume in {PAIR_WITH}')

    return volatile_coins, len(volatile_coins), historical_prices[hsp_head]


def wait_for_price_from_db_table(custom_pair_name=''):
    '''calls the initial price and ensures the correct amount of time has passed
    before reading the current price again'''
    volatile_coins = {custom_pair_name: 1}
    last_price = {custom_pair_name:
                      {'price': client.get_symbol_ticker(symbol=custom_pair_name).get('price')}
                  }
    return volatile_coins, len(volatile_coins), last_price


def external_signals():
    external_list = {}
    signals = {}

    # check directory and load pairs from files into external_list
    signals = glob.glob("signals/*.exs")
    for filename in signals:
        for line in open(filename):
            symbol = line.strip()
            external_list[symbol] = symbol
        try:
            os.remove(filename)
        except:
            if DEBUG: print(f'{txcolors.WARNING}Could not remove external signalling file{txcolors.DEFAULT}')

    return external_list


def pause_bot():
    '''Pause the script when exeternal indicators detect a bearish trend in the market'''
    global bot_paused, session_profit, hsp_head

    # start counting for how long the bot's been paused
    start_time = time.perf_counter()

    while os.path.isfile("signals/paused.exc"):

        if bot_paused == False:
            print(f'{txcolors.WARNING}Pausing buying due to change in market conditions, stop loss and take profit will continue to work...{txcolors.DEFAULT}')
            bot_paused = True

        # Sell function needs to work even while paused
        coins_sold = sell_coins()
        remove_from_portfolio(coins_sold)
        get_price(True)

        # pausing here
        if hsp_head == 1: print(f'Paused...Session profit:{session_profit:.2f}% Est:${(QUANTITY * session_profit)/100:.2f}')
        time.sleep((TIME_DIFFERENCE * 60) / RECHECK_INTERVAL)

    else:
        # stop counting the pause time
        stop_time = time.perf_counter()
        time_elapsed = timedelta(seconds=int(stop_time-start_time))

        # resume the bot and ser pause_bot to False
        if  bot_paused == True:
            print(f'{txcolors.WARNING}Resuming buying due to change in market conditions, total sleep time: {time_elapsed}{txcolors.DEFAULT}')
            bot_paused = False

    return


def asset_with_correct_step_size(asset=None, symbol=''):
    info = client.get_symbol_info(symbol)
    step_size = info['filters'][2]['stepSize']
    lot_size = step_size.index('1') - 1
    if lot_size < 0:
        lot_size = 0
    number = Decimal(str(asset))
    number = number.quantize(Decimal('1.{}'.format(''.join(['0' for i in range(lot_size)]))), rounding=ROUND_DOWN)
    number = float(number)
    return number


def convert_volume(custom_pair_name=''):
    '''Converts the volume given in QUANTITY from USDT to the each coin's volume'''

    volatile_coins, number_of_coins, last_price = wait_for_price_from_db_table(custom_pair_name=custom_pair_name)

    volume = {}
    isolated_margin_volume = {}
    for coin in volatile_coins:
        #spot
        asset = float(QUANTITY / float(last_price[coin]['price']))
        volume[coin] = asset_with_correct_step_size(asset=asset, symbol=coin)
        isolated_margin_volume[coin] = ''
        if MARGIN:
            asset *= MARGIN_LEVERAGE_COEFFICIENT
            isolated_margin_volume[coin] = asset_with_correct_step_size(asset=asset, symbol=coin)

    return volume, isolated_margin_volume, last_price


# def correct_volume_with_step_size(symbol=''):
#     last_price = client.get_ticker(symbol=symbol).get('lastPrice')
#     return asset_with_correct_step_size(asset=float(QUANTITY / float(last_price)) * MARGIN_LEVERAGE_COEFFICIENT,
#                                         symbol=symbol)


def core_spot_buy(coin=None, volume=None, isolated_margin_volume=None, orders=None):
    try:
        buy_limit = client.create_order(symbol=coin,
                                        side='BUY',
                                        type='MARKET',
                                        # quantity=volume[coin])
                                        quantity=asset_with_correct_step_size(asset=volume[coin], symbol=coin))
        print('core_spot_buy -- spot buy was  successful')
        orders[coin] = client.get_all_orders(symbol=coin, limit=1)

        # binance sometimes returns an empty list, the code will wait here until binance returns the order
        while orders[coin] == []:
            print('Binance is being slow in returning the order, calling the API again...')

            orders[coin] = client.get_all_orders(symbol=coin, limit=1)
            time.sleep(1)

        else:
            print('Order returned, saving order to file')
            # Log trade
            if LOG_TRADES:
                write_log(f"Buy : {volume[coin]} {coin} - {last_price[coin]['price']}")
            isolated_margin_volume[coin] = ''
            return True
    except Exception as e:
        print(e)
        return False


def enable_isolated_margin_account(symbol=''):
    # turn on an account that already was activated but now it in the disable stage.
    try:
        # we can send this command a few times without any error
        client._request_margin_api('post', 'margin/isolated/account', True, data={'symbol': symbol})
        client.transfer_spot_to_isolated_margin(asset=PAIR_WITH,
                                                symbol=symbol,
                                                amount=str(QUANTITY))
        return True
    except Exception as e:
        print(e)
        return False


def activate_isolated_margin_account(symbol=''):
    try:
        client.transfer_spot_to_isolated_margin(asset=PAIR_WITH,
                                                symbol=symbol,
                                                amount=str(QUANTITY))
        return True
    except Exception as e:
        print(e)
        return False


def activate_or_enable_isolated_margin_account(symbol=''):
    if activate_isolated_margin_account(symbol=symbol):
        return True
    else:
        return enable_isolated_margin_account(symbol=symbol)


def check_isolated_margin_symbol(symbol=''):
    try:
        res = client.get_isolated_margin_symbol(symbol=symbol)
        if res:
            return True
    except Exception as e:
        if 'Pair not found' in e.message:
            print(e.message)
            return False


def core_isolated_margin_buy(coin=None, isolated_margin_volume=None, orders=None):
    try:

        activate_or_enable = activate_or_enable_isolated_margin_account(symbol=coin)
        # transaction = client.transfer_spot_to_isolated_margin(asset=PAIR_WITH,
        #                                                       symbol=coin,
        #                                                       amount=str(QUANTITY))


        print('core_isolated_margin_buy -- activate_or_enable_isolated_margin_account was successful')

        if activate_or_enable:  # activate_or_enable_isolated_margin_account  and transaction from spot account was successful
            buy_margin_order = client.create_margin_order(symbol=coin,
                                                          side=client.SIDE_BUY,
                                                          type=client.ORDER_TYPE_MARKET,
                                                          # timeInForce=client.TIME_IN_FORCE_GTC,
                                                          sideEffectType="MARGIN_BUY",
                                                          isIsolated='TRUE',
                                                          # quantity=isolated_margin_volume[coin])
                                                          quantity=asset_with_correct_step_size(asset=isolated_margin_volume[coin], symbol=coin))


            print('core_isolated_margin_buy -- isolated margin buy was successful pair: {}'.format(coin))
            orders[coin] = client.get_all_margin_orders(symbol=coin,
                                                        isIsolated='TRUE',
                                                        limit=1)
            # binance sometimes returns an empty list, the code will wait here until binance returns the order
            while orders[coin] == []:
                print('Binance is being slow in returning the order, calling the API again...')
                orders[coin] = client.get_all_margin_orders(symbol=coin,
                                                            isIsolated='TRUE',
                                                            limit=1)
                time.sleep(1)
            else:
                print('Margin order returned, saving order to file')
                # Log trade
                if LOG_TRADES:
                    write_log(f"Buy (margin account): {isolated_margin_volume[coin]} {coin} - {last_price[coin]['price']}")
                return True
        else:
            return False
    except Exception as e:
        print('error buy in isolated margin account')
        print(e)
        return False


def transfer_from_isolated_margin_to_spot_for_buy(symbol=''):
    try:
        account_data = client.get_isolated_margin_account(symbols=symbol)
        free_quote_money = account_data['assets'][0]['quoteAsset']['free']
        if free_quote_money != '0':  # if we have some money to the transaction
            transaction = client.transfer_isolated_margin_to_spot(asset=PAIR_WITH,
                                                                  symbol=symbol,
                                                                  amount=free_quote_money)
            return True if transaction.get('tranId') else False
        return False
    except Exception as e:
        print(e)
        return False


def check_pair_name_from_table_margin_buy_sell_custom_signal():
    pair_name, buy, buy_time, sell = table_margin_buy_sell_custom_signal_read_data(conn=connect)
    if not pair_name or pair_name == 'False':
        return False
    else:
        return pair_name


def buy(custom_pair_name=''):
    '''Place Buy market orders for each volatile coin found'''

    volume, isolated_margin_volume, last_price = convert_volume(custom_pair_name=custom_pair_name)
    orders = {}
    buy_unix_time={}
    for coin in volume:
        # only buy if the there are no active trades on the coin
        if coin not in coins_bought:
        #     print(f"{txcolors.BUY}Preparing to buy {volume[coin]} {coin}{txcolors.DEFAULT}")
        #     curr_unix_time = time.mktime(datetime.now().timetuple())
        #     buy_unix_time[coin] = 0
        #     curr_minus_delta_time = curr_unix_time - 20 * 60
        #     if TEST_MODE:
        #         if STATUS == 'main':
        #             if check_coin_pair_activity(connect=connect, pair_names=[coin]):
        #                 efficiency_coef, positive_set, efficiency_coef_processed_time, positive_set_processed_time = table_calculate_efficiency_read_data(conn=connect)
        #                 if (float(efficiency_coef) > 0.8 and int(efficiency_coef_processed_time) >= curr_minus_delta_time) or \
        #                          (positive_set and int(positive_set_processed_time) >= curr_minus_delta_time):
        #
        #                     orders[coin] = [{
        #                         'symbol': coin,
        #                         'orderId': 0,
        #                         'time': datetime.now().timestamp()
        #                     }]
        #                     # Log trade
        #                     if LOG_TRADES:
        #                         write_log(f"Buy : {volume[coin]} {coin} - {last_price[coin]['price']}")
        #         elif STATUS == 'statistics':
        #             orders[coin] = [{
        #                 'symbol': coin,
        #                 'orderId': 0,
        #                 'time': datetime.now().timestamp()
        #             }]
        #             # Log trade
        #             if LOG_TRADES:
        #                 write_log(f"Buy : {volume[coin]} {coin} - {last_price[coin]['price']}")
        #         continue
        #     # try to create a real order if the test orders did not raise an exception
        #     # try:
        #     #     if STATUS == 'main' and not TEST_MODE:
        #     #         if check_coin_pair_activity(connect=connect, pair_names=[coin]):
        #     #             efficiency_coef, positive_set, efficiency_coef_processed_time, positive_set_processed_time = table_calculate_efficiency_read_data(conn=connect)
        #     #             if (float(efficiency_coef) > 0.8 and int(efficiency_coef_processed_time) >= curr_minus_delta_time) or \
        #     #                      (positive_set and int(positive_set_processed_time) >= curr_minus_delta_time):
        #     #                 buy_limit = client.create_order(
        #     #                     symbol=coin,
        #     #                     side='BUY',
        #     #                     type='MARKET',
        #     #                     quantity=volume[coin]
        #     #                 )
        #     #
        #     # # error handling here in case position cannot be placed
        #     # except Exception as e:
        #     #     print(e)
        #
        #     # run the else block if the position has been placed and return order info
            if STATUS == 'main' and not TEST_MODE:
                # if check_coin_pair_activity(connect=connect, pair_names=[coin]):
                #     efficiency_coef, positive_set, efficiency_coef_processed_time, positive_set_processed_time = table_calculate_efficiency_read_data(conn=connect)
                #     if (float(efficiency_coef) > 0.8 and int(efficiency_coef_processed_time) >= curr_minus_delta_time) or \
                #             (positive_set and int(positive_set_processed_time) >= curr_minus_delta_time):

                if not MARGIN:# use spot account
                    core_spot_buy(coin=coin,
                                  volume=volume,
                                  isolated_margin_volume=isolated_margin_volume,
                                  orders=orders)
                    buy_unix_time[coin] = int(time.mktime(datetime.now().timetuple()))
                    continue
                    # buy_limit = client.create_order(symbol=coin,
                    #                                 side='BUY',
                    #                                 type='MARKET',
                    #                                 quantity=volume[coin])
                    #
                    # orders[coin] = client.get_all_orders(symbol=coin, limit=1)
                    #
                    # # binance sometimes returns an empty list, the code will wait here until binance returns the order
                    # while orders[coin] == []:
                    #     print('Binance is being slow in returning the order, calling the API again...')
                    #
                    #     orders[coin] = client.get_all_orders(symbol=coin, limit=1)
                    #     time.sleep(1)
                    #
                    # else:
                    #     print('Order returned, saving order to file')
                    #
                    #     # Log trade
                    #     if LOG_TRADES:
                    #         write_log(f"Buy : {volume[coin]} {coin} - {last_price[coin]['price']}")



                    # more info  for isolated margin account
                    # https://stackoverflow.com/questions/60736731/what-is-the-problem-with-my-code-in-borrowing-cryptocurrency-with-api-in-binance
                    # https://stackoverflow.com/questions/66558035/binance-python-api-margin-order-incomplete-repay-loan
                elif MARGIN:# use isolated margin account
                    if not check_isolated_margin_symbol(symbol=coin):
                        continue
                    res_isolated_margin_buy = core_isolated_margin_buy(coin=coin,
                                                                       isolated_margin_volume=isolated_margin_volume,
                                                                       orders=orders)
                    buy_unix_time[coin] = int(time.mktime(datetime.now().timetuple()))
                    if res_isolated_margin_buy:
                        continue
                    else: #if we have some error in isolated_margin_buy -- try to use spot account

                        # account_data = client.get_isolated_margin_account(symbols=coin)
                        # free_quote_money = account_data['assets'][0]['quoteAsset']['free']
                        # # free_base_money = account_data['assets'][0]['baseAsset']['free']
                        # if free_quote_money != '0':  # if we have some money to the transaction
                        #     transaction = client.transfer_isolated_margin_to_spot(asset=PAIR_WITH,
                        #                                                           symbol=coin,
                        #                                                           amount=free_quote_money)

                        if transfer_from_isolated_margin_to_spot_for_buy(symbol=coin):
                        # if transaction.get('tranId'):
                            core_spot_buy(coin=coin,
                                          volume=volume,
                                          orders=orders,
                                          isolated_margin_volume=isolated_margin_volume)
                            buy_unix_time[coin] = int(time.mktime(datetime.now().timetuple()))


                        else:
                            # if we have not any money in the isolated  margin account
                            # or it was some problems with the transfer it to the spot account
                            # try to use the spot account
                            core_spot_buy(coin=coin,
                                          volume=volume,
                                          orders=orders,
                                          isolated_margin_volume=isolated_margin_volume)
                            buy_unix_time[coin] = int(time.mktime(datetime.now().timetuple()))

                        # client.transfer_isolated_margin_to_spot(asset=coin[:-len(PAIR_WITH)],  # base coin name
                        #                                         symbol=coin,
                        #                                         amount=free_base_money)

                        continue

                    # try:
                    #     # volume[coin] = volume[coin] * MARGIN_LEVERAGE_COEFFICIENT
                    #     transaction = client.transfer_spot_to_isolated_margin(asset=PAIR_WITH,
                    #                                                           symbol=coin,
                    #                                                           amount=str(QUANTITY))
                    #
                    #     if transaction.get('tranId'): #transaction from spot to isolated_margin was successful
                    #         buy_margin_order = client.create_margin_order(symbol=coin,
                    #                                                       side=client.SIDE_BUY,
                    #                                                       type=client.ORDER_TYPE_MARKET,
                    #                                                      # timeInForce=client.TIME_IN_FORCE_GTC,
                    #                                                       sideEffectType="MARGIN_BUY",
                    #                                                       isIsolated='TRUE',
                    #                                                       quantity=isolated_margin_volume[coin])
                    #
                    #
                    #         orders[coin] = client.get_all_margin_orders(symbol=coin,
                    #                                                     isIsolated='TRUE',
                    #                                                     limit=1)
                    #         # binance sometimes returns an empty list, the code will wait here until binance returns the order
                    #         while orders[coin] == []:
                    #             print('Binance is being slow in returning the order, calling the API again...')
                    #             orders[coin] = client.get_all_margin_orders(symbol=coin,
                    #                                                         isIsolated='TRUE',
                    #                                                         limit=1)
                    #             time.sleep(1)
                    #         else:
                    #             print('Margin order returned, saving order to file')
                    #             # Log trade
                    #             if LOG_TRADES:
                    #                 write_log(f"Buy (margin account): {volume[coin]} {coin} - {last_price[coin]['price']}")
                    # except Exception as e:
                    #     print('error buy in isolated margin account')
                    #     print(e)

        else:
            print(f'Signal detected, but there is already an active trade on {coin}')

    return orders, last_price, volume, isolated_margin_volume, buy_unix_time


# def core_sell(coin='', LastPrice=None, BuyPrice=None, PriceChange=None, coins_sold=None):
#     # try to create a real order
#     global hsp_head, session_profit
#     try:
#         if not TEST_MODE:
#             sell_coins_limit = client.create_order(symbol=coin,
#                                                    side='SELL',
#                                                    type='MARKET',
#                                                    quantity=coins_bought[coin]['volume']
#                                                    )
#
#     # error handling here in case position cannot be placed
#     except Exception as e:
#         print(e)
#
#     # run the else block if coin has been sold and create a dict for each coin sold
#     else:
#         coins_sold[coin] = coins_bought[coin]
#
#         # prevent system from buying this coin for the next TIME_DIFFERENCE minutes
#         volatility_cooloff[coin] = datetime.now()
#
#         # Log trade
#         if LOG_TRADES:
#             profit = ((LastPrice - BuyPrice) * coins_sold[coin]['volume']) * (
#                     1 - (TRADING_FEE * 2))  # adjust for trading fee here
#             write_log(
#                 f"Sell: {coins_sold[coin]['volume']} {coin} - {BuyPrice} - {LastPrice} Profit: {profit:.2f} {PriceChange - (TRADING_FEE * 2):.2f}%")
#             curr_unix_time = int(time.mktime(datetime.now().timetuple()))
#             curr_res = "+" if profit >= 0.0 else "-"
#             efficiency_coef, efficiency_coef_processed_time = calculate_efficiency_lib(curr_res=curr_res)
#             # write to the efficiency_log file
#             efficiency_log(curr_unix_time=curr_unix_time,
#                            efficiency_result=curr_res,
#                            efficiency_coeff=efficiency_coef)
#
#
#             session_profit = session_profit + (PriceChange - (TRADING_FEE * 2))
#     return coins_sold


# def sell_coins(coins_close_manually=[]):


def transfer_from_isolated_margin_to_spot_for_sell(symbol=''):
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


def sell_coins():
    '''sell coins that have reached the STOP LOSS or TAKE PROFIT threshold'''
    coins_bought_list = list(coins_bought)
    # if coins_close_manually:
    #     coins_bought_list = coins_close_manually

    global hsp_head, session_profit

    last_price = get_price(False) # don't populate rolling window
    #last_price = get_price(add_to_historical=True) # don't populate rolling window
    coins_sold = {}

    # {
    #     "BTCSTUSDT": {
    #         "symbol": "BTCSTUSDT",
    #         "orderid": 0,
    #         "timestamp": 1660264315.045158,
    #         "bought_at": "25.99000000",
    #         "volume": 7.7,
    #         "stop_loss": -2.5,
    #         "take_profit": 0.8
    #     }
    # }



    # #---------------------------------
    # if coins_close_manually:
    #     coins_close_manually_dict={}
    #     for coin in list(coins_bought):
    #         if
    #---------------------------------
    # coins_bought ={'BTCSTUSDT': {'symbol': 'BTCSTUSDT', 'orderid': 0, 'timestamp': 1660264315.045158, 'bought_at': '25.99000000',
    #                'volume': 7.7, 'stop_loss': -2.5, 'take_profit': 0.8}}
    # list(coins_bought) ==['BTCSTUSDT']

    last_coin_pair_name = ''
    for coin in coins_bought_list:
        # define stop loss and take profit
        TP = float(coins_bought[coin]['bought_at']) + (float(coins_bought[coin]['bought_at']) * coins_bought[coin]['take_profit']) / 100
        SL = float(coins_bought[coin]['bought_at']) + (float(coins_bought[coin]['bought_at']) * coins_bought[coin]['stop_loss']) / 100


        LastPrice = float(last_price[coin]['price'])
        BuyPrice = float(coins_bought[coin]['bought_at'])
        PriceChange = float((LastPrice - BuyPrice) / BuyPrice * 100)

        # if not coins_close_manually:
        # check that the price is above the take profit and readjust SL and TP accordingly if trialing stop loss used
        if LastPrice > TP and USE_TRAILING_STOP_LOSS:

            # increasing TP by TRAILING_TAKE_PROFIT (essentially next time to readjust SL)
            coins_bought[coin]['take_profit'] = PriceChange + TRAILING_TAKE_PROFIT
            coins_bought[coin]['stop_loss'] = coins_bought[coin]['take_profit'] - TRAILING_STOP_LOSS
            if DEBUG: print(f"{coin} TP reached, adjusting TP {coins_bought[coin]['take_profit']:.2f}  and SL {coins_bought[coin]['stop_loss']:.2f} accordingly to lock-in profit")
            continue

        # check that the price is below the stop loss or above take profit (if trailing stop loss not used) and sell if this is the case
        if LastPrice < SL or LastPrice > TP and not USE_TRAILING_STOP_LOSS:
            print(f"{txcolors.SELL_PROFIT if PriceChange >= 0. else txcolors.SELL_LOSS}TP or SL reached, selling {coins_bought[coin]['volume']} {coin} - {BuyPrice} - {LastPrice} : {PriceChange-(TRADING_FEE*2):.2f}% Est:${(QUANTITY*(PriceChange-(TRADING_FEE*2)))/100:.2f}{txcolors.DEFAULT}")

            if not TEST_MODE:
                if STATUS == 'main':
                    # if not MARGIN:  # use spot account
                    coin_isolated_margin_volume = coins_bought[coin]['isolated_margin_volume']
                    if not coin_isolated_margin_volume:  # use spot account
                        print("sell_coins --- coin_isolated_margin_volume == {}".format(coin_isolated_margin_volume))
                        print('sell_coins --- use spot account')
                        sell_coins_limit = client.create_order(symbol=coin,
                                                               side='SELL',
                                                               type='MARKET',
                                                               quantity=coins_bought[coin]['volume'])

                    # elif MARGIN: # use isolated margin account
                    elif coin_isolated_margin_volume:
                        print("sell_coins --- coin_isolated_margin_volume == {}".format(coin_isolated_margin_volume))
                        print('sell_coins --- use isolated margin account')
                        account_data = client.get_isolated_margin_account(symbols=coin)
                        free_base_money = account_data['assets'][0]['baseAsset']['free']
                        sell_margin_order = client.create_margin_order(symbol=coin,
                                                                       side=client.SIDE_SELL,
                                                                       type=client.ORDER_TYPE_MARKET,
                                                                       sideEffectType="AUTO_REPAY",
                                                                       isIsolated='TRUE',
                                                                       # quantity=coins_bought[coin]['volume']
                                                                       quantity=asset_with_correct_step_size(asset=free_base_money,
                                                                                                             symbol=coin)
                                                                       )

                        last_coin_pair_name = coin
                        # # values of baseAsset and quoteAsset  was changed  - get it again
                        # account_data = client.get_isolated_margin_account(symbols=coin)
                        # free_base_money = account_data['assets'][0]['baseAsset']['free']
                        # free_quote_money = account_data['assets'][0]['quoteAsset']['free']
                        # # from isolated to spot
                        # if free_quote_money !='0':
                        #     client.transfer_isolated_margin_to_spot(asset=PAIR_WITH,
                        #                                             symbol=coin,
                        #                                             amount=free_quote_money)
                        #
                        # if free_base_money !='0':
                        #     client.transfer_isolated_margin_to_spot(asset=coin[:-len(PAIR_WITH)],  # base coin name
                        #                                             symbol=coin,
                        #                                             amount=free_base_money)


                    coins_sold[coin] = coins_bought[coin]
                    # prevent system from buying this coin for the next TIME_DIFFERENCE minutes
                    volatility_cooloff[coin] = datetime.now()
                    # Log trade
                    if LOG_TRADES:
                        coins_sold_volume = coins_sold[coin]['volume'] if not coins_bought[coin]['isolated_margin_volume'] else coins_sold[coin]['isolated_margin_volume']

                        profit = ((LastPrice - BuyPrice) * coins_sold_volume) * (1 - (TRADING_FEE * 2))  # adjust for trading fee here
                        write_log(
                            f"Sell: {coins_sold[coin]['volume']} {coin} - {BuyPrice} - {LastPrice} Profit: {profit:.2f} {PriceChange - (TRADING_FEE * 2):.2f}%")

                        curr_unix_time = int(time.mktime(datetime.now().timetuple()))
                        curr_res = "+" if profit >= 0.0 else "-"
                        efficiency_coef, efficiency_coef_processed_time = calculate_efficiency_lib(curr_res=curr_res)
                        # write to the efficiency_log file
                        efficiency_log(curr_unix_time=curr_unix_time,
                                       efficiency_result=curr_res,
                                       efficiency_coeff=efficiency_coef)
                        # write to the db
                        table_last_sold_pairs_data_write_new_data(conn=connect,
                                                                  pair_name=coin,
                                                                  last_sold_time=str(efficiency_coef_processed_time))
                        session_profit = session_profit + (PriceChange - (TRADING_FEE * 2))
                    continue


            else: #if TEST_MODE==True
                coins_sold[coin] = coins_bought[coin]
                # prevent system from buying this coin for the next TIME_DIFFERENCE minutes
                volatility_cooloff[coin] = datetime.now()
                # Log trade
                if LOG_TRADES:
                    profit = ((LastPrice - BuyPrice) * coins_sold[coin]['volume']) * (1 - (TRADING_FEE * 2))  # adjust for trading fee here
                    write_log(
                        f"Sell: {coins_sold[coin]['volume']} {coin} - {BuyPrice} - {LastPrice} Profit: {profit:.2f} {PriceChange - (TRADING_FEE * 2):.2f}%")

                    curr_unix_time = int(time.mktime(datetime.now().timetuple()))
                    curr_res = "+" if profit >= 0.0 else "-"
                    efficiency_coef, efficiency_coef_processed_time = calculate_efficiency_lib(curr_res=curr_res)
                    positive_set, positive_set_processed_time = calculate_last_positive_negative()
                    # write to the efficiency_log file
                    efficiency_log(curr_unix_time=curr_unix_time,
                                   efficiency_result=curr_res,
                                   efficiency_coeff=efficiency_coef)
                    # write to the db
                    if STATUS == 'statistics':
                        table_calculate_efficiency_write_data(conn=connect,
                                                              efficiency_coef=efficiency_coef,
                                                              efficiency_coef_processed_time=str(efficiency_coef_processed_time),
                                                              positive_set=positive_set,
                                                              positive_set_processed_time=str(positive_set_processed_time))

                    if STATUS == 'main':
                        table_last_sold_pairs_data_write_new_data(conn=connect,
                                                                  pair_name=coin,
                                                                  last_sold_time=str(efficiency_coef_processed_time))

                    session_profit = session_profit + (PriceChange - (TRADING_FEE * 2))
                continue

        #---------------start the block "checking time after buy" -------------
        if coins_bought[coin]['buy_unix_time']:
            if int(time.mktime(datetime.now().timetuple())) - coins_bought[coin]['buy_unix_time'] >= 370:#6 min 10 sec
                coins_bought_coin_volume = coins_bought[coin]['volume'] if not coins_bought[coin]['isolated_margin_volume'] else coins_bought[coin]['isolated_margin_volume']
                print(f"{txcolors.SELL_PROFIT if PriceChange >= 0. else txcolors.SELL_LOSS}Time of the buy signal is ended, selling {coins_bought_coin_volume} {coin} - {BuyPrice} - {LastPrice} : {PriceChange-(TRADING_FEE*2):.2f}% Est:${(QUANTITY*(PriceChange-(TRADING_FEE*2)))/100:.2f}{txcolors.DEFAULT}")

                if not TEST_MODE:
                    if STATUS == 'main':
                        # if not MARGIN:  # use spot account
                        coin_isolated_margin_volume = coins_bought[coin]['isolated_margin_volume']
                        if not coin_isolated_margin_volume:  # use spot account
                            print("sell_coins --- coin_isolated_margin_volume == {}".format(coin_isolated_margin_volume))
                            print('sell_coins --- use spot account')
                            sell_coins_limit = client.create_order(symbol=coin,
                                                                   side='SELL',
                                                                   type='MARKET',
                                                                   quantity=coins_bought[coin]['volume'])

                        # elif MARGIN: # use isolated margin account
                        elif coin_isolated_margin_volume:
                            print("sell_coins --- coin_isolated_margin_volume == {}".format(coin_isolated_margin_volume))
                            print('sell_coins --- use isolated margin account')
                            print('Time of the buy signal is ended')
                            account_data = client.get_isolated_margin_account(symbols=coin)
                            free_base_money = account_data['assets'][0]['baseAsset']['free']
                            sell_margin_order = client.create_margin_order(symbol=coin,
                                                                           side=client.SIDE_SELL,
                                                                           type=client.ORDER_TYPE_MARKET,
                                                                           sideEffectType="AUTO_REPAY",
                                                                           isIsolated='TRUE',
                                                                           # quantity=coins_bought[coin]['volume']
                                                                           quantity=asset_with_correct_step_size(asset=free_base_money,
                                                                                                                 symbol=coin)
                                                                           )

                            last_coin_pair_name = coin
                            # # values of baseAsset and quoteAsset  was changed  - get it again
                            # account_data = client.get_isolated_margin_account(symbols=coin)
                            # free_base_money = account_data['assets'][0]['baseAsset']['free']
                            # free_quote_money = account_data['assets'][0]['quoteAsset']['free']
                            # # from isolated to spot
                            # if free_quote_money !='0':
                            #     client.transfer_isolated_margin_to_spot(asset=PAIR_WITH,
                            #                                             symbol=coin,
                            #                                             amount=free_quote_money)
                            #
                            # if free_base_money !='0':
                            #     client.transfer_isolated_margin_to_spot(asset=coin[:-len(PAIR_WITH)],  # base coin name
                            #                                             symbol=coin,
                            #                                             amount=free_base_money)


                        coins_sold[coin] = coins_bought[coin]
                        # prevent system from buying this coin for the next TIME_DIFFERENCE minutes
                        volatility_cooloff[coin] = datetime.now()
                        # Log trade
                        if LOG_TRADES:
                            coins_sold_volume = coins_sold[coin]['volume'] if not coins_bought[coin]['isolated_margin_volume'] else coins_sold[coin]['isolated_margin_volume']

                            profit = ((LastPrice - BuyPrice) * coins_sold_volume) * (1 - (TRADING_FEE * 2))  # adjust for trading fee here
                            write_log(
                                f"Sell: {coins_sold[coin]['volume']} {coin} - {BuyPrice} - {LastPrice} Profit: {profit:.2f} {PriceChange - (TRADING_FEE * 2):.2f}%")

                            curr_unix_time = int(time.mktime(datetime.now().timetuple()))
                            curr_res = "+" if profit >= 0.0 else "-"
                            efficiency_coef, efficiency_coef_processed_time = calculate_efficiency_lib(curr_res=curr_res)
                            # write to the efficiency_log file
                            efficiency_log(curr_unix_time=curr_unix_time,
                                           efficiency_result=curr_res,
                                           efficiency_coeff=efficiency_coef)
                            # write to the db
                            table_last_sold_pairs_data_write_new_data(conn=connect,
                                                                      pair_name=coin,
                                                                      last_sold_time=str(efficiency_coef_processed_time))
                            session_profit = session_profit + (PriceChange - (TRADING_FEE * 2))
                        continue


                else: #if TEST_MODE==True
                    coins_sold[coin] = coins_bought[coin]
                    # prevent system from buying this coin for the next TIME_DIFFERENCE minutes
                    volatility_cooloff[coin] = datetime.now()
                    # Log trade
                    if LOG_TRADES:
                        profit = ((LastPrice - BuyPrice) * coins_sold[coin]['volume']) * (1 - (TRADING_FEE * 2))  # adjust for trading fee here
                        write_log(
                            f"Sell: {coins_sold[coin]['volume']} {coin} - {BuyPrice} - {LastPrice} Profit: {profit:.2f} {PriceChange - (TRADING_FEE * 2):.2f}%")

                        curr_unix_time = int(time.mktime(datetime.now().timetuple()))
                        curr_res = "+" if profit >= 0.0 else "-"
                        efficiency_coef, efficiency_coef_processed_time = calculate_efficiency_lib(curr_res=curr_res)
                        positive_set, positive_set_processed_time = calculate_last_positive_negative()
                        # write to the efficiency_log file
                        efficiency_log(curr_unix_time=curr_unix_time,
                                       efficiency_result=curr_res,
                                       efficiency_coeff=efficiency_coef)
                        # write to the db
                        if STATUS == 'statistics':
                            table_calculate_efficiency_write_data(conn=connect,
                                                                  efficiency_coef=efficiency_coef,
                                                                  efficiency_coef_processed_time=str(efficiency_coef_processed_time),
                                                                  positive_set=positive_set,
                                                                  positive_set_processed_time=str(positive_set_processed_time))

                        if STATUS == 'main':
                            table_last_sold_pairs_data_write_new_data(conn=connect,
                                                                      pair_name=coin,
                                                                      last_sold_time=str(efficiency_coef_processed_time))

                        session_profit = session_profit + (PriceChange - (TRADING_FEE * 2))
                    continue


        #--------------- end the block "checking time after buy"- -------------



        # no action; print once every TIME_DIFFERENCE
        if hsp_head == 1:
            if len(coins_bought) > 0:
                print(f'TP or SL not yet reached, not selling {coin} for now {BuyPrice} - {LastPrice} : {txcolors.SELL_PROFIT if PriceChange >= 0. else txcolors.SELL_LOSS}{PriceChange-(TRADING_FEE*2):.2f}% Est:${(QUANTITY*(PriceChange-(TRADING_FEE*2)))/100:.2f}{txcolors.DEFAULT}')

    if hsp_head == 1 and len(coins_bought_list) == 0: print(f'Not holding any coins')
 
    return last_coin_pair_name, coins_sold


def update_portfolio(orders, last_price, volume, isolated_margin_volume,buy_unix_time):
    '''add every coin bought to our portfolio for tracking/selling later'''
    if DEBUG:
        print(orders)
    for coin in orders:
        #---- for testing --------
        print('volume {}'.format(volume[coin]))
        print('isolated_margin_volume {}'.format(isolated_margin_volume[coin]))
        #---- --------------------

        coins_bought[coin] = {
            'symbol': orders[coin][0]['symbol'],
            'orderid': orders[coin][0]['orderId'],
            'timestamp': orders[coin][0]['time'],
            'bought_at': last_price[coin]['price'],
            'volume': volume[coin],
            'isolated_margin_volume': isolated_margin_volume[coin],
            'buy_unix_time': buy_unix_time[coin],
            'stop_loss': -STOP_LOSS,
            'take_profit': TAKE_PROFIT,
            }

        # save the coins in a json file in the same directory
        with open(coins_bought_file_path, 'w') as file:
            json.dump(coins_bought, file, indent=4)

        print(f'Order with id {orders[coin][0]["orderId"]} placed and saved to file')


def remove_from_portfolio(coins_sold):
    '''Remove coins sold due to SL or TP from portfolio'''
    for coin in coins_sold:
        coins_bought.pop(coin)

    with open(coins_bought_file_path, 'w') as file:
        json.dump(coins_bought, file, indent=4)


def write_log(logline):
    timestamp = datetime.now().strftime("%d/%m %H:%M:%S")
    with open(LOG_FILE,'a+') as f:
        f.write(timestamp + ' ' + logline + '\n')


def manage_in_running():
    DEFAULT_CONFIG_FILE ='config.yml'
    args = parse_args()
    config_file = args.config if args.config else DEFAULT_CONFIG_FILE
    parsed_config = load_config(config_file)
    manage_file_path = parsed_config['manage_in_running_options']['MANAGE_FILE']
    if os.path.isfile(manage_file_path) and os.stat(manage_file_path).st_size != 0:
        with open(manage_file_path) as manage_file:
            manage_in_running_data = json.load(manage_file)
            close_pairs = manage_in_running_data['commands']['close_pairs']
            stop_main_script_manually= manage_in_running_data['commands']['stop_main_script_manually']
        return close_pairs, stop_main_script_manually


def use_actual_balance_for_pair_with():
    if STATUS == 'main' and USE_CURRENT_BALANCE_FOR_PAIR_WITH and not TEST_MODE:
        return int(0.95 * float(client.get_asset_balance(asset=PAIR_WITH)['free']))# usage 95% from all money
    else:
        return parsed_config['trading_options']['QUANTITY']



if __name__ == '__main__':

    # Load arguments then parse settings
    args = parse_args()
    mymodule = {}

    # set to false at Start
    global bot_paused
    bot_paused = False

    DEFAULT_CONFIG_FILE = 'config.yml'
    DEFAULT_CREDS_FILE = 'creds.yml'

    config_file = args.config if args.config else DEFAULT_CONFIG_FILE
    creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
    parsed_config = load_config(config_file)
    parsed_creds = load_config(creds_file)

    # Default no debugging
    DEBUG = False

    # Load system vars
    TEST_MODE = parsed_config['script_options']['TEST_MODE']
    LOG_TRADES = parsed_config['script_options'].get('LOG_TRADES')
    STATUS = parsed_config['script_options'].get('STATUS')
    MARGIN = parsed_config['script_options'].get('MARGIN')
    MARGIN_LEVERAGE_COEFFICIENT = parsed_config['script_options'].get('MARGIN_LEVERAGE_COEFFICIENT')

    USE_CURRENT_BALANCE_FOR_PAIR_WITH = parsed_config['trading_options']['USE_CURRENT_BALANCE_FOR_PAIR_WITH']

    LOG_FILE = parsed_config['script_options'].get('LOG_FILE')
    EFFICIENCY_FILE = parsed_config['script_options'].get('EFFICIENCY_FILE')

    DEBUG_SETTING = parsed_config['script_options'].get('DEBUG')
    AMERICAN_USER = parsed_config['script_options'].get('AMERICAN_USER')

    # Load trading vars
    PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
    MAX_COINS = parsed_config['trading_options']['MAX_COINS']
    FIATS = parsed_config['trading_options']['FIATS']
    TIME_DIFFERENCE = parsed_config['trading_options']['TIME_DIFFERENCE']
    RECHECK_INTERVAL = parsed_config['trading_options']['RECHECK_INTERVAL']
    CHANGE_IN_PRICE = parsed_config['trading_options']['CHANGE_IN_PRICE']
    STOP_LOSS = parsed_config['trading_options']['STOP_LOSS']
    TAKE_PROFIT = parsed_config['trading_options']['TAKE_PROFIT']
    CUSTOM_LIST = parsed_config['trading_options']['CUSTOM_LIST']
    TICKERS_LIST = parsed_config['trading_options']['TICKERS_LIST']
    USE_TRAILING_STOP_LOSS = parsed_config['trading_options']['USE_TRAILING_STOP_LOSS']
    TRAILING_STOP_LOSS = parsed_config['trading_options']['TRAILING_STOP_LOSS']
    TRAILING_TAKE_PROFIT = parsed_config['trading_options']['TRAILING_TAKE_PROFIT']
    TRADING_FEE = parsed_config['trading_options']['TRADING_FEE']
    SIGNALLING_MODULES = parsed_config['trading_options']['SIGNALLING_MODULES']
    if DEBUG_SETTING or args.debug:
        DEBUG = True

    # Load creds for correct environment
    access_key, secret_key = load_correct_creds(parsed_creds)

    if DEBUG:
        print(f'loaded config below\n{json.dumps(parsed_config, indent=4)}')
        print(f'Your credentials have been loaded from {creds_file}')


    # Authenticate with the client, Ensure API key is good before continuing
    if AMERICAN_USER:
        client = Client(access_key, secret_key, tld='us')
    else:
        client = Client(access_key, secret_key)
    # QUANTITY = parsed_config['trading_options']['QUANTITY']
    QUANTITY = use_actual_balance_for_pair_with()


    # If the users has a bad / incorrect API key.
    # this will stop the script from starting, and display a helpful error.
    api_ready, msg = test_api_key(client, BinanceAPIException)
    if api_ready is not True:
       exit(f'{txcolors.SELL_LOSS}{msg}{txcolors.DEFAULT}')

    # Use CUSTOM_LIST symbols if CUSTOM_LIST is set to True
    if CUSTOM_LIST: tickers=[line.strip() for line in open(TICKERS_LIST)]


    # rolling window of prices; cyclical queue
    historical_prices = [None] * (TIME_DIFFERENCE * RECHECK_INTERVAL)
    hsp_head = -1

    # prevent including a coin in volatile_coins if it has already appeared there less than TIME_DIFFERENCE minutes ago
    volatility_cooloff = {}


    # try to load all the coins bought by the bot if the file exists and is not empty
    coins_bought = {}
    # path to the saved coins_bought file
    coins_bought_file_path = 'coins_bought.json'
    # use separate files for testing and live trading
    if TEST_MODE:
        coins_bought_file_path = 'test_' + coins_bought_file_path

    # if coins_bought json file exists and it's not empty --clean it
    if os.path.isfile(coins_bought_file_path):
        with open(coins_bought_file_path,'w') as file:
            file.close()

    # # if saved coins_bought json file exists and it's not empty then load it
    # if os.path.isfile(coins_bought_file_path) and os.stat(coins_bought_file_path).st_size!= 0:
    #     with open(coins_bought_file_path) as file:
    #             coins_bought = json.load(file)




    print('Press Ctrl-Q to stop the script')

    if not TEST_MODE:
        if not args.notimeout: # if notimeout skip this (fast for dev tests)
            print('WARNING: You are using the Mainnet and live funds. Waiting 30 seconds as a security measure')
            time.sleep(30)

    signals = glob.glob("signals/*.exs")
    for filename in signals:
        for line in open(filename):
            try:
                os.remove(filename)
            except:
                if DEBUG: print(f'{txcolors.WARNING}Could not remove external signalling file {filename}{txcolors.DEFAULT}')

    if os.path.isfile("signals/paused.exc"):
        try:
            os.remove("signals/paused.exc")
        except:
            if DEBUG: print(f'{txcolors.WARNING}Could not remove external signalling file {filename}{txcolors.DEFAULT}')

    # load signalling modules
    # try:
    #     if len(SIGNALLING_MODULES) > 0:
    #         for module in SIGNALLING_MODULES:
    #             print(f'Starting {module}')
    #             mymodule[module] = importlib.import_module(module)
    #             t = threading.Thread(target=mymodule[module].do_work, args=())
    #             t.daemon = True
    #             t.start()
    #             time.sleep(2)
    #     else:
    #         print(f'No modules to load {SIGNALLING_MODULES}')
    # except Exception as e:
    #     print(e)

    # seed initial prices
    get_price()
    READ_TIMEOUT_COUNT=0
    CONNECTION_ERROR_COUNT = 0
    while True:
        try:
            # coins_close_manually, stop_main_script_manually = manage_in_running()

            custom_pair_name = check_pair_name_from_table_margin_buy_sell_custom_signal()
            if not custom_pair_name:
                time.sleep((timedelta(minutes=float(TIME_DIFFERENCE / RECHECK_INTERVAL))).total_seconds())
                continue
            else:
                orders, last_price, volume, isolated_margin_volume, buy_unix_time = buy(custom_pair_name=custom_pair_name)
                update_portfolio(orders, last_price, volume, isolated_margin_volume, buy_unix_time)
                # coins_sold = sell_coins(coins_close_manually=coins_close_manually)
                last_coin_pair_name, coins_sold = sell_coins()
                if last_coin_pair_name:
                    transfer_from_isolated_margin_to_spot_for_sell(symbol=last_coin_pair_name)
                remove_from_portfolio(coins_sold)
        except ReadTimeout as rt:
            READ_TIMEOUT_COUNT += 1
            print(f'{txcolors.WARNING}We got a timeout error from from binance. Going to re-loop. Current Count: {READ_TIMEOUT_COUNT}\n{rt}{txcolors.DEFAULT}')
        except ConnectionError as ce:
            CONNECTION_ERROR_COUNT +=1 
            print(f'{txcolors.WARNING}We got a timeout error from from binance. Going to re-loop. Current Count: {CONNECTION_ERROR_COUNT}\n{ce}{txcolors.DEFAULT}')


