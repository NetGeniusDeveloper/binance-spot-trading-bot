#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "======================================"
echo "1. FRESH SCANNER DEMO PIPELINE"
echo "======================================"
./run_scanner_demo_fresh.sh

echo
echo "======================================"
echo "2. SCANNER AGENT JSON EXPORT"
echo "======================================"
python scanner_agent_export.py

echo
echo "======================================"
echo "3. GENERATED AGENT EXPORT"
echo "======================================"
echo "JSON export: reports/scanner_agent_export.json"

echo
echo "DONE"
