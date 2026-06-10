#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/root/binance-spot-trading-bot"

CHECK_ONLY="false"
WITH_DOCS="false"
TAG_NAME=""
COMMIT_MESSAGE=""

usage() {
  echo "Usage:"
  echo "  ./safe_status_release.sh --check-only"
  echo "  ./safe_status_release.sh <tag-name> \"<commit message>\""
  echo "  ./safe_status_release.sh --with-docs <tag-name> \"<commit message>\""
  echo
  echo "Examples:"
  echo "  ./safe_status_release.sh --check-only"
  echo "  ./safe_status_release.sh scanner-safe-example-v1 \"Describe safe release\""
  echo "  ./safe_status_release.sh --with-docs scanner-safe-example-v1 \"Describe safe release\""
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --check-only)
      CHECK_ONLY="true"
      shift
      ;;
    --with-docs)
      WITH_DOCS="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [ -z "${TAG_NAME}" ]; then
        TAG_NAME="$1"
      elif [ -z "${COMMIT_MESSAGE}" ]; then
        COMMIT_MESSAGE="$1"
      else
        echo "[ERROR] Unexpected argument: $1"
        usage
        exit 2
      fi
      shift
      ;;
  esac
done

if [ "${CHECK_ONLY}" = "true" ] && [ "${WITH_DOCS}" = "true" ]; then
  echo "[ERROR] --check-only and --with-docs cannot be used together."
  exit 2
fi

if [ "${CHECK_ONLY}" != "true" ]; then
  if [ -z "${TAG_NAME}" ]; then
    echo "[ERROR] Missing tag name."
    usage
    exit 2
  fi

  if [ -z "${COMMIT_MESSAGE}" ]; then
    echo "[ERROR] Missing commit message."
    usage
    exit 2
  fi
fi

cd "${PROJECT_DIR}"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

DOC_TAG_NAME=""

if [ "${WITH_DOCS}" = "true" ]; then
  if [[ "${TAG_NAME}" == scanner-safe-* ]]; then
    DOC_TAG_NAME="scanner-safe-project-status-${TAG_NAME#scanner-safe-}"
  else
    DOC_TAG_NAME="${TAG_NAME}-project-status"
  fi
fi

echo "======================================"
echo "SAFE STATUS RELEASE SNAPSHOT"
echo "======================================"
echo "Project: ${PROJECT_DIR}"
echo "Mode check-only: ${CHECK_ONLY}"
echo "Mode with-docs: ${WITH_DOCS}"

if [ "${CHECK_ONLY}" != "true" ]; then
  echo "Tag: ${TAG_NAME}"
  echo "Commit message: ${COMMIT_MESSAGE}"
fi

if [ "${WITH_DOCS}" = "true" ]; then
  echo "Documentation tag: ${DOC_TAG_NAME}"
fi

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

if [ "${CHECK_ONLY}" != "true" ]; then
  if git tag --list | grep -qx "${TAG_NAME}"; then
    echo "[ERROR] Tag already exists locally: ${TAG_NAME}"
    exit 11
  fi

  if git ls-remote --tags origin "${TAG_NAME}" | grep -q "${TAG_NAME}"; then
    echo "[ERROR] Tag already exists on origin: ${TAG_NAME}"
    exit 12
  fi

  if [ "${WITH_DOCS}" = "true" ]; then
    if git tag --list | grep -qx "${DOC_TAG_NAME}"; then
      echo "[ERROR] Documentation tag already exists locally: ${DOC_TAG_NAME}"
      exit 13
    fi

    if git ls-remote --tags origin "${DOC_TAG_NAME}" | grep -q "${DOC_TAG_NAME}"; then
      echo "[ERROR] Documentation tag already exists on origin: ${DOC_TAG_NAME}"
      exit 14
    fi
  fi
fi

echo
echo "======================================"
echo "2. STATIC SAFETY CHECKS"
echo "======================================"

