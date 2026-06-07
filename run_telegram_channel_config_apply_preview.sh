#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "====================================="
echo "TELEGRAM CHANNEL CONFIG APPLY PREVIEW"
echo "====================================="
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
  telegram_channel_config_apply_preview.py \
  telegram_channel_config_recommendations.py \
  scanner_real_channels.py

echo "[OK] Python files compiled successfully"

echo
echo "======================================"
echo "2. CHECK RECOMMENDATIONS FILE"
echo "======================================"

if [ ! -f "reports/telegram_channel_config_recommendations.json" ]; then
  echo "[WARN] Missing: reports/telegram_channel_config_recommendations.json"
  echo "Run ./run_telegram_channel_config_recommendations.sh first."
else
  echo "[OK] Found: reports/telegram_channel_config_recommendations.json"
fi

echo
echo "======================================"
echo "3. BUILD APPLY PREVIEW"
echo "======================================"
python telegram_channel_config_apply_preview.py

echo
echo "======================================"
echo "4. RECOMMENDED CONFIG PREVIEW"
echo "======================================"

if [ -f "reports/scanner_real_channels.recommended.py" ]; then
  cat reports/scanner_real_channels.recommended.py
else
  echo "[WARN] Missing: reports/scanner_real_channels.recommended.py"
fi

echo
echo "======================================"
echo "5. GENERATED FILES"
echo "======================================"
echo "Recommended PY: reports/scanner_real_channels.recommended.py"
echo "Preview JSON: reports/telegram_channel_config_apply_preview.json"
echo "Preview TXT: reports/telegram_channel_config_apply_preview.txt"

echo
echo "======================================"
echo "6. SAFETY RESULT"
echo "======================================"
echo "[OK] This script did not modify scanner_real_channels.py"
echo "[OK] This script did not read Telegram"
echo "[OK] This script did not call Binance API"
echo "[OK] This script did not create orders"
echo "[OK] Output is for manual review only"

echo
echo "DONE"
