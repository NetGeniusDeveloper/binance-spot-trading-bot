import logging

from binance.enums import *
from binance.exceptions import *

from config import DRY_RUN
from telegram_message_sender import send_new_sell_order_message
from trading_journal import log_trade_decision
from utils import get_local_timestamp


def sell(binance_spot_api, symbol):
    logging.info('trying to sell ' + symbol)

    order_id = 's' + get_local_timestamp()

    if DRY_RUN:
        journal_id = log_trade_decision(
            symbol=symbol + 'USDT',
            side='SELL',
            action='DRY_RUN_SELL',
            price=None,
            quantity=None,
            volume_usdt=None,
            confidence=None,
            reason='DRY_RUN is enabled: private balance request and SELL order were skipped',
            dry_run=True,
            order_id=order_id,
            status='dry_run_skipped',
            raw_response={
                'symbol': symbol,
                'message': 'Private balance request skipped in DRY_RUN mode',
            },
        )

        logging.info(
            'DRY_RUN is enabled: skipping private Binance balance request for SELL. '
            'SELL order was NOT sent to Binance. symbol=' + symbol +
            ', order_id=' + order_id +
            ', journal_id=' + str(journal_id)
        )

        return {
            'dry_run': True,
            'side': 'SELL',
            'symbol': symbol,
            'order_id': order_id,
            'journal_id': journal_id,
            'message': 'Private balance request skipped in DRY_RUN mode',
        }

    try:
        volume_response = binance_spot_api.get_asset_balance(symbol)
        logging.info('volume to sell ' + symbol + ' is ' + str(volume_response))

        if volume_response is None:
            log_trade_decision(
                symbol=symbol + 'USDT',
                side='SELL',
                action='SELL_BALANCE_NOT_FOUND',
                reason='Asset balance not found',
                dry_run=False,
                order_id=order_id,
                status='error',
                raw_response=None,
            )

            logging.warning('asset balance not found for ' + symbol)
            return None

        volume = float(volume_response.get('free', 0.0))

        sell_price = extract_sell_price(binance_spot_api, symbol)
        logging.info(symbol + ' sell price is ' + str(sell_price))

        quantity = volume
        logging.info(symbol + ' quantity to sell is ' + str(quantity))

        logging.info(
            'creating sell order with [' +
            'symbol: ' + symbol + ', ' +
            'side: ' + str(SIDE_SELL) + ', ' +
            'type: ' + str(ORDER_TYPE_MARKET) + ', ' +
            'quantity: ' + str(quantity) + ', ' +
            'price: ' + str(sell_price) + ', ' +
            'newClientOrderId: ' + order_id + ', ' +
            ']'
        )

        send_new_sell_order_message(symbol, sell_price, quantity, order_id)

        sell_order_response = binance_spot_api.create_order(
            symbol=symbol + 'USDT',
            side=SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=quantity,
            newClientOrderId=order_id
        )

        journal_id = log_trade_decision(
            symbol=symbol + 'USDT',
            side='SELL',
            action='REAL_SELL',
            price=float(sell_price),
            quantity=float(quantity),
            volume_usdt=float(quantity) * float(sell_price),
            confidence=None,
            reason='Real SELL order sent to Binance',
            dry_run=False,
            order_id=order_id,
            status='sent',
            raw_response=sell_order_response,
        )

        logging.info('sell order response is ' + str(sell_order_response))
        logging.info('sell journal_id is ' + str(journal_id))

        return sell_order_response

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
            side='SELL',
            action='SELL_ERROR',
            reason='Error on creating new SELL order',
            dry_run=DRY_RUN,
            order_id=order_id,
            status='error',
            raw_response=str(ex),
        )

        logging.error('error on creating new sell order')
        logging.exception(ex)
        return None


def extract_sell_price(binance_spot_api, symbol):
    logging.info('trying to get ' + symbol + ' ticker')
    symbol_ticker = binance_spot_api.get_symbol_ticker(symbol=symbol + 'USDT')['price']
    logging.info(symbol + ' ticker :' + str(symbol_ticker))
    return float(symbol_ticker)
