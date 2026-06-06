#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "======================================"
echo "TELEGRAM COLLECTOR SAFE CHECK"
echo "======================================"
echo "Mode: analytical only"
echo "Orders: disabled"
echo "Trading: disabled"
echo

echo "======================================"
echo "1. PYTHON COMPILE CHECK"
echo "======================================"
python -m py_compile \
  credentials.py \
  scanner_real_channels.py \
  scanner_channels.py \
  telegram_social_collector.py \
  social_signal_engine.py

echo "[OK] Python files compiled successfully"

echo
echo "======================================"
echo "2. SCANNER CHANNELS CONFIG"
echo "======================================"
python scanner_channels.py

echo
echo "======================================"
echo "3. TELEGRAM COLLECTOR STATUS"
echo "======================================"
python telegram_social_collector.py

echo
echo "======================================"
echo "4. SOCIAL SIGNAL ENGINE DEMO CHECK"
echo "======================================"
python social_signal_engine.py

echo
echo "======================================"
echo "5. SAFETY RESULT"
echo "======================================"
echo "[OK] Telegram collector check completed"
echo "[OK] This script did not create orders"
echo "[OK] This script did not run trading bot"
echo "[OK] This script did not run Binance market scanner"
echo "[OK] Real Telegram channels are controlled by scanner_real_channels.py"
echo
echo "DONE"
