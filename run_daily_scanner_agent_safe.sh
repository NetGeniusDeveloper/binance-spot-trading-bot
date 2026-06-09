#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

# Safe daily runner default:
# Telegram delivery is disabled even if local .env contains enabled flags.
# To allow analytical Telegram delivery for this runner, explicitly run:
# ALLOW_TELEGRAM_SEND_IN_DAILY_SAFE_RUN=true ./run_daily_scanner_agent_safe.sh
ALLOW_TELEGRAM_SEND_IN_DAILY_SAFE_RUN="${ALLOW_TELEGRAM_SEND_IN_DAILY_SAFE_RUN:-false}"

if [ "${ALLOW_TELEGRAM_SEND_IN_DAILY_SAFE_RUN}" != "true" ]; then
  export SCANNER_TELEGRAM_SEND_ENABLED="false"
  export SCANNER_TELEGRAM_MANUAL_CONFIRM="false"
fi

mkdir -p reports

LOG_FILE="reports/daily_scanner_agent_pipeline.log"
SUMMARY_TXT="reports/scanner_agent_pipeline_summary.txt"
SUMMARY_JSON="reports/scanner_agent_pipeline_summary.json"
QUALITY_TXT="reports/telegram_channel_quality_report.txt"
QUALITY_JSON="reports/telegram_channel_quality_report.json"
RECOMMENDATIONS_TXT="reports/telegram_channel_config_recommendations.txt"
RECOMMENDATIONS_JSON="reports/telegram_channel_config_recommendations.json"
AUDIT_TXT="reports/scanner_agent_telegram_sender_audit_report.txt"
AUDIT_JSON="reports/scanner_agent_telegram_sender_audit_report.json"
SAFETY_GATE_TXT="reports/scanner_agent_safety_gate_report.txt"
SAFETY_GATE_JSON="reports/scanner_agent_safety_gate_report.json"
BLOCKED_RISK_TXT="reports/scanner_agent_blocked_risk_report.txt"
BLOCKED_RISK_JSON="reports/scanner_agent_blocked_risk_report.json"
WATCHLIST_TXT="reports/scanner_agent_watchlist_report.txt"
WATCHLIST_JSON="reports/scanner_agent_watchlist_report.json"

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
echo "3A. TELEGRAM SENDER AUDIT GENERATION"
echo "======================================"

SKIP_TELEGRAM_AUDIT=$(python - <<'PYAUDIT'
import json
from pathlib import Path

path = Path("reports/scanner_agent_pipeline_summary.json")

if not path.exists():
    print("false")
    raise SystemExit

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("false")
    raise SystemExit

telegram = payload.get("telegram", {})

if not isinstance(telegram, dict):
    telegram = {}

ignored = bool(telegram.get("sender_result_ignored_because_no_decisions"))
final_status = str(payload.get("final_status", ""))

if ignored and final_status == "no_decisions":
    print("true")
else:
    print("false")
PYAUDIT
)

if [ "${SKIP_TELEGRAM_AUDIT}" = "true" ]; then
  echo "[OK] Telegram sender audit skipped for current run."
  echo "[OK] Current pipeline has no decisions."
  echo "[OK] Any old Telegram sender result is intentionally ignored."
  echo "[OK] No Telegram message was sent by the current safe daily run."
else
  python scanner_agent_telegram_sender_audit_report.py || echo "[WARN] Telegram sender audit report failed"
fi

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
echo "3B. BLOCKED RISK REPORT"
echo "======================================"
python scanner_agent_blocked_risk_report.py || echo "[WARN] Blocked risk report failed"

if [ -f "${BLOCKED_RISK_TXT}" ]; then
  cat "${BLOCKED_RISK_TXT}"
else
  echo "[WARN] Missing blocked risk TXT: ${BLOCKED_RISK_TXT}"
fi

echo
echo "Blocked risk JSON: ${BLOCKED_RISK_JSON}"
if [ -f "${BLOCKED_RISK_JSON}" ]; then
  python - <<'PYBR'
import json
from pathlib import Path

path = Path("reports/scanner_agent_blocked_risk_report.json")

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception as ex:
    print("[WARN] Cannot read blocked risk JSON:", ex)
    raise SystemExit

print("Blocked risk safe to continue:", payload.get("safe_to_continue"))
print("Blocked risk count:", payload.get("blocked_count"))
print("Blocked risk levels:", payload.get("summary_by_risk_level"))
print("Blocked risk flags:", payload.get("summary_by_risk_flag"))
print("Blocked risk blockers:", ", ".join(payload.get("blockers", [])) or "none")
print("Blocked risk warnings:", ", ".join(payload.get("warnings", [])) or "none")
PYBR
else
  echo "[WARN] Missing blocked risk JSON: ${BLOCKED_RISK_JSON}"
fi

echo
echo "======================================"
echo "3C. WATCHLIST REPORT"
echo "======================================"
python scanner_agent_watchlist_report.py || echo "[WARN] Watchlist report failed"

if [ -f "${WATCHLIST_TXT}" ]; then
  cat "${WATCHLIST_TXT}"
else
  echo "[WARN] Missing watchlist TXT: ${WATCHLIST_TXT}"
fi

echo
echo "Watchlist JSON: ${WATCHLIST_JSON}"
if [ -f "${WATCHLIST_JSON}" ]; then
  python - <<'PYWL'
import json
from pathlib import Path

path = Path("reports/scanner_agent_watchlist_report.json")

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception as ex:
    print("[WARN] Cannot read watchlist JSON:", ex)
    raise SystemExit

