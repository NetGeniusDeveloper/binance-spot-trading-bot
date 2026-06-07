#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "================================="
echo "SCANNER AGENT TELEGRAM SENDER RUN"
echo "================================="
echo "Mode: analytical only"
echo "Orders: disabled"
echo "Trading: disabled"
echo "Binance API: disabled"
echo "Telegram send: controlled by SCANNER_TELEGRAM_SEND_ENABLED"
echo "Manual confirm: controlled by SCANNER_TELEGRAM_MANUAL_CONFIRM"
echo "Real Telegram sending requires BOTH flags to be true"
echo

echo "======================================"
echo "1. PYTHON COMPILE CHECK"
echo "======================================"
python -m py_compile \
  credentials.py \
  scanner_agent_telegram_message_preview.py \
  scanner_agent_telegram_sender_dry_run.py \
  scanner_agent_telegram_sender.py

echo "[OK] Python files compiled successfully"

echo
echo "======================================"
echo "2. CHECK REQUIRED FILES"
echo "======================================"

if [ ! -f "reports/scanner_agent_telegram_message_preview.txt" ]; then
  echo "[WARN] Missing: reports/scanner_agent_telegram_message_preview.txt"
  echo "Run ./run_scanner_agent_telegram_message_preview.sh first."
fi

if [ -f "reports/scanner_agent_telegram_message_preview.txt" ]; then
  echo "[OK] Found: reports/scanner_agent_telegram_message_preview.txt"
fi

echo
echo "======================================"
echo "3. TELEGRAM MESSAGE PREVIEW"
echo "======================================"
python scanner_agent_telegram_message_preview.py

echo
echo "======================================"
echo "4. TELEGRAM SENDER DRY RUN"
echo "======================================"
python scanner_agent_telegram_sender_dry_run.py

echo
echo "======================================"
echo "5. TELEGRAM SENDER"
echo "======================================"
python scanner_agent_telegram_sender.py

echo
echo "======================================"
echo "6. GENERATED / USED FILES"
echo "======================================"
echo "Telegram message preview TXT: reports/scanner_agent_telegram_message_preview.txt"
echo "Telegram sender dry-run JSON: reports/scanner_agent_telegram_sender_dry_run.json"
echo "Telegram sender result JSON: reports/scanner_agent_telegram_sender_result.json"

echo
echo "======================================"
echo "7. SAFETY RESULT"
echo "======================================"
echo "[OK] This script did not create orders"
echo "[OK] This script did not run trading bot"
echo "[OK] This script did not call Binance API"
echo "[OK] Telegram sending is controlled by SCANNER_TELEGRAM_SEND_ENABLED"
echo "[OK] Manual confirmation is controlled by SCANNER_TELEGRAM_MANUAL_CONFIRM"
echo "[OK] Default safe value for both flags is false"

echo
echo "DONE"