python -m py_compile \
  config.py \
  credentials.py \
  health_check.py \
  scanner_agent_safety_gate_report.py \
  scanner_agent_risk_filter_backtest.py \
  scanner_agent_scenario_matrix_report.py \
  quick_safe_dashboard.py \
  manual_review_cards.py \
  manager_brief_report.py

bash -n run_daily_scanner_agent_safe.sh
bash -n run_daily_scanner_agent_cron_safe.sh
bash -n safe_status_release.sh

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
echo "6. RISK FILTER BACKTEST CHECK"
echo "======================================"
python scanner_agent_risk_filter_backtest.py

python - <<'PYRFBT'
import json
from pathlib import Path

path = Path("reports/scanner_agent_risk_filter_backtest.json")

if not path.exists():
    raise SystemExit("[ERROR] Missing reports/scanner_agent_risk_filter_backtest.json")

payload = json.loads(path.read_text(encoding="utf-8"))

checks = {
    "analytical_only": payload.get("analytical_only"),
    "orders_enabled": payload.get("orders_enabled"),
    "order_execution_allowed": payload.get("order_execution_allowed"),
    "trading_enabled": payload.get("trading_enabled"),
    "telegram_sending": payload.get("telegram_sending"),
    "safe_to_continue": payload.get("safe_to_continue"),
}

print("Risk filter analytical_only:", checks["analytical_only"])
print("Risk filter orders_enabled:", checks["orders_enabled"])
print("Risk filter order_execution_allowed:", checks["order_execution_allowed"])
print("Risk filter trading_enabled:", checks["trading_enabled"])
print("Risk filter telegram_sending:", checks["telegram_sending"])
print("Risk filter safe_to_continue:", checks["safe_to_continue"])
print("Risk filter summary by bucket:", payload.get("summary_by_bucket"))
print("Risk filter gap summary:", payload.get("gap_summary"))
print("Risk filter synthetic scenarios OK:", payload.get("synthetic_scenarios_ok"))
print("Risk filter synthetic scenario failed count:", payload.get("synthetic_scenario_failed_count"))

if payload.get("synthetic_scenarios_ok") is not True:
    raise SystemExit("[ERROR] Risk filter synthetic scenarios failed")

if checks["analytical_only"] is not True:
    raise SystemExit("[ERROR] Risk filter backtest analytical_only must be True")

for key in [
    "orders_enabled",
    "order_execution_allowed",
    "trading_enabled",
    "telegram_sending",
]:
    if checks[key] is not False:
        raise SystemExit(f"[ERROR] Risk filter backtest unsafe flag: {key}")

if checks["safe_to_continue"] is not True:
    raise SystemExit("[ERROR] Risk filter backtest safe_to_continue must be True")

blockers = payload.get("blockers", [])

if blockers:
    raise SystemExit("[ERROR] Risk filter backtest blockers are present: " + ", ".join(str(item) for item in blockers))

print("[OK] Risk filter backtest allows release")
PYRFBT

echo
echo "======================================"
echo "6B. SCENARIO MATRIX REPORT CHECK"
echo "======================================"
python scanner_agent_scenario_matrix_report.py

python - <<'PYSCENARIO'
import json
from pathlib import Path

path = Path("reports/scanner_agent_scenario_matrix_report.json")

if not path.exists():
    raise SystemExit("[ERROR] Missing reports/scanner_agent_scenario_matrix_report.json")

payload = json.loads(path.read_text(encoding="utf-8"))

print("Scenario matrix safe to continue:", payload.get("safe_to_continue"))
print("Scenario matrix synthetic OK:", payload.get("synthetic_scenarios_ok"))
print("Scenario matrix count:", payload.get("scenario_count"))
print("Scenario matrix failed count:", payload.get("failed_count"))
print("Scenario matrix unsafe runtime count:", payload.get("unsafe_runtime_count"))
print("Scenario matrix summary by result:", payload.get("summary_by_result"))

if payload.get("safe_to_continue") is not True:
    raise SystemExit("[ERROR] Scenario matrix report is not safe to continue")

if payload.get("synthetic_scenarios_ok") is not True:
    raise SystemExit("[ERROR] Scenario matrix synthetic scenarios failed")

