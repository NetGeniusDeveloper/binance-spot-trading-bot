#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "=================================================="
echo "FULL SCANNER AGENT NOTIFICATION PIPELINE SAFE RUN"
echo "=================================================="
echo "Mode: analytical only"
echo "Orders: disabled"
echo "Trading: disabled"
echo "Binance orders: disabled"
echo "Telegram sending: controlled by SCANNER_TELEGRAM_SEND_ENABLED"
echo "Telegram sender will be skipped when total_decisions=0"
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
  scanner_agent_decision.py \
  scanner_agent_decision_report.py \
  scanner_agent_notification_report.py \
  scanner_agent_telegram_message_preview.py \
  scanner_agent_telegram_sender_dry_run.py \
  scanner_agent_telegram_sender.py

echo "[OK] Python files compiled successfully"

echo
echo "======================================"
echo "2. BASH SYNTAX CHECK"
echo "======================================"
bash -n run_telegram_real_market_scanner_safe.sh
bash -n run_scanner_agent_decision_report.sh
bash -n run_scanner_agent_notification_report.sh
bash -n run_scanner_agent_telegram_message_preview.sh
bash -n run_scanner_agent_telegram_sender_safe.sh

echo "[OK] Bash runner files syntax is valid"

echo
echo "======================================"
echo "3. REAL TELEGRAM MARKET SCANNER SAFE PIPELINE"
echo "======================================"
./run_telegram_real_market_scanner_safe.sh

echo
echo "======================================"
echo "4. SCANNER AGENT DECISION REPORT SAFE RUN"
echo "======================================"
./run_scanner_agent_decision_report.sh

echo
echo "======================================"
echo "5. SCANNER AGENT NOTIFICATION REPORT SAFE RUN"
echo "======================================"
./run_scanner_agent_notification_report.sh

echo
echo "======================================"
echo "6. SCANNER AGENT TELEGRAM MESSAGE PREVIEW SAFE RUN"
echo "======================================"
./run_scanner_agent_telegram_message_preview.sh

echo
echo "======================================"
echo "7. DECISION COUNT CHECK BEFORE TELEGRAM SENDER"
echo "======================================"

TOTAL_DECISIONS=$(python - <<'PY'
import json
from pathlib import Path

path = Path("reports") / "scanner_agent_decision.json"

if not path.exists():
    print(0)
    raise SystemExit

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print(0)
    raise SystemExit

decisions = payload.get("decisions", [])

if not isinstance(decisions, list):
    decisions = []

total_decisions = payload.get("total_decisions")

try:
    total_decisions = int(total_decisions)
except Exception:
    total_decisions = len(decisions)

print(total_decisions)
PY
)

echo "Total decisions detected: ${TOTAL_DECISIONS}"

if [ "$TOTAL_DECISIONS" -le 0 ]; then
  echo "[OK] No analytical decisions found."
  echo "[OK] Telegram sender safe run skipped to avoid empty notification."
  echo "[OK] Reports and preview files were still generated."
else
  echo "[OK] Analytical decisions found."
  echo "[OK] Running Telegram sender safe runner."
  echo
  echo "======================================"
  echo "8. SCANNER AGENT TELEGRAM SENDER SAFE RUN"
  echo "======================================"
  ./run_scanner_agent_telegram_sender_safe.sh
fi

echo
echo "======================================"
echo "9. FINAL GENERATED / USED FILES"
echo "======================================"
echo "Telegram preview JSON: reports/telegram_real_messages_preview.json"
echo "Telegram social analysis JSON: reports/telegram_real_social_signals.json"
echo "Telegram market rated JSON: reports/telegram_real_market_rated_signals.json"
echo "Markdown report: reports/social_scanner_demo_report.md"
echo "Agent export JSON: reports/scanner_agent_export.json"
echo "Agent decision JSON: reports/scanner_agent_decision.json"
echo "Agent notification report TXT: reports/scanner_agent_notification_report.txt"
echo "Telegram message preview TXT: reports/scanner_agent_telegram_message_preview.txt"
echo "Telegram sender dry-run JSON: reports/scanner_agent_telegram_sender_dry_run.json"
echo "Telegram sender result JSON: reports/scanner_agent_telegram_sender_result.json"
echo "SQLite DB: data/social_scanner.db"

echo
echo "======================================"
echo "10. FINAL SAFETY RESULT"
echo "======================================"
echo "[OK] This full pipeline did not create orders"
echo "[OK] This full pipeline did not run trading bot"
echo "[OK] Binance was used only for public market metrics"
echo "[OK] Telegram channel reading was limited to the configured analytical scanner"
echo "[OK] Telegram notification sending is controlled only by SCANNER_TELEGRAM_SEND_ENABLED"
echo "[OK] Default safe value is SCANNER_TELEGRAM_SEND_ENABLED=false"
echo "[OK] Telegram sender is skipped when total_decisions=0"
echo "[OK] Final notification is analytical only"

echo
echo "DONE"
