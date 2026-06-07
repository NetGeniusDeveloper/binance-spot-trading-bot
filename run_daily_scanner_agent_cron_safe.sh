#!/usr/bin/env bash
set -u

PROJECT_DIR="/root/binance-spot-trading-bot"
LOG_DIR="${PROJECT_DIR}/reports"
CRON_LOG="${LOG_DIR}/daily_scanner_agent_cron_safe.log"
SAFETY_GATE_JSON="${LOG_DIR}/scanner_agent_safety_gate_report.json"

mkdir -p "${LOG_DIR}"

{
  echo "======================================"
  echo "DAILY SCANNER AGENT CRON SAFE WRAPPER"
  echo "======================================"
  echo "Started at: $(date -Iseconds)"
  echo "Project dir: ${PROJECT_DIR}"
  echo "Mode: analytical only"
  echo "Orders: disabled"
  echo "Trading: disabled"
  echo "Binance orders: disabled"
  echo "Telegram sending: controlled by safety flags"
  echo

  cd "${PROJECT_DIR}"

  if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "[OK] Virtual environment activated"
  else
    echo "[WARN] .venv directory not found"
  fi

  echo
  echo "======================================"
  echo "1. GIT STATUS SNAPSHOT"
  echo "======================================"
  git status --short || echo "[WARN] Cannot read git status"
  git log --oneline -3 || echo "[WARN] Cannot read git log"

  echo
  echo "======================================"
  echo "2. DAILY SAFE PIPELINE RUN"
  echo "======================================"

  if ./run_daily_scanner_agent_safe.sh; then
    echo "[OK] Daily safe scanner pipeline finished"
  else
    PIPELINE_EXIT_CODE="$?"
    echo "[ERROR] Daily safe scanner pipeline failed with exit code: ${PIPELINE_EXIT_CODE}"
    echo "Finished at: $(date -Iseconds)"
    exit "${PIPELINE_EXIT_CODE}"
  fi

  echo
  echo "======================================"
  echo "3. SAFETY GATE CHECK"
  echo "======================================"

  if [ ! -f "${SAFETY_GATE_JSON}" ]; then
    echo "[ERROR] Missing safety gate JSON: ${SAFETY_GATE_JSON}"
    echo "Finished at: $(date -Iseconds)"
    exit 20
  fi

  python - <<'PY'
import json
from pathlib import Path

path = Path("reports/scanner_agent_safety_gate_report.json")

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception as ex:
    print("[ERROR] Cannot read safety gate JSON:", ex)
    raise SystemExit(21)

gate_status = str(payload.get("gate_status", "unknown"))
safety_gate_ok = bool(payload.get("safety_gate_ok", False))
review_required = bool(payload.get("review_required", False))
blockers = payload.get("blockers", [])
warnings = payload.get("warnings", [])

print("Safety gate status:", gate_status)
print("Safety gate OK:", safety_gate_ok)
print("Review required:", review_required)
print("Blockers:", ", ".join(blockers) if blockers else "none")
print("Warnings:", ", ".join(warnings) if warnings else "none")

safe_statuses = {
    "safe",
    "duplicate_blocked",
}

review_statuses = {
    "review_required",
}

if gate_status in safe_statuses and safety_gate_ok:
    print("[OK] Safety gate passed")
    raise SystemExit(0)

if gate_status in review_statuses and review_required:
    print("[WARN] Safety gate requires manual review, but no dangerous action was executed")
    raise SystemExit(0)

print("[ERROR] Safety gate did not pass")
raise SystemExit(22)
PY

  SAFETY_EXIT_CODE="$?"

  echo
  echo "======================================"
  echo "4. FINAL CRON WRAPPER RESULT"
  echo "======================================"

  if [ "${SAFETY_EXIT_CODE}" -eq 0 ]; then
    echo "[OK] Cron safe wrapper completed successfully"
    echo "[OK] No orders were created"
    echo "[OK] Trading bot was not started"
    echo "[OK] Binance orders stayed disabled"
  else
    echo "[ERROR] Cron safe wrapper stopped because safety gate did not pass"
    echo "Finished at: $(date -Iseconds)"
    exit "${SAFETY_EXIT_CODE}"
  fi

  echo "Finished at: $(date -Iseconds)"
  echo
  echo "DONE"
} >> "${CRON_LOG}" 2>&1
