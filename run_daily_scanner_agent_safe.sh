#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

mkdir -p reports

LOG_FILE="reports/daily_scanner_agent_pipeline.log"
SUMMARY_TXT="reports/scanner_agent_pipeline_summary.txt"
SUMMARY_JSON="reports/scanner_agent_pipeline_summary.json"

echo "======================================"
echo "DAILY SCANNER AGENT SAFE RUN"
echo "======================================"
echo "Mode: analytical only"
echo "Orders: disabled"
echo "Trading: disabled"
echo "Binance orders: disabled"
echo "Telegram sending: controlled by safety flags"
echo "Full log: ${LOG_FILE}"
echo

echo "======================================"
echo "1. BASH SYNTAX CHECK"
echo "======================================"
bash -n run_full_scanner_agent_notification_pipeline_safe.sh
echo "[OK] Full pipeline bash syntax is valid"

echo
echo "======================================"
echo "2. RUN FULL SAFE PIPELINE"
echo "======================================"
echo "[INFO] Running full pipeline. This may take some time..."
echo

./run_full_scanner_agent_notification_pipeline_safe.sh > "${LOG_FILE}" 2>&1

echo "[OK] Full safe pipeline finished"
echo "[OK] Full log saved to: ${LOG_FILE}"

echo
echo "======================================"
echo "3. FINAL SUMMARY"
echo "======================================"

if [ -f "${SUMMARY_TXT}" ]; then
  cat "${SUMMARY_TXT}"
else
  echo "[WARN] Missing summary TXT: ${SUMMARY_TXT}"
fi

echo
echo "======================================"
echo "4. QUICK JSON STATUS"
echo "======================================"

if [ -f "${SUMMARY_JSON}" ]; then
  python - <<'PY'
import json
from pathlib import Path

path = Path("reports/scanner_agent_pipeline_summary.json")

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception as ex:
    print("[WARN] Cannot read summary JSON:", ex)
    raise SystemExit

print("Final status:", payload.get("final_status"))
print("Safe pipeline:", payload.get("safe_pipeline"))
print("Signals loaded:", payload.get("scanner", {}).get("total_signals_loaded"))
print("Decisions:", payload.get("decisions", {}).get("total_decisions"))
print("Telegram send enabled:", payload.get("telegram", {}).get("telegram_send_enabled"))
print("Telegram manual confirm:", payload.get("telegram", {}).get("telegram_manual_confirm"))
print("Telegram message sent:", payload.get("telegram", {}).get("telegram_message_sent"))

blockers = payload.get("blockers", [])
warnings = payload.get("warnings", [])

print("Blockers:", ", ".join(blockers) if blockers else "none")
print("Warnings:", ", ".join(warnings) if warnings else "none")
PY
else
  echo "[WARN] Missing summary JSON: ${SUMMARY_JSON}"
fi

echo
echo "======================================"
echo "5. SAFETY RESULT"
echo "======================================"
echo "[OK] This daily runner did not create orders"
echo "[OK] This daily runner did not start trading bot"
echo "[OK] Full pipeline log was saved locally"
echo "[OK] Final summary was printed for manual review"
echo "[OK] Telegram sending still depends on safety flags"

echo
echo "DONE"
