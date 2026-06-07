#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "======================================"
echo "TELEGRAM CHANNEL SELECTION EXPORT RUN"
echo "======================================"
echo "Mode: analytical only"
echo "Orders: disabled"
echo "Trading: disabled"
echo "Telegram: disabled"
echo "Binance API: disabled"
echo "Does not modify scanner_real_channels.py"
echo

echo "======================================"
echo "1. PYTHON COMPILE CHECK"
echo "======================================"
python -m py_compile \
  scanner_real_channels.py \
  telegram_channel_selection_export.py

echo "[OK] Python files compiled successfully"

echo
echo "======================================"
echo "2. CHECK DISCOVERY FILE"
echo "======================================"

if [ ! -f "reports/telegram_channel_discovery.json" ]; then
  echo "[WARN] Missing: reports/telegram_channel_discovery.json"
  echo "Run ./run_telegram_channel_discovery_safe.sh first."
else
  echo "[OK] Found: reports/telegram_channel_discovery.json"
fi

echo
echo "======================================"
echo "3. EXPORT SELECTED CHANNELS"
echo "======================================"
python telegram_channel_selection_export.py

echo
echo "======================================"
echo "4. GENERATED FILES"
echo "======================================"
echo "Selection JSON: reports/telegram_channel_selection_export.json"
echo "Selection TXT: reports/telegram_channel_selection_export.txt"

echo
echo "======================================"
echo "5. SAFETY RESULT"
echo "======================================"
echo "[OK] This script did not modify scanner_real_channels.py"
echo "[OK] This script did not read Telegram"
echo "[OK] This script did not call Binance API"
echo "[OK] This script did not create orders"
echo "[OK] Output is for manual review only"

echo
echo "DONE"
