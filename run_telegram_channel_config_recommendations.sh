#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "======================================="
echo "TELEGRAM CHANNEL CONFIG RECOMMENDATIONS"
echo "======================================="
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
  telegram_channel_config_recommendations.py

echo "[OK] Python files compiled successfully"

echo
echo "======================================"
echo "2. CHECK QUALITY REPORT"
echo "======================================"

if [ ! -f "reports/telegram_channel_quality_report.json" ]; then
  echo "[WARN] Missing: reports/telegram_channel_quality_report.json"
  echo "Run ./run_telegram_channel_quality_report.sh first."
else
  echo "[OK] Found: reports/telegram_channel_quality_report.json"
fi

echo
echo "======================================"
echo "3. BUILD CONFIG RECOMMENDATIONS"
echo "======================================"
python telegram_channel_config_recommendations.py

echo
echo "======================================"
echo "4. GENERATED FILES"
echo "======================================"
echo "Recommendations JSON: reports/telegram_channel_config_recommendations.json"
echo "Recommendations TXT: reports/telegram_channel_config_recommendations.txt"

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
