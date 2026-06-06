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
echo "2. SCANNER DEMO"
echo "======================================"
python scanner_demo.py

echo
echo "======================================"
echo "3. SCANNER STORAGE REPORT"
echo "======================================"
python scanner_storage_report.py

echo
echo "======================================"
echo "4. GENERATED REPORT"
echo "======================================"
echo "Markdown report: reports/social_scanner_demo_report.md"
echo "SQLite DB: data/social_scanner.db"

echo
echo "DONE"
