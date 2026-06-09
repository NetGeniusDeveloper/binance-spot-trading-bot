#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/root/binance-spot-trading-bot"

TAG_NAME="${1:-}"
COMMIT_MESSAGE="${2:-}"

if [ -z "${TAG_NAME}" ]; then
  echo "[ERROR] Missing tag name."
  echo "Usage: ./safe_status_release.sh <tag-name> \"<commit message>\""
  exit 2
fi

if [ -z "${COMMIT_MESSAGE}" ]; then
  echo "[ERROR] Missing commit message."
  echo "Usage: ./safe_status_release.sh <tag-name> \"<commit message>\""
  exit 2
fi

cd "${PROJECT_DIR}"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "======================================"
echo "SAFE STATUS RELEASE SNAPSHOT"
echo "======================================"
echo "Project: ${PROJECT_DIR}"
echo "Tag: ${TAG_NAME}"
echo "Commit message: ${COMMIT_MESSAGE}"
echo "Started at: $(date -Iseconds)"
echo

echo "======================================"
echo "1. GIT STATE"
echo "======================================"
git status
CURRENT_BRANCH="$(git branch --show-current)"
echo "Current branch: ${CURRENT_BRANCH}"

if [ "${CURRENT_BRANCH}" != "main" ]; then
  echo "[ERROR] Releases are allowed only from main branch."
  exit 10
fi

git log --oneline -5

echo
echo "Recent safe tags:"
git tag --list | grep -E 'scanner-safe-' | tail -n 20 || true

if git tag --list | grep -qx "${TAG_NAME}"; then
  echo "[ERROR] Tag already exists locally: ${TAG_NAME}"
  exit 11
fi

if git ls-remote --tags origin "${TAG_NAME}" | grep -q "${TAG_NAME}"; then
  echo "[ERROR] Tag already exists on origin: ${TAG_NAME}"
  exit 12
fi

echo
echo "======================================"
echo "2. STATIC SAFETY CHECKS"
echo "======================================"

python -m py_compile \
  config.py \
  credentials.py \
  health_check.py \
  scanner_agent_safety_gate_report.py

bash -n run_daily_scanner_agent_safe.sh
bash -n run_daily_scanner_agent_cron_safe.sh

python - <<'PY'
import config

checks = {
    "DRY_RUN": getattr(config, "DRY_RUN", None),
    "SEND_TELEGRAM_MESSAGE": getattr(config, "SEND_TELEGRAM_MESSAGE", None),
    "WALLET_USAGE_PERCENT": getattr(config, "WALLET_USAGE_PERCENT", None),
}

print("DRY_RUN:", checks["DRY_RUN"])
print("SEND_TELEGRAM_MESSAGE:", checks["SEND_TELEGRAM_MESSAGE"])
print("WALLET_USAGE_PERCENT:", checks["WALLET_USAGE_PERCENT"])

if checks["DRY_RUN"] is not True:
    raise SystemExit("[ERROR] DRY_RUN must be True")

if checks["SEND_TELEGRAM_MESSAGE"] is not False:
    raise SystemExit("[ERROR] SEND_TELEGRAM_MESSAGE must be False")

try:
    wallet_usage = float(checks["WALLET_USAGE_PERCENT"])
except Exception:
    raise SystemExit("[ERROR] WALLET_USAGE_PERCENT must be numeric")

if wallet_usage != 0.0:
    raise SystemExit("[ERROR] WALLET_USAGE_PERCENT must be 0.0")

print("[OK] Static config safety checks passed")
PY

echo
echo "======================================"
echo "3. HEALTH CHECK"
echo "======================================"
python health_check.py

echo
echo "======================================"
echo "4. SAFE CRON SNAPSHOT"
echo "======================================"
./run_daily_scanner_agent_cron_safe.sh

echo
echo "======================================"
echo "5. SAFETY GATE JSON CHECK"
echo "======================================"

python - <<'PY'
import json
from pathlib import Path

path = Path("reports/scanner_agent_safety_gate_report.json")

if not path.exists():
    raise SystemExit("[ERROR] Missing reports/scanner_agent_safety_gate_report.json")

payload = json.loads(path.read_text(encoding="utf-8"))

gate_status = str(payload.get("gate_status", "unknown"))
safety_gate_ok = bool(payload.get("safety_gate_ok", False))
review_required = bool(payload.get("review_required", False))
blockers = payload.get("blockers", [])
warnings = payload.get("warnings", [])
dangerous = payload.get("dangerous_flags", {})

allowed_statuses = {
    "safe",
    "duplicate_blocked",
    "safe_manual_review",
}

print("Gate status:", gate_status)
print("Safety gate OK:", safety_gate_ok)
print("Review required:", review_required)
print("Blockers:", ", ".join(blockers) if blockers else "none")
print("Warnings:", ", ".join(warnings) if warnings else "none")
print("Dangerous flags:", dangerous)

if gate_status not in allowed_statuses:
    raise SystemExit(f"[ERROR] Gate status is not allowed for release: {gate_status}")

if not safety_gate_ok:
    raise SystemExit("[ERROR] Safety gate OK is False")

if blockers:
    raise SystemExit("[ERROR] Safety blockers are present")

for key in [
    "orders_enabled",
    "trading_enabled",
    "binance_api_used",
    "binance_orders_created",
]:
    if bool(dangerous.get(key)):
        raise SystemExit(f"[ERROR] Dangerous flag is enabled: {key}")

print("[OK] Safety gate allows release")
PY

echo
echo "======================================"
echo "6. REPORT SNAPSHOT"
echo "======================================"

echo "--- scanner_agent_pipeline_summary.txt ---"
cat reports/scanner_agent_pipeline_summary.txt

echo
echo "--- scanner_agent_safety_gate_report.txt ---"
cat reports/scanner_agent_safety_gate_report.txt

echo
echo "--- scanner_agent_blocked_risk_report.txt ---"
cat reports/scanner_agent_blocked_risk_report.txt

echo
echo "======================================"
echo "7. GIT COMMIT / PUSH / TAG"
echo "======================================"

git status --short

if [ -n "$(git status --short)" ]; then
  echo "[INFO] Changes detected. Preparing commit."

  if git status --short | grep -E '(^.. \.env$|\.session$|data/.*\.db$|reports/.*\.json$|reports/.*\.txt$|__pycache__|\.pyc$)' ; then
    echo "[ERROR] Refusing to commit secrets, sessions, databases, runtime reports, or cache files."
    exit 30
  fi

  git add .
  git commit -m "${COMMIT_MESSAGE}"
  git push origin main
else
  echo "[OK] No file changes detected. No commit needed."
fi

CURRENT_COMMIT="$(git rev-parse --short HEAD)"

echo "Current commit: ${CURRENT_COMMIT}"

git tag -a "${TAG_NAME}" -m "${COMMIT_MESSAGE}"
git push origin "${TAG_NAME}"

echo
echo "======================================"
echo "8. FINAL STATE"
echo "======================================"
git status
git log --oneline -5
git tag --list | grep -E "${TAG_NAME}" || true

echo
echo "[OK] Safe status release completed."
echo "Tag: ${TAG_NAME}"
echo "Commit: ${CURRENT_COMMIT}"
echo "Finished at: $(date -Iseconds)"
