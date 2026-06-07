#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "=========================================="
echo "SCANNER AGENT TELEGRAM SENDER DRY RUN"
echo "=========================================="
echo "Mode: analytical only"
echo "Orders: disabled"
echo "Trading: disabled"
echo "Telegram send: disabled"
echo "Telegram API: disabled"
echo "Binance API: disabled"
echo

echo "======================================"
echo "1. PYTHON COMPILE CHECK"
echo "======================================"
python -m py_compile \
  credentials.py \
  scanner_agent_decision.py \
  scanner_agent_decision_report.py \
  scanner_agent_notification_report.py \
  scanner_agent_telegram_message_preview.py \
  scanner_agent_telegram_sender_dry_run.py

echo "[OK] Python files compiled successfully"

echo
echo "======================================"
echo "2. CHECK REQUIRED FILES"
echo "======================================"

if [ ! -f "reports/scanner_agent_decision.json" ]; then
  echo "[WARN] Missing: reports/scanner_agent_decision.json"
  echo "Run ./run_telegram_real_market_scanner_safe.sh first."
fi

if [ ! -f "reports/scanner_agent_telegram_message_preview.txt" ]; then
  echo "[WARN] Missing: reports/scanner_agent_telegram_message_preview.txt"
  echo "Run ./run_scanner_agent_telegram_message_preview.sh first."
fi

if [ -f "reports/scanner_agent_decision.json" ]; then
  echo "[OK] Found: reports/scanner_agent_decision.json"
fi

if [ -f "reports/scanner_agent_telegram_message_preview.txt" ]; then
  echo "[OK] Found: reports/scanner_agent_telegram_message_preview.txt"
fi

echo
echo "======================================"
echo "3. SCANNER AGENT TELEGRAM MESSAGE PREVIEW"
echo "======================================"
python scanner_agent_telegram_message_preview.py

echo
echo "======================================"
echo "4. TELEGRAM SENDER DRY RUN"
echo "======================================"
python scanner_agent_telegram_sender_dry_run.py

echo
echo "======================================"
echo "5. GENERATED / USED FILES"
echo "======================================"
echo "Agent decision JSON: reports/scanner_agent_decision.json"
echo "Telegram message preview TXT: reports/scanner_agent_telegram_message_preview.txt"
echo "Telegram sender dry-run JSON: reports/scanner_agent_telegram_sender_dry_run.json"

echo
echo "======================================"
echo "6. SAFETY RESULT"
echo "======================================"
echo "[OK] This script did not create orders"
echo "[OK] This script did not run trading bot"
echo "[OK] This script did not read Telegram"
echo "[OK] This script did not send Telegram messages"
echo "[OK] This script did not call Binance API"
echo "[OK] This script only performs a local dry-run check"

echo
echo "DONE"