if payload.get("failed_count") != 0:
    raise SystemExit("[ERROR] Scenario matrix failed scenarios are present")

if payload.get("unsafe_runtime_count") != 0:
    raise SystemExit("[ERROR] Scenario matrix unsafe runtime rows are present")

for key in [
    "orders_enabled",
    "order_execution_allowed",
    "trading_enabled",
    "telegram_sending",
    "binance_private_api_used",
]:
    if payload.get(key) is not False:
        raise SystemExit(f"[ERROR] Scenario matrix unsafe flag: {key}")

print("[OK] Scenario matrix report allows release")
PYSCENARIO

echo
echo "======================================"
echo "6C. QUICK SAFE DASHBOARD CHECK"
echo "======================================"
python quick_safe_dashboard.py

python - <<'PYDASH'
import json
from pathlib import Path

path = Path("reports/quick_safe_dashboard.json")

if not path.exists():
    raise SystemExit("[ERROR] Missing reports/quick_safe_dashboard.json")

payload = json.loads(path.read_text(encoding="utf-8"))
dashboard = payload.get("dashboard", {})

if not isinstance(dashboard, dict):
    dashboard = {}

print("Quick dashboard safe to continue:", payload.get("safe_to_continue"))
print("Quick dashboard pipeline status:", dashboard.get("pipeline_status"))
print("Quick dashboard safety gate:", dashboard.get("safety_gate_status"))
print("Quick dashboard scenario matrix failed:", dashboard.get("scenario_matrix_failed"))
print("Quick dashboard Telegram sent:", dashboard.get("telegram_message_sent"))
print("Quick dashboard Telegram API used:", dashboard.get("telegram_api_used"))
print("Quick dashboard blocked risk count:", dashboard.get("blocked_risk_count"))
print("Quick dashboard watchlist count:", dashboard.get("watchlist_count"))

cockpit = dashboard.get("decision_cockpit", {})

if not isinstance(cockpit, dict):
    raise SystemExit("[ERROR] Quick dashboard decision cockpit is missing")

print("Quick dashboard cockpit state:", cockpit.get("state"))
print("Quick dashboard cockpit action allowed:", cockpit.get("action_allowed"))

if cockpit.get("action_allowed") is not False:
    raise SystemExit("[ERROR] Quick dashboard cockpit allowed unsafe action")

if cockpit.get("allowed_action") != "manual_review_only":
    raise SystemExit("[ERROR] Quick dashboard cockpit allowed_action is unexpected")

if payload.get("safe_to_continue") is not True:
    raise SystemExit("[ERROR] Quick dashboard is not safe to continue")

for key in [
    "orders_enabled",
    "order_execution_allowed",
    "trading_enabled",
    "telegram_sending",
    "binance_private_api_used",
]:
    if payload.get(key) is not False:
        raise SystemExit(f"[ERROR] Quick dashboard unsafe flag: {key}")

print("[OK] Quick safe dashboard allows release")
PYDASH

echo
echo "======================================"
echo "6D. MANUAL REVIEW CARDS CHECK"
echo "======================================"
python manual_review_cards.py

python - <<'PYCARDS'
import json
from pathlib import Path

path = Path("reports/manual_review_cards.json")

if not path.exists():
    raise SystemExit("[ERROR] Missing reports/manual_review_cards.json")

payload = json.loads(path.read_text(encoding="utf-8"))

print("Manual review cards safe to continue:", payload.get("safe_to_continue"))
print("Manual review cards count:", payload.get("cards_count"))
print("Manual review cards status summary:", payload.get("summary_by_status"))
print("Manual review cards safe decision summary:", payload.get("summary_by_safe_decision"))
print("Manual review cards quick dashboard state:", payload.get("quick_dashboard_state"))

if payload.get("safe_to_continue") is not True:
    raise SystemExit("[ERROR] Manual review cards are not safe to continue")

for key in [
    "analytical_only",
]:
    if payload.get(key) is not True:
        raise SystemExit(f"[ERROR] Manual review cards expected True flag failed: {key}")

