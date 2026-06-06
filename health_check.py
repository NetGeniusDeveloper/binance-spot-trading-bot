import traceback

from binance.client import Client

from ai_strategy import analyze_symbol
from config import (
    ACTIVE_TRADING_SYMBOLS,
    BINANCE_API_TIMEOUT,
    DRY_RUN,
    MAX_DAILY_TRADES,
    MAX_TRADE_USDT,
    MIN_AI_CONFIDENCE,
    SEND_TELEGRAM_MESSAGE,
    WALLET_USAGE_PERCENT,
)
from credentials import BINANCE_API_KEY, BINANCE_SECRET_KEY, TELEGRAM_API_KEY
from risk_manager import validate_ai_trade
from trading_journal import DB_PATH, init_trading_journal_db, list_recent_decisions


def print_ok(message):
    print("[OK]", message)


def print_warn(message):
    print("[WARN]", message)


def print_fail(message):
    print("[FAIL]", message)


def check_config():
    print()
    print("CONFIG")
    print("------")

    print("DRY_RUN:", DRY_RUN)
    print("SEND_TELEGRAM_MESSAGE:", SEND_TELEGRAM_MESSAGE)
    print("WALLET_USAGE_PERCENT:", WALLET_USAGE_PERCENT)
    print("ACTIVE_TRADING_SYMBOLS:", ACTIVE_TRADING_SYMBOLS)
    print("MIN_AI_CONFIDENCE:", MIN_AI_CONFIDENCE)
    print("MAX_TRADE_USDT:", MAX_TRADE_USDT)
    print("MAX_DAILY_TRADES:", MAX_DAILY_TRADES)

    if DRY_RUN:
        print_ok("DRY_RUN включён")
    else:
        print_warn("DRY_RUN выключен. Реальная торговля может быть опасна.")

    if WALLET_USAGE_PERCENT <= 0:
        print_ok("WALLET_USAGE_PERCENT = 0.0, автоматическая покупка через main.py заблокирована")
    else:
        print_warn("WALLET_USAGE_PERCENT больше 0. Проверьте лимиты риска перед запуском.")

    if not SEND_TELEGRAM_MESSAGE:
        print_ok("Telegram-отправка отключена")
    else:
        print_warn("Telegram-отправка включена")


def check_credentials():
    print()
    print("CREDENTIALS")
    print("-----------")

    print("BINANCE_API_KEY exists:", bool(BINANCE_API_KEY))
    print("BINANCE_SECRET_KEY exists:", bool(BINANCE_SECRET_KEY))
    print("TELEGRAM_API_KEY exists:", bool(TELEGRAM_API_KEY))

    if not BINANCE_API_KEY or not BINANCE_SECRET_KEY:
        print_ok("Binance private keys не заданы — безопасно для DRY_RUN")
    else:
        print_warn("Binance keys заданы. Не выключайте DRY_RUN без отдельной проверки.")


def check_journal():
    print()
    print("TRADING JOURNAL")
    print("---------------")

    init_trading_journal_db()
    print("DB_PATH:", DB_PATH)

    rows = list_recent_decisions(limit=5)
    print("Recent rows:", len(rows))

    print_ok("SQLite-журнал доступен")


def check_risk_manager():
    print()
    print("RISK MANAGER")
    print("------------")

    test_symbol = ACTIVE_TRADING_SYMBOLS[0]["symbol"] if ACTIVE_TRADING_SYMBOLS else "ETH"

    result = validate_ai_trade(
        symbol=test_symbol,
        action="BUY",
        confidence=0.75,
        volume_usdt=min(5.0, MAX_TRADE_USDT),
    )

    print("Test result:", result)

    if result.get("approved"):
        print_ok("Risk manager разрешает валидную тестовую DRY_RUN-сделку")
    else:
        print_warn("Risk manager отклонил тестовую сделку: " + str(result.get("reasons")))


def check_binance_public_api():
    print()
    print("BINANCE PUBLIC API")
    print("------------------")

    client = Client(
        api_key=BINANCE_API_KEY,
        api_secret=BINANCE_SECRET_KEY,
        requests_params={"timeout": BINANCE_API_TIMEOUT},
    )

    status = client.get_system_status()
    print("System status:", status)

    ticker = client.get_symbol_ticker(symbol="BTCUSDT")
    print("BTCUSDT ticker:", ticker)

    print_ok("Binance public API доступен")

    return client


def check_ai_strategy(client):
    print()
    print("AI STRATEGY")
    print("-----------")

    symbol = ACTIVE_TRADING_SYMBOLS[0]["symbol"] if ACTIVE_TRADING_SYMBOLS else "ETH"
    decision = analyze_symbol(client, symbol, dry_run=DRY_RUN)

    print("Decision:", decision)

    if decision.get("action") in ("BUY", "SELL", "HOLD"):
        print_ok("AI strategy вернула корректное действие")
    else:
        print_fail("AI strategy вернула неизвестное действие")


def main():
    print("AI TRADING BOT HEALTH CHECK")
    print("===========================")

    try:
        check_config()
        check_credentials()
        check_journal()
        check_risk_manager()
        client = check_binance_public_api()
        check_ai_strategy(client)

        print()
        print("RESULT")
        print("------")
        print_ok("Health check завершён")

    except Exception as error:
        print()
        print_fail("Health check завершился ошибкой: " + str(error))
        traceback.print_exc()


if __name__ == "__main__":
    main()
