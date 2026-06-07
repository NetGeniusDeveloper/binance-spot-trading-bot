#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "======================================"
echo "TELEGRAM REAL MESSAGES PREVIEW"
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
  social_signal_engine.py

echo "[OK] Python files compiled successfully"

echo
echo "======================================"
echo "2. SCANNER CHANNELS CONFIG"
echo "======================================"
python scanner_channels.py

echo
echo "======================================"
echo "3. TELEGRAM REAL MODE READINESS CHECK"
echo "======================================"
python telegram_real_mode_check.py

echo
echo "======================================"
echo "4. TELEGRAM CONNECTION TEST"
echo "======================================"
python telegram_connection_test.py

echo
echo "======================================"
echo "5. TELEGRAM CHANNEL METADATA CHECK"
echo "======================================"
python telegram_channel_metadata_check.py

echo
echo "======================================"
echo "6. TELEGRAM REAL MESSAGES PREVIEW"
echo "======================================"
python telegram_real_messages_preview.py

echo
echo "======================================"
echo "7. GENERATED FILES"
echo "======================================"
echo "Telegram preview JSON: reports/telegram_real_messages_preview.json"

echo
echo "======================================"
echo "8. SAFETY RESULT"
echo "======================================"
echo "[OK] This script did not create orders"
echo "[OK] This script did not run trading bot"
echo "[OK] This script did not run Binance market scanner"
echo "[OK] This script reads only limited public Telegram messages from scanner_real_channels.py"
echo
echo "DONE"
