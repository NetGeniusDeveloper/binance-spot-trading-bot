from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceRequestException, BinanceAPIException

from buy_asset import buy
from config import BINANCE_API_TIMEOUT, MAXIMUM_NUMBER_OF_API_CALL_TRIES, ACTIVE_TRADING_SYMBOLS, \
    WALLET_USAGE_PERCENT, DRY_RUN
from credentials import BINANCE_API_KEY, BINANCE_SECRET_KEY
from indicators import rsi_fourteen_days_close, rsi_fifteen_days_close, heikin_today, heikin_yesterday, \
    heikin_day_before_yesterday
from return_codes import *
from sell_asset import sell
from telegram_message_sender import send_message
from ai_strategy import analyze_symbol
from risk_manager import validate_ai_trade
from trading_journal import log_trade_decision
import logging
import sys
from requests.exceptions import RequestException

global executing_times_file
global binance_spot_api
global account_free_usdt_balance
global last_account_free_usdt_balances_list
global account_locked_usdt_balance
global last_account_locked_usdt_balances_list
global heikin_ashi_candles


def is_it_time_to_sell(symbol: str):
    logging.info('checking to is it time to sell symbol ' + symbol)
    suitable = False  # You should define your sell strategy here
    if suitable:
        logging.info('it is time to sell symbol ' + symbol)
    else:
        logging.info('it is not time to sell symbol ' + symbol)
    return suitable


def is_it_time_to_to_buy(symbol: str):
    logging.info('checking to is it time to buy symbol ' + symbol)
    suitable = False  # You should define your BUY strategy here
    if suitable:
        logging.info('it is time to buy symbol ' + symbol)
    else:
        logging.info('it is not time to buy symbol ' + symbol)
    return suitable


def is_binance_status_ok():
    logging.info('checking binance status')
    status: bool = binance_spot_api.get_system_status()['status'] == 0
    logging.info('binance status is ' + str(status))
    return status


def update_account_usdt_balance():
    logging.info('trying to update account USDT balance')
    global account_free_usdt_balance

    if DRY_RUN:
        logging.info('DRY_RUN is enabled: skipping private Binance balance request')
        account_free_usdt_balance = 0.0
        return SUCCESSFUL

    global last_account_free_usdt_balances_list
    last_account_free_usdt_balances_list = []
    global account_locked_usdt_balance
    global last_account_locked_usdt_balances_list
    last_account_locked_usdt_balances_list = []
    for i in range(MAXIMUM_NUMBER_OF_API_CALL_TRIES):
        try:
            logging.info('trying to get USDT balance')
            asset_balance_response = binance_spot_api.get_asset_balance('USDT')
            logging.info('USDT balance is' + str(asset_balance_response))
            if asset_balance_response is None:
                return ASSET_BALANCE_NOT_FOUND
            account_free_usdt_balance = float(asset_balance_response['free'])
            logging.info('account free usdt balance is ' + str(account_free_usdt_balance))
            last_account_free_usdt_balances_list.append(account_free_usdt_balance)

            account_locked_usdt_balance = float(asset_balance_response['locked'])
            logging.info('account locked usdt balance is ' + str(account_locked_usdt_balance))
            last_account_locked_usdt_balances_list.append(account_locked_usdt_balance)
            return SUCCESSFUL
        except (BinanceRequestException, BinanceAPIException) as ex:
            logging.error('ERROR in update_account_usdt_balance')
            logging.exception(ex)
            return ERROR


def init_bot():
    global binance_spot_api
    global executing_times_file

    try:
        logging.info('initiating bot...')
        binance_spot_api = Client(
            api_key=BINANCE_API_KEY,
            api_secret=BINANCE_SECRET_KEY,
            requests_params={'timeout': BINANCE_API_TIMEOUT},
        )
        executing_times_file = open('execute-times.tmp', 'a+')
        return SUCCESSFUL
    except (RequestException, BinanceRequestException, BinanceAPIException, TimeoutError, OSError) as ex:
        logging.error('ERROR in init_bot: Binance connection is not available')
        logging.exception(ex)
        return ERROR


def sell_symbols(to_sell_symbols):
    for symbol in to_sell_symbols:
        sell(binance_spot_api, symbol)