for key in [
    "orders_enabled",
    "order_execution_allowed",
    "trading_enabled",
    "telegram_sending",
    "binance_private_api_used",
]:
    if payload.get(key) is not False:
        raise SystemExit(f"[ERROR] Manual review cards unsafe flag: {key}")

cards = payload.get("cards", [])

if not isinstance(cards, list):
    raise SystemExit("[ERROR] Manual review cards payload cards must be a list")

for card in cards:
    if not isinstance(card, dict):
        raise SystemExit("[ERROR] Manual review card is not a dict")

    if card.get("forbidden_action") != "NO_ORDERS_NO_LIVE_TRADING_NO_AUTO_TELEGRAM":
        raise SystemExit("[ERROR] Manual review card forbidden action is unsafe or missing")

    if card.get("safe_decision") not in {"DO_NOT_ENTER", "WATCH_ONLY", "MANUAL_REVIEW_ONLY"}:
        raise SystemExit("[ERROR] Manual review card safe decision is unexpected")

    if not isinstance(card.get("human_checklist"), list):
        raise SystemExit("[ERROR] Manual review card human checklist must be a list")

blockers = payload.get("blockers", [])

if blockers:
    raise SystemExit("[ERROR] Manual review cards blockers are present: " + ", ".join(str(item) for item in blockers))

print("[OK] Manual review cards allow release")
PYCARDS

echo
echo "======================================"
echo "6E. MANAGER BRIEF REPORT CHECK"
echo "======================================"
python manager_brief_report.py

python - <<'PYBRIEF'
import json
from pathlib import Path

path = Path("reports/manager_brief_report.json")

if not path.exists():
    raise SystemExit("[ERROR] Missing reports/manager_brief_report.json")

payload = json.loads(path.read_text(encoding="utf-8"))

print("Manager brief safe to continue:", payload.get("safe_to_continue"))
print("Manager brief cards count:", payload.get("cards_count"))
print("Manager brief all blocked:", payload.get("all_current_pairs_blocked"))
print("Manager brief summary:", payload.get("summary"))

if payload.get("safe_to_continue") is not True:
    raise SystemExit("[ERROR] Manager brief report is not safe to continue")

for key in [
    "analytical_only",
]:
    if payload.get(key) is not True:
        raise SystemExit(f"[ERROR] Manager brief expected True flag failed: {key}")

for key in [
    "orders_enabled",
    "order_execution_allowed",
    "trading_enabled",
    "telegram_sending",
    "binance_private_api_used",
]:
    if payload.get(key) is not False:
        raise SystemExit(f"[ERROR] Manager brief unsafe flag: {key}")

items = payload.get("brief_items", [])

if not isinstance(items, list):
    raise SystemExit("[ERROR] Manager brief items must be a list")

for item in items:
    if not isinstance(item, dict):
        raise SystemExit("[ERROR] Manager brief item is not a dict")

    if item.get("forbidden_action") != "NO_ORDERS_NO_LIVE_TRADING_NO_AUTO_TELEGRAM":
        raise SystemExit("[ERROR] Manager brief forbidden action is unsafe or missing")

    if item.get("safe_decision") not in {"DO_NOT_ENTER", "WATCH_ONLY", "MANUAL_REVIEW_ONLY"}:
        raise SystemExit("[ERROR] Manager brief safe decision is unexpected")

blockers = payload.get("blockers", [])

if blockers:
    raise SystemExit("[ERROR] Manager brief blockers are present: " + ", ".join(str(item) for item in blockers))

print("[OK] Manager brief report allows release")
PYBRIEF

echo
echo "======================================"
echo "7. REPORT SNAPSHOT"
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
echo "--- scanner_agent_risk_filter_backtest.txt ---"
cat reports/scanner_agent_risk_filter_backtest.txt

echo
echo "--- scanner_agent_scenario_matrix_report.txt ---"
cat reports/scanner_agent_scenario_matrix_report.txt

echo
echo "--- quick_safe_dashboard.txt ---"
cat reports/quick_safe_dashboard.txt

