#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "===================================="
echo "TELEGRAM CHANNEL CONFIG APPLY MANUAL"
echo "===================================="
echo "Mode: manual apply"
echo "Requires: APPLY_CHANNEL_CONFIG_CONFIRM=YES"
echo "Orders: disabled"
echo "Trading: disabled"
echo "Telegram: disabled"
echo "Binance API: disabled"
echo

echo "======================================"
echo "1. PYTHON COMPILE CHECK"
echo "======================================"
python -m py_compile \
  telegram_channel_config_apply_manual.py \
  scanner_real_channels.py

echo "[OK] Python files compiled successfully"

echo
echo "======================================"
echo "2. CHECK RECOMMENDED CONFIG"
echo "======================================"

if [ ! -f "reports/scanner_real_channels.recommended.py" ]; then
  echo "[WARN] Missing: reports/scanner_real_channels.recommended.py"
  echo "Run ./run_telegram_channel_config_apply_preview.sh first."
else
  echo "[OK] Found: reports/scanner_real_channels.recommended.py"
fi

echo
echo "======================================"
echo "3. MANUAL APPLY"
echo "======================================"
python telegram_channel_config_apply_manual.py

echo
echo "======================================"
echo "4. GENERATED FILES"
echo "======================================"
echo "Apply JSON: reports/telegram_channel_config_apply_manual.json"
echo "Apply TXT: reports/telegram_channel_config_apply_manual.txt"
echo "Backup: reports/scanner_real_channels.backup.py"

echo
echo "======================================"
echo "5. SAFETY RESULT"
echo "======================================"
echo "[OK] This script requires APPLY_CHANNEL_CONFIG_CONFIRM=YES"
echo "[OK] This script does not read Telegram"
echo "[OK] This script does not call Binance API"
echo "[OK] This script does not create orders"

echo
echo "DONE"
