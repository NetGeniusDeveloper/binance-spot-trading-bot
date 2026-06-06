#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "======================================"
echo "1. NETWORK CHECK"
echo "======================================"
python network_check.py

echo
echo "======================================"
echo "2. HEALTH CHECK"
echo "======================================"
python health_check.py

echo
echo "======================================"
echo "3. RUN BOT"
echo "======================================"
python main.py

echo
echo "======================================"
echo "4. JOURNAL REPORT"
echo "======================================"
python journal_report.py
