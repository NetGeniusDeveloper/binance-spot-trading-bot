import logging

from binance.client import Client

from config import BINANCE_API_TIMEOUT, DRY_RUN
from credentials import BINANCE_API_KEY, BINANCE_SECRET_KEY
from risk_manager import validate_ai_trade
from sell_asset import sell
from trading_journal import log_trade_decision


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    symbol = "BTC"
    action = "SELL"
    confidence = 0.75
    volume_usdt = 0.0

    logging.info("Simulating AI SELL signal")

    log_trade_decision(
        symbol=symbol + "USDT",
        side="SELL",
        action="AI_SELL",
        price=None,
        quantity=None,
        volume_usdt=volume_usdt,
        confidence=confidence,
        reason="Simulated AI SELL signal for safety test",
        dry_run=DRY_RUN,
        order_id="",
        status="ai_decision",
        raw_response={
            "source": "simulate_ai_sell.py",
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
        side="SELL",
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
            "source": "simulate_ai_sell.py",
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

    sell_result = sell(client, symbol)

    print("Sell result:", sell_result)


if __name__ == "__main__":
    main()