def buy_symbols(to_buy_symbols_with_weights):
    global account_free_usdt_balance

    if not to_buy_symbols_with_weights:
        logging.info('AI selected no symbols to buy')
        return

    total_weight = 0
    for item in to_buy_symbols_with_weights:
        total_weight += item['weight']

    if total_weight <= 0:
        logging.warning('total buy weight is zero, skipping buy')
        return

    total_buy_volume = WALLET_USAGE_PERCENT / 100 * account_free_usdt_balance

    if total_buy_volume <= 0:
        logging.info('total buy volume is zero, skipping buy')
        return

    for item in to_buy_symbols_with_weights:
        volume = item['weight'] / total_weight * total_buy_volume
        buy(binance_spot_api, item['symbol'], volume)


def check_for_buy_and_sell_symbols(to_buy_symbols, to_sell_symbols):
    logging.info('checking for buy and sell symbols using AI strategy and risk manager...')

    for item in ACTIVE_TRADING_SYMBOLS:
        symbol = item['symbol']

        decision = analyze_symbol(
            binance_spot_api=binance_spot_api,
            symbol=symbol,
            dry_run=DRY_RUN,
        )

        action = decision.get('action')
        confidence = float(decision.get('confidence') or 0.0)

        logging.info(
            'AI result for ' + symbol +
            ': action=' + str(action) +
            ', confidence=' + str(confidence)
        )

        risk_result = validate_ai_trade(
            symbol=symbol,
            action=str(action),
            confidence=confidence,
            volume_usdt=0.0,
        )

        risk_action = 'RISK_APPROVED' if risk_result.get('approved') else 'RISK_REJECTED'
        risk_status = 'risk_approved' if risk_result.get('approved') else 'risk_rejected'

        log_trade_decision(
            symbol=symbol + 'USDT',
            side=str(action) if action in ('BUY', 'SELL') else 'NONE',
            action=risk_action,
            price=float(decision.get('features', {}).get('current_price') or 0.0),
            quantity=None,
            volume_usdt=0.0,
            confidence=confidence,
            reason='Risk manager result: ' + ', '.join(risk_result.get('reasons') or ['approved']),
            dry_run=DRY_RUN,
            order_id='',
            status=risk_status,
            raw_response={
                'ai_decision': decision,
                'risk_result': risk_result,
            },
        )

        if not risk_result.get('approved'):
            logging.info(
                'Risk manager rejected ' + symbol +
                ': action=' + str(action) +
                ', reasons=' + str(risk_result.get('reasons'))
            )
            continue

        logging.info(
            'Risk manager approved ' + symbol +
            ': action=' + str(action)
        )

        if action == 'SELL':
            to_sell_symbols.append(symbol)

        if action == 'BUY':
            to_buy_symbols.append({'symbol': symbol, 'weight': item['weight']})


def does_run_this_day():
    global executing_times_file
    content = executing_times_file.read()
    return content.__contains__(datetime.now().strftime('%Y-%m-%d'))


def update_executing_times_file():
    global executing_times_file
    executing_times_file.write(datetime.now().strftime('%Y-%m-%d'))


def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%Y/%m/%d %I:%M:%S %p',
                        handlers=[logging.FileHandler("application.log"), logging.StreamHandler(sys.stdout)])

    if init_bot() != SUCCESSFUL:
        logging.error('bot stopped safely: init_bot failed')
        return

    try:
        while True:
            if not is_binance_status_ok():
                logging.warning('bot stopped safely: Binance system status is not OK')
                return

            send_message('bot started')

            if does_run_this_day():
                logging.info('bot already was ran at this day')
                return

            update_account_usdt_balance()

            to_sell_symbols = []
            to_buy_symbols_with_weights = []

            check_for_buy_and_sell_symbols(to_buy_symbols_with_weights, to_sell_symbols)
            sell_symbols(to_sell_symbols)
            buy_symbols(to_buy_symbols_with_weights)
            update_executing_times_file()

            return

    except (RequestException, BinanceRequestException, BinanceAPIException, TimeoutError, OSError) as ex:
        logging.error('bot stopped safely: Binance/network error during main loop')
        logging.exception(ex)
        return


if __name__ == '__main__':
    main()
