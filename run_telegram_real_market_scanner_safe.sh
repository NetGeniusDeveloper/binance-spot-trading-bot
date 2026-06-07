#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "======================================"
echo "TELEGRAM REAL MARKET SCANNER SAFE RUN"
echo "======================================"
echo "Mode: analytical only"
echo "Orders: disabled"
echo "Trading: disabled"
echo "Binance orders: disabled"
echo

echo "======================================"
echo "1. PYTHON COMPILE CHECK"
echo "======================================"
python -m py_compile \
  credentials.py \
  scanner_real_channels.py \
  scanner_channels.py \
  telegram_real_mode_check.py \
  telegram_connection_test.py \
  telegram_channel_metadata_check.py \
  telegram_social_collector.py \
  telegram_real_messages_preview.py \
  telegram_real_messages_analyze.py \
  telegram_real_market_scanner.py \
  social_signal_engine.py \
  ticker_extractor.py \
  scanner_market_data.py \
  signal_rating.py \
  scanner_storage.py \
  scanner_report.py \
  scanner_storage_report.py \
  clear_scanner_demo_history.py \
  scanner_agent_export.py \
  scanner_agent_export_report.py \
  scanner_agent_decision.py

echo "[OK] Python files compiled successfully"

echo
echo "======================================"
echo "2. CLEAR SCANNER HISTORY"
echo "======================================"
python clear_scanner_demo_history.py

echo
echo "======================================"
echo "3. TELEGRAM REAL MESSAGES ANALYZE"
echo "======================================"
./run_telegram_real_messages_analyze.sh

echo
echo "======================================"
echo "4. TELEGRAM REAL MARKET SCANNER"
echo "======================================"
python telegram_real_market_scanner.py

echo
echo "======================================"
echo "5. SCANNER STORAGE REPORT"
echo "======================================"
python scanner_storage_report.py

echo
echo "======================================"
echo "6. SCANNER AGENT JSON EXPORT"
echo "======================================"
python scanner_agent_export.py

echo
echo "======================================"
echo "7. SCANNER AGENT EXPORT REPORT"
echo "======================================"
python scanner_agent_export_report.py

echo
echo "======================================"
echo "8. SCANNER AGENT DECISION"
echo "======================================"
python scanner_agent_decision.py

echo
echo "======================================"
echo "9. GENERATED FILES"
echo "======================================"
echo "Telegram preview JSON: reports/telegram_real_messages_preview.json"
echo "Telegram social analysis JSON: reports/telegram_real_social_signals.json"
echo "Telegram market rated JSON: reports/telegram_real_market_rated_signals.json"
echo "Markdown report: reports/social_scanner_demo_report.md"
echo "Agent export JSON: reports/scanner_agent_export.json"
echo "Agent decision JSON: reports/scanner_agent_decision.json"
echo "SQLite DB: data/social_scanner.db"

echo
echo "======================================"
echo "10. SAFETY RESULT"
echo "======================================"
echo "[OK] This script did not create orders"
echo "[OK] This script did not run trading bot"
echo "[OK] This script cleared only analytical scanner_signals history"
echo "[OK] This script used Telegram only for limited public channel messages"
echo "[OK] This script used Binance only for public market metrics"
echo "[OK] This script created only analytical agent decisions"

echo
echo "DONE"
