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
echo "2. CLEAR SCANNER DEMO HISTORY"
echo "======================================"
python clear_scanner_demo_history.py

echo
echo "======================================"
echo "3. REAL MARKET SCANNER DEMO"
echo "======================================"
python scanner_real_market_demo.py

echo
echo "======================================"
echo "4. SCANNER STORAGE REPORT"
echo "======================================"
python scanner_storage_report.py

echo
echo "======================================"
echo "5. SCANNER AGENT JSON EXPORT"
echo "======================================"
python scanner_agent_export.py

echo
echo "======================================"
echo "6. GENERATED FILES"
echo "======================================"
echo "Markdown report: reports/social_scanner_demo_report.md"
echo "JSON export: reports/scanner_agent_export.json"
echo "SQLite DB: data/social_scanner.db"

echo
echo "DONE"
