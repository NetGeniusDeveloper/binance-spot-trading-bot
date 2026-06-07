#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "======================================"
echo "TELEGRAM REAL MESSAGES ANALYZE"
echo "======================================"
echo "Mode: analytical only"
echo "Orders: disabled"
echo "Trading: disabled"
echo "Binance scanner: disabled"
echo

echo "======================================"
echo "1. PYTHON COMPILE CHECK"
echo "======================================"
python -m py_compile \
  credentials.py \
  scanner_real_channels.py \
  scanner_channels.py \
  telegram_real_mode_check.py \
  telegram_connection_test.py \
  telegram_channel_metadata_check.py \
  telegram_social_collector.py \
  telegram_real_messages_preview.py \
  telegram_real_messages_analyze.py \
  social_signal_engine.py \
  ticker_extractor.py

echo "[OK] Python files compiled successfully"

echo
echo "======================================"
echo "2. REAL MESSAGES PREVIEW"
echo "======================================"
python telegram_real_messages_preview.py

echo
echo "======================================"
echo "3. REAL MESSAGES SOCIAL ANALYSIS"
echo "======================================"
python telegram_real_messages_analyze.py

echo
echo "======================================"
echo "4. GENERATED FILES"
echo "======================================"
echo "Telegram preview JSON: reports/telegram_real_messages_preview.json"
echo "Telegram social analysis JSON: reports/telegram_real_social_signals.json"

echo
echo "======================================"
echo "5. SAFETY RESULT"
echo "======================================"
echo "[OK] This script did not create orders"
echo "[OK] This script did not run trading bot"
echo "[OK] This script did not run Binance market scanner"
echo "[OK] This script analyzed saved Telegram messages only"

echo
echo "DONE"
