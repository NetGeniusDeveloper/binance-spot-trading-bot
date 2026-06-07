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
QUALITY_TXT="reports/telegram_channel_quality_report.txt"
QUALITY_JSON="reports/telegram_channel_quality_report.json"

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
echo "4. CHANNEL QUALITY SUMMARY"
echo "======================================"

if [ -f "${QUALITY_TXT}" ]; then
  cat "${QUALITY_TXT}"
else
  echo "[WARN] Missing channel quality TXT: ${QUALITY_TXT}"
fi

echo
echo "======================================"
echo "5. QUICK JSON STATUS"
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
echo "6. QUICK CHANNEL QUALITY STATUS"
echo "======================================"

if [ -f "${QUALITY_JSON}" ]; then
  python - <<'PY'
import json
from pathlib import Path

path = Path("reports/telegram_channel_quality_report.json")

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception as ex:
    print("[WARN] Cannot read channel quality JSON:", ex)
    raise SystemExit

print("Safe to continue:", payload.get("safe_to_continue"))
print("Channels analyzed:", payload.get("channels_analyzed"))
print("Keep:", payload.get("channels_keep"))
print("Watch:", payload.get("channels_watch"))
print("Disable:", payload.get("channels_disable"))
print("Preview messages collected:", payload.get("preview_messages_collected"))
print("Skipped old messages:", payload.get("preview_skipped_old_messages"))
print("Skipped empty messages:", payload.get("preview_skipped_empty_messages"))

blockers = payload.get("blockers", [])
warnings = payload.get("warnings", [])

print("Blockers:", ", ".join(blockers) if blockers else "none")
print("Warnings:", ", ".join(warnings) if warnings else "none")

channels = payload.get("channels", [])

if channels:
    print()
    print("Channel recommendations:")

    for item in channels:
        print(
            "- @{channel}: {recommendation} "
            "score={score} messages={messages} tickers={tickers}".format(
                channel=item.get("channel"),
                recommendation=item.get("recommendation"),
                score=item.get("quality_score"),
                messages=item.get("messages"),
                tickers=",".join(item.get("unique_tickers", [])) or "none",
            )
        )
PY
else
  echo "[WARN] Missing channel quality JSON: ${QUALITY_JSON}"
fi

echo
echo "======================================"
echo "7. SAFETY RESULT"
echo "======================================"
echo "[OK] This daily runner did not create orders"
echo "[OK] This daily runner did not start trading bot"
echo "[OK] Full pipeline log was saved locally"
echo "[OK] Final pipeline summary was printed for manual review"
echo "[OK] Channel quality summary was printed for manual review"
echo "[OK] Telegram sending still depends on safety flags"

echo
echo "DONE"
