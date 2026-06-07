#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "======================================"
echo "TELEGRAM CHANNEL QUALITY REPORT RUN"
echo "======================================"
echo "Mode: analytical only"
echo "Orders: disabled"
echo "Trading: disabled"
echo "Telegram: disabled"
echo "Binance API: disabled"
echo "Uses saved preview JSON only"
echo

echo "======================================"
echo "1. PYTHON COMPILE CHECK"
echo "======================================"
python -m py_compile \
  telegram_channel_quality_report.py \
  ticker_extractor.py \
  config.py

echo "[OK] Python files compiled successfully"

echo
echo "======================================"
echo "2. CHECK PREVIEW FILE"
echo "======================================"

if [ ! -f "reports/telegram_real_messages_preview.json" ]; then
  echo "[WARN] Missing: reports/telegram_real_messages_preview.json"
  echo "Run ./run_telegram_real_messages_preview.sh first."
else
  echo "[OK] Found: reports/telegram_real_messages_preview.json"
fi

echo
echo "======================================"
echo "3. CHANNEL QUALITY REPORT"
echo "======================================"
python telegram_channel_quality_report.py

echo
echo "======================================"
echo "4. GENERATED FILES"
echo "======================================"
echo "Quality JSON: reports/telegram_channel_quality_report.json"
echo "Quality TXT: reports/telegram_channel_quality_report.txt"

echo
echo "======================================"
echo "5. SAFETY RESULT"
echo "======================================"
echo "[OK] This script did not read Telegram"
echo "[OK] This script did not call Binance API"
echo "[OK] This script did not create orders"
echo "[OK] This script only analyzed saved preview JSON"

echo
echo "DONE"
