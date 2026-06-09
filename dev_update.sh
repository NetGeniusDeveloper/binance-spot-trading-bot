#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/root/binance-spot-trading-bot"

usage() {
  echo "Usage:"
  echo "  ./dev_update.sh <tag-name> \"<commit message>\" -- <patch command>"
  echo
  echo "Examples:"
  echo "  ./dev_update.sh scanner-safe-example-v1 \"Describe update\" -- bash patch_example.sh"
  echo "  ./dev_update.sh scanner-safe-example-v1 \"Describe update\" -- python patch_example.py"
  echo
  echo "What it does:"
  echo "  1. verifies clean Git state"
  echo "  2. runs ./safe_status_release.sh --check-only"
  echo "  3. runs the patch command after --"
  echo "  4. shows changed files and diff summary"
  echo "  5. runs ./safe_status_release.sh --with-docs <tag> <message>"
}

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  usage
  exit 0
fi

TAG_NAME="${1:-}"
COMMIT_MESSAGE="${2:-}"

if [ -z "${TAG_NAME}" ] || [ -z "${COMMIT_MESSAGE}" ]; then
  echo "[ERROR] Missing tag name or commit message."
  usage
  exit 2
fi

shift 2

if [ "${1:-}" != "--" ]; then
  echo "[ERROR] Missing -- before patch command."
  usage
  exit 2
fi

shift

if [ "$#" -eq 0 ]; then
  echo "[ERROR] Missing patch command after --."
  usage
  exit 2
fi

cd "${PROJECT_DIR}"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

echo "======================================"
echo "DEV UPDATE CONVEYOR"
echo "======================================"
echo "Project: ${PROJECT_DIR}"
echo "Tag: ${TAG_NAME}"
echo "Commit message: ${COMMIT_MESSAGE}"
echo "Patch command: $*"
echo "Started at: $(date -Iseconds)"
echo

echo "======================================"
echo "1. PREFLIGHT GIT STATE"
echo "======================================"
git status
CURRENT_BRANCH="$(git branch --show-current)"
echo "Current branch: ${CURRENT_BRANCH}"

if [ "${CURRENT_BRANCH}" != "main" ]; then
  echo "[ERROR] dev_update.sh is allowed only on main branch."
  exit 10
fi

if [ -n "$(git status --short)" ]; then
  echo "[ERROR] Working tree must be clean before dev update."
  echo "[INFO] Commit, stash, or restore current changes first."
  exit 11
fi

if [ ! -x "./safe_status_release.sh" ]; then
  echo "[ERROR] Missing executable ./safe_status_release.sh"
  exit 12
fi

echo
echo "======================================"
echo "2. BASELINE SAFE CHECK"
echo "======================================"
./safe_status_release.sh --check-only

echo
echo "======================================"
echo "3. RUN PATCH COMMAND"
echo "======================================"
"$@"

echo
echo "======================================"
echo "4. POST-PATCH DIFF SUMMARY"
echo "======================================"
git status
echo
echo "Changed files:"
git diff --name-only || true

if [ -z "$(git status --short)" ]; then
  echo "[ERROR] Patch command completed, but no file changes were detected."
  echo "[INFO] Nothing to release."
  exit 20
fi

SHORT_STATUS="$(git status --short)"

if echo "${SHORT_STATUS}" | grep -E '(^.. \.env$|\.session$|data/.*\.db$|reports/.*\.(json|txt|log)$|application\.log$|execute-times\.tmp$|__pycache__|\.pyc$)' ; then
  echo "[ERROR] Patch produced unsafe files for commit."
  echo "[INFO] Refusing to continue."
  exit 21
fi

echo
echo "Diff stat:"
git diff --stat || true

echo
echo "======================================"
echo "5. SAFE RELEASE WITH AUTO DOCS"
echo "======================================"
./safe_status_release.sh --with-docs "${TAG_NAME}" "${COMMIT_MESSAGE}"

echo
echo "======================================"
echo "6. FINAL DEV UPDATE STATE"
echo "======================================"
git status
git log --oneline -5

echo
echo "[OK] dev_update.sh completed."
echo "Tag: ${TAG_NAME}"
echo "Finished at: $(date -Iseconds)"
