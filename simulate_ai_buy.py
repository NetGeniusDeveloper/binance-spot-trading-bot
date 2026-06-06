import logging

from binance.client import Client

from buy_asset import buy
from config import BINANCE_API_TIMEOUT, DRY_RUN, MAX_TRADE_USDT
from credentials import BINANCE_API_KEY, BINANCE_SECRET_KEY
from risk_manager import validate_ai_trade
from trading_journal import log_trade_decision


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    symbol = "BTC"
    action = "BUY"
    confidence = 0.75
    volume_usdt = min(5.0, MAX_TRADE_USDT)

    logging.info("Simulating AI BUY signal")

    log_trade_decision(
        symbol=symbol + "USDT",
        side="BUY",
        action="AI_BUY",
        price=None,
        quantity=None,
        volume_usdt=volume_usdt,
        confidence=confidence,
        reason="Simulated AI BUY signal for safety test",
        dry_run=DRY_RUN,
        order_id="",
        status="ai_decision",
        raw_response={
            "source": "simulate_ai_buy.py",
            "symbol": symbol,
            "action": action,
            "confidence": confidence,
            "volume_usdt": volume_usdt,
        },
    )

    risk_result = validate_ai_trade(
        symbol=symbol,
        action=action,
        confidence=confidence,
        volume_usdt=volume_usdt,
    )

    risk_action = "RISK_APPROVED" if risk_result.get("approved") else "RISK_REJECTED"
    risk_status = "risk_approved" if risk_result.get("approved") else "risk_rejected"

    log_trade_decision(
        symbol=symbol + "USDT",
        side="BUY",
        action=risk_action,
        price=None,
        quantity=None,
        volume_usdt=volume_usdt,
        confidence=confidence,
        reason="Risk manager result: " + ", ".join(risk_result.get("reasons") or ["approved"]),
        dry_run=DRY_RUN,
        order_id="",
        status=risk_status,
        raw_response={
            "source": "simulate_ai_buy.py",
            "risk_result": risk_result,
        },
    )

    print("Risk result:", risk_result)

    if not risk_result.get("approved"):
        print("Trade rejected by risk manager.")
        return

    client = Client(
        api_key=BINANCE_API_KEY,
        api_secret=BINANCE_SECRET_KEY,
        requests_params={"timeout": BINANCE_API_TIMEOUT},
    )

    buy_result = buy(client, symbol, volume_usdt)

    print("Buy result:", buy_result)


if __name__ == "__main__":
    main()
