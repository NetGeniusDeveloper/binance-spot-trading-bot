#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "======================================"
echo "TELEGRAM CHANNEL DISCOVERY SAFE RUN"
echo "======================================"
echo "Mode: analytical only"
echo "Orders: disabled"
echo "Trading: disabled"
echo "Binance API: disabled"
echo "Reads only limited public Telegram channel data"
echo

echo "======================================"
echo "1. PYTHON COMPILE CHECK"
echo "======================================"
python -m py_compile \
  credentials.py \
  telegram_connection_test.py \
  binance_symbol_universe.py \
  telegram_channel_discovery_safe.py

echo "[OK] Python files compiled successfully"

echo
echo "======================================"
echo "2. CHECK CANDIDATE FILE"
echo "======================================"

if [ ! -f "data/telegram_channel_candidates.txt" ]; then
  echo "[WARN] Missing: data/telegram_channel_candidates.txt"
  echo "Create it and add public Telegram channel usernames."
fi

if [ -f "data/telegram_channel_candidates.txt" ]; then
  echo "[OK] Found: data/telegram_channel_candidates.txt"
fi

echo
echo "======================================"
echo "3. CHANNEL DISCOVERY"
echo "======================================"
python telegram_channel_discovery_safe.py

echo
echo "======================================"
echo "4. GENERATED FILES"
echo "======================================"
echo "Discovery JSON: reports/telegram_channel_discovery.json"
echo "Discovery TXT: reports/telegram_channel_discovery.txt"

echo
echo "======================================"
echo "5. SAFETY RESULT"
echo "======================================"
echo "[OK] This script did not create orders"
echo "[OK] This script did not run trading bot"
echo "[OK] This script did not call Binance API"
echo "[OK] This script reads only limited public Telegram channel data"
echo "[OK] Results are for manual review only"

echo
echo "DONE"