echo
echo "--- manual_review_cards.txt ---"
cat reports/manual_review_cards.txt

echo
echo "--- manager_brief_report.txt ---"
cat reports/manager_brief_report.txt

if [ "${CHECK_ONLY}" = "true" ]; then
  echo
  echo "======================================"
  echo "8. CHECK-ONLY RESULT"
  echo "======================================"
  git status
  echo
  echo "[OK] Check-only mode completed."
  echo "[OK] No commit was created."
  echo "[OK] Nothing was pushed."
  echo "[OK] No tag was created."
  echo "Finished at: $(date -Iseconds)"
  exit 0
fi

echo
echo "======================================"
echo "8. GIT COMMIT / PUSH / TAG"
echo "======================================"

SHORT_STATUS="$(git status --short)"
echo "${SHORT_STATUS}"

if [ -n "${SHORT_STATUS}" ]; then
  echo "[INFO] Changes detected. Preparing commit."

  if echo "${SHORT_STATUS}" | grep -E '(^.. \.env$|\.session$|data/.*\.db$|reports/.*\.(json|txt|log)$|application\.log$|execute-times\.tmp$|__pycache__|\.pyc$)' ; then
    echo "[ERROR] Refusing to commit secrets, sessions, databases, runtime reports, logs, temp files, or cache files."
    exit 30
  fi

  git add .
  git commit -m "${COMMIT_MESSAGE}"
  git push origin main
else
  echo "[OK] No file changes detected. No commit needed."
fi

CURRENT_COMMIT="$(git rev-parse --short HEAD)"
CHANGED_FILES="$(git diff-tree --no-commit-id --name-only -r HEAD || true)"

echo "Current commit: ${CURRENT_COMMIT}"

git tag -a "${TAG_NAME}" -m "${COMMIT_MESSAGE}"
git push origin "${TAG_NAME}"

if [ "${WITH_DOCS}" = "true" ]; then
  echo
  echo "======================================"
  echo "9. AUTO DOCUMENTATION UPDATE"
  echo "======================================"
  echo "Documentation tag: ${DOC_TAG_NAME}"

  RELEASE_TAG="${TAG_NAME}" \
  RELEASE_COMMIT="${CURRENT_COMMIT}" \
  DOC_TAG="${DOC_TAG_NAME}" \
  RELEASE_MESSAGE="${COMMIT_MESSAGE}" \
  CHANGED_FILES="${CHANGED_FILES}" \
  python - <<'PY'
import json
import os
import re
from pathlib import Path

release_tag = os.environ["RELEASE_TAG"]
release_commit = os.environ["RELEASE_COMMIT"]
doc_tag = os.environ["DOC_TAG"]
release_message = os.environ["RELEASE_MESSAGE"]
changed_files_raw = os.environ.get("CHANGED_FILES", "").strip()

changed_files = [line.strip() for line in changed_files_raw.splitlines() if line.strip()]
if not changed_files:
    changed_files = ["no file changes in release commit"]

project_status = Path("PROJECT_STATUS.md")
safe_releases = Path("SAFE_RELEASES.md")
gate_json_path = Path("reports/scanner_agent_safety_gate_report.json")

status_text = project_status.read_text(encoding="utf-8")
release_text = safe_releases.read_text(encoding="utf-8")

status_text = re.sub(
    r"(Current stable tag:\n\n)([^\n]+)",
    rf"\g<1>{release_tag}",
    status_text,
    count=1,
)

status_text = re.sub(
    r"(Stable commit:\n\n)([0-9a-f]+)",
    rf"\g<1>{release_commit}",
    status_text,
    count=1,
)

helper_line = "- safe_status_release.sh supports --check-only and --with-docs conveyor mode for safer one-command project releases."

if helper_line not in status_text:
    marker = "- safe_status_release.sh can run a safe snapshot, verify safety gate, commit, push, and create an explicit tag."
    if marker in status_text:
        status_text = status_text.replace(marker, marker + "\n" + helper_line)
    else:
        status_text = status_text.rstrip() + "\n" + helper_line + "\n"

project_status.write_text(status_text, encoding="utf-8")