print("Watchlist safe to continue:", payload.get("safe_to_continue"))
print("Watchlist count:", payload.get("watchlist_count"))
print("Watchlist statuses:", payload.get("summary_by_watch_status"))
print("Watchlist decisions:", payload.get("summary_by_decision"))
print("Watchlist blockers:", ", ".join(payload.get("blockers", [])) or "none")
print("Watchlist warnings:", ", ".join(payload.get("warnings", [])) or "none")
PYWL
else
  echo "[WARN] Missing watchlist JSON: ${WATCHLIST_JSON}"
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
echo "5. CHANNEL CONFIG RECOMMENDATIONS"
echo "======================================"

if [ -f "${RECOMMENDATIONS_TXT}" ]; then
  cat "${RECOMMENDATIONS_TXT}"
else
  echo "[WARN] Missing channel config recommendations TXT: ${RECOMMENDATIONS_TXT}"
fi

echo
echo "======================================"
echo "6. QUICK JSON STATUS"
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
print("Duplicate notification blocked:", payload.get("telegram", {}).get("duplicate_notification_blocked"))

blockers = payload.get("blockers", [])
warnings = payload.get("warnings", [])

print("Blockers:", ", ".join(blockers) if blockers else "none")
print("Warnings:", ", ".join(warnings) if warnings else "none")
PY
echo
echo "Telegram audit JSON: ${AUDIT_JSON}"
if [ -f "${AUDIT_JSON}" ]; then
  python - <<'PY2'
import json
from pathlib import Path

path = Path("reports/scanner_agent_telegram_sender_audit_report.json")

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception as ex:
    print("[WARN] Cannot read Telegram sender audit JSON:", ex)
    raise SystemExit

print("Telegram audit status:", payload.get("audit_status"))
print("Telegram audit safety OK:", payload.get("safety_ok"))
print("Telegram audit duplicate blocked:", payload.get("duplicate_delivery_text_blocked"))
print("Telegram audit blockers:", ", ".join(payload.get("blockers", [])) or "none")
print("Telegram audit warnings:", ", ".join(payload.get("warnings", [])) or "none")
PY2
else
  echo "[WARN] Missing Telegram sender audit JSON: ${AUDIT_JSON}"
fi
else
  echo "[WARN] Missing summary JSON: ${SUMMARY_JSON}"
fi

echo
echo "======================================"
echo "7. QUICK CHANNEL QUALITY STATUS"
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
echo "8. QUICK CHANNEL CONFIG RECOMMENDATIONS STATUS"
echo "======================================"

if [ -f "${RECOMMENDATIONS_JSON}" ]; then
  python - <<'PY'
import json
from pathlib import Path

path = Path("reports/telegram_channel_config_recommendations.json")

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception as ex:
    print("[WARN] Cannot read channel config recommendations JSON:", ex)
    raise SystemExit

print("Safe to continue:", payload.get("safe_to_continue"))
print("scanner_real_channels.py modified:", payload.get("scanner_real_channels_modified"))
print("Current real channels:", payload.get("current_real_channels"))
print("Keep:", payload.get("keep"))
print("Watch:", payload.get("watch"))
print("Disable:", payload.get("disable"))

blockers = payload.get("blockers", [])
warnings = payload.get("warnings", [])

print("Blockers:", ", ".join(blockers) if blockers else "none")
print("Warnings:", ", ".join(warnings) if warnings else "none")

recommendations = payload.get("recommendations", [])

if recommendations:
    print()
    print("Config recommendations:")

    for item in recommendations:
        print(
            "- @{username}: final={final} enabled={enabled} "
            "weight={weight} authority={authority} quality={quality}".format(
                username=item.get("username"),
                final=item.get("final_recommendation"),
                enabled=item.get("recommended_enabled"),
                weight=item.get("recommended_weight"),
                authority=item.get("recommended_authority_score"),
                quality=item.get("quality_score"),
            )
        )
PY
else
  echo "[WARN] Missing channel config recommendations JSON: ${RECOMMENDATIONS_JSON}"
fi

echo
echo "======================================"
echo "8A. SAFETY GATE REPORT"
echo "======================================"
python scanner_agent_safety_gate_report.py || echo "[WARN] Safety gate report failed"

if [ -f "${SAFETY_GATE_TXT}" ]; then
  cat "${SAFETY_GATE_TXT}"
else
  echo "[WARN] Missing safety gate TXT: ${SAFETY_GATE_TXT}"
fi

echo
echo "Safety gate JSON: ${SAFETY_GATE_JSON}"
if [ -f "${SAFETY_GATE_JSON}" ]; then
  python - <<'PY3'
import json
from pathlib import Path

path = Path("reports/scanner_agent_safety_gate_report.json")

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception as ex:
    print("[WARN] Cannot read safety gate JSON:", ex)
    raise SystemExit

print("Safety gate status:", payload.get("gate_status"))
print("Safety gate OK:", payload.get("safety_gate_ok"))
print("Review required:", payload.get("review_required"))
print("Safety gate blockers:", ", ".join(payload.get("blockers", [])) or "none")
print("Safety gate warnings:", ", ".join(payload.get("warnings", [])) or "none")
PY3
else
  echo "[WARN] Missing safety gate JSON: ${SAFETY_GATE_JSON}"
fi

echo
echo "======================================"
echo "9. SAFETY RESULT"
echo "======================================"
echo "[OK] This daily runner did not create orders"
echo "[OK] This daily runner did not start trading bot"
echo "[OK] Full pipeline log was saved locally"
echo "[OK] Final pipeline summary was printed for manual review"
echo "[OK] Channel quality summary was printed for manual review"
echo "[OK] Channel config recommendations were printed for manual review"
echo "[OK] Watchlist report was printed for manual review"
echo "[OK] Telegram sending still depends on safety flags"

echo
echo "DONE"
