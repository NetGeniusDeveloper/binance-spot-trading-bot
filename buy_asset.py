from binance.enums import *
from binance.exceptions import *
from utils import get_local_timestamp
import logging

from config import DRY_RUN
from telegram_message_sender import send_new_buy_order_message
from trading_journal import log_trade_decision


def buy(binance_spot_api, symbol, volume):
    logging.info('trying to buy ' + symbol + ' with volume ' + str(volume))

    buy_price = extract_buy_price(binance_spot_api, symbol)
    logging.info(symbol + ' buy price is ' + str(buy_price))

    quantity = float(volume) / float(buy_price) if float(buy_price) > 0 else 0.0
    logging.info(symbol + ' quantity to buy is ' + str(quantity))

    order_id = 'b' + get_local_timestamp()

    logging.info(
        'creating buy order with [' +
        'symbol: ' + symbol + ', ' +
        'side: ' + str(SIDE_BUY) + ', ' +
        'type: ' + str(ORDER_TYPE_MARKET) + ', ' +
        'quantity: ' + str(quantity) + ', ' +
        'price: ' + str(buy_price) + ', ' +
        'newClientOrderId: ' + order_id + ', ' +
        ']'
    )

    if DRY_RUN:
        journal_id = log_trade_decision(
            symbol=symbol + 'USDT',
            side='BUY',
            action='DRY_RUN_BUY',
            price=float(buy_price),
            quantity=float(quantity),
            volume_usdt=float(volume),
            confidence=None,
            reason='DRY_RUN is enabled: BUY order was not sent to Binance',
            dry_run=True,
            order_id=order_id,
            status='dry_run_skipped',
            raw_response={
                'symbol': symbol,
                'price': buy_price,
                'quantity': quantity,
                'volume_usdt': volume,
            },
        )

        logging.info(
            'DRY_RUN is enabled: BUY order was NOT sent to Binance. '
            'symbol=' + symbol +
            ', quantity=' + str(quantity) +
            ', price=' + str(buy_price) +
            ', order_id=' + order_id +
            ', journal_id=' + str(journal_id)
        )

        return {
            'dry_run': True,
            'side': 'BUY',
            'symbol': symbol,
            'quantity': quantity,
            'price': buy_price,
            'order_id': order_id,
            'journal_id': journal_id,
        }

    try:
        send_new_buy_order_message(symbol, buy_price, quantity, order_id)

        buy_order_response = binance_spot_api.create_order(
            symbol=symbol + 'USDT',
            side=SIDE_BUY,
            type=ORDER_TYPE_MARKET,
            quantity=quantity,
            newClientOrderId=order_id
        )

        journal_id = log_trade_decision(
            symbol=symbol + 'USDT',
            side='BUY',
            action='REAL_BUY',
            price=float(buy_price),
            quantity=float(quantity),
            volume_usdt=float(volume),
            confidence=None,
            reason='Real BUY order sent to Binance',
            dry_run=False,
            order_id=order_id,
            status='sent',
            raw_response=buy_order_response,
        )

        logging.info('buy order response is ' + str(buy_order_response))
        logging.info('buy journal_id is ' + str(journal_id))

        return buy_order_response

    except (
        BinanceRequestException,
        BinanceAPIException,
        BinanceOrderException,
        BinanceOrderMinAmountException,
        BinanceOrderMinPriceException,
        BinanceOrderMinTotalException,
        BinanceOrderUnknownSymbolException,
        BinanceOrderInactiveSymbolException
    ) as ex:
        log_trade_decision(
            symbol=symbol + 'USDT',
            side='BUY',
            action='BUY_ERROR',
            price=float(buy_price),
            quantity=float(quantity),
            volume_usdt=float(volume),
            confidence=None,
            reason='Error on creating new BUY order',
            dry_run=DRY_RUN,
            order_id=order_id,
            status='error',
            raw_response=str(ex),
        )

        logging.error('error on creating new buy order')
        logging.exception(ex)
        return None


def extract_buy_price(binance_spot_api, symbol):
    logging.info('trying to get ' + symbol + ' ticker')
    symbol_ticker = binance_spot_api.get_symbol_ticker(symbol=symbol + 'USDT')['price']
    logging.info(symbol + ' ticker :' + str(symbol_ticker))
    return float(symbol_ticker)