gate = {}
if gate_json_path.exists():
    gate = json.loads(gate_json_path.read_text(encoding="utf-8"))

dangerous = gate.get("dangerous_flags", {}) if isinstance(gate, dict) else {}

changed_file_lines = [f"- {name}" for name in changed_files]

section_lines = [
    "",
    "---",
    "",
    f"### {release_tag}",
    "",
    "Purpose:",
    "",
    release_message,
    "",
    "Release mode:",
    "",
    "Created through safe_status_release.sh --with-docs.",
    "",
    "What was changed:",
    "",
    *changed_file_lines,
    "",
    "Safety result:",
    "",
    f"Gate status: {gate.get('gate_status', 'unknown')}",
    f"Safety gate OK: {gate.get('safety_gate_ok', 'unknown')}",
    f"Review required: {gate.get('review_required', 'unknown')}",
    f"Telegram message sent: {gate.get('telegram_message_sent', False)}",
    f"Orders enabled: {dangerous.get('orders_enabled', False)}",
    f"Trading enabled: {dangerous.get('trading_enabled', False)}",
    f"Binance API used: {dangerous.get('binance_api_used', False)}",
    f"Binance orders created: {dangerous.get('binance_orders_created', False)}",
    "",
    "Validation:",
    "",
    "1. cd /root/binance-spot-trading-bot",
    "2. source .venv/bin/activate",
    "3. ./safe_status_release.sh --check-only",
    "",
    "Stable point:",
    "",
    f"tag: {release_tag}",
    f"commit: {release_commit}",
    "branch: main",
    "",
    "---",
    "",
    "## Recommended next stable status tag",
    "",
    "After committing this documentation status update, create a new tag:",
    "",
    doc_tag,
    "",
    "Commands:",
    "",
    f"git tag -a {doc_tag} -m \"Stable project status after {release_tag}\"",
    f"git push origin {doc_tag}",
    "",
]

if f"### {release_tag}" not in release_text:
    release_text = release_text.rstrip() + "\n" + "\n".join(section_lines) + "\n"

safe_releases.write_text(release_text, encoding="utf-8")
PY

  echo "=== DOC REFERENCES ==="
  grep -n "${TAG_NAME}\|${DOC_TAG_NAME}\|${CURRENT_COMMIT}\|safe_status_release.sh\|safe_manual_review" PROJECT_STATUS.md SAFE_RELEASES.md || true

  DOC_STATUS="$(git status --short)"
  echo "${DOC_STATUS}"

  if [ -n "${DOC_STATUS}" ]; then
    if echo "${DOC_STATUS}" | grep -E '(^.. \.env$|\.session$|data/.*\.db$|reports/.*\.(json|txt|log)$|application\.log$|execute-times\.tmp$|__pycache__|\.pyc$)' ; then
      echo "[ERROR] Refusing to commit unsafe files during documentation update."
      exit 31
    fi

    git add PROJECT_STATUS.md SAFE_RELEASES.md
    git commit -m "Update project status after ${TAG_NAME}"
    git push origin main
  else
    echo "[OK] Documentation already up to date."
  fi

  git tag -a "${DOC_TAG_NAME}" -m "Stable project status after ${TAG_NAME}"
  git push origin "${DOC_TAG_NAME}"

  CURRENT_COMMIT="$(git rev-parse --short HEAD)"
fi

echo
echo "======================================"
echo "10. FINAL STATE"
echo "======================================"
git status
git log --oneline -5

echo
echo "Created tags:"
git tag --list | grep -F "${TAG_NAME}" || true

if [ "${WITH_DOCS}" = "true" ]; then
  git tag --list | grep -F "${DOC_TAG_NAME}" || true
fi

echo
echo "[OK] Safe status release completed."
echo "Tag: ${TAG_NAME}"

if [ "${WITH_DOCS}" = "true" ]; then
  echo "Documentation tag: ${DOC_TAG_NAME}"
fi

echo "Final commit: ${CURRENT_COMMIT}"
echo "Finished at: $(date -Iseconds)"
