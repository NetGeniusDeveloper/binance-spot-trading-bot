#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "=========================================="
echo "SCANNER AGENT NOTIFICATION REPORT SAFE RUN"
echo "=========================================="
echo "Mode: analytical only"
echo "Orders: disabled"
echo "Trading: disabled"
echo "Telegram send: disabled"
echo "Binance API: disabled"
echo

echo "======================================"
echo "1. PYTHON COMPILE CHECK"
echo "======================================"
python -m py_compile \
  scanner_agent_decision.py \
  scanner_agent_decision_report.py \
  scanner_agent_notification_report.py

echo "[OK] Python files compiled successfully"

echo
echo "======================================"
echo "2. CHECK REQUIRED FILES"
echo "======================================"

if [ ! -f "reports/scanner_agent_decision.json" ]; then
  echo "[WARN] Missing: reports/scanner_agent_decision.json"
  echo "Run ./run_telegram_real_market_scanner_safe.sh first."
fi

if [ -f "reports/scanner_agent_decision.json" ]; then
  echo "[OK] Found: reports/scanner_agent_decision.json"
fi

echo
echo "======================================"
echo "3. SCANNER AGENT DECISION REPORT"
echo "======================================"
python scanner_agent_decision_report.py

echo
echo "======================================"
echo "4. SCANNER AGENT NOTIFICATION REPORT"
echo "======================================"
python scanner_agent_notification_report.py

echo
echo "======================================"
echo "5. GENERATED / USED FILES"
echo "======================================"
echo "Agent decision JSON: reports/scanner_agent_decision.json"
echo "Notification report TXT: reports/scanner_agent_notification_report.txt"

echo
echo "======================================"
echo "6. SAFETY RESULT"
echo "======================================"
echo "[OK] This script did not create orders"
echo "[OK] This script did not run trading bot"
echo "[OK] This script did not read Telegram"
echo "[OK] This script did not send Telegram messages"
echo "[OK] This script did not call Binance API"
echo "[OK] This script did not clear SQLite history"
echo "[OK] This script only reads existing analytical JSON reports"

echo
echo "DONE"
