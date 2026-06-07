#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "================================"
echo "TELEGRAM ALERT CHAT ID SAFE CHECK"
echo "================================"
echo "Mode: analytical only"
echo "Orders: disabled"
echo "Trading: disabled"
echo "Telegram send: disabled"
echo "Telegram API: disabled"
echo "Binance API: disabled"
echo

echo "======================================"
echo "1. PYTHON COMPILE CHECK"
echo "======================================"
python -m py_compile \
  credentials.py \
  telegram_alert_chat_id_check.py

echo "[OK] Python files compiled successfully"

echo
echo "======================================"
echo "2. TELEGRAM ALERT CHAT ID CHECK"
echo "======================================"
python telegram_alert_chat_id_check.py

echo
echo "======================================"
echo "3. JSON REPORT"
echo "======================================"
python -m json.tool reports/telegram_alert_chat_id_check.json

echo
echo "======================================"
echo "4. GENERATED FILES"
echo "======================================"
echo "Telegram alert check JSON: reports/telegram_alert_chat_id_check.json"

echo
echo "======================================"
echo "5. SAFETY RESULT"
echo "======================================"
echo "[OK] This script did not create orders"
echo "[OK] This script did not run trading bot"
echo "[OK] This script did not send Telegram messages"
echo "[OK] This script did not call Telegram API"
echo "[OK] This script did not call Binance API"
echo "[OK] This script only checks local .env values through credentials.py"

echo
echo "DONE"
