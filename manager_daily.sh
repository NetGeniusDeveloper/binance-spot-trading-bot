#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/root/binance-spot-trading-bot"
cd "$PROJECT_DIR"

DASHBOARD_LOG="${TMPDIR:-/tmp}/manager_daily_quick_dashboard.out"

line() {
  echo "======================================"
}

line
echo " MANAGER DAILY / БЕЗОПАСНАЯ СВОДКА"
line
echo "Проект: $PROJECT_DIR"
echo "Режим: analytical only / no orders / no live trading"
echo

echo "GIT"
echo "----"
branch="$(git branch --show-current 2>/dev/null || echo unknown)"
if git diff --quiet && git diff --cached --quiet; then
  git_state="clean"
else
  git_state="dirty"
fi
echo "Branch: $branch"
echo "Git: $git_state"
echo

echo "ОБНОВЛЯЕМ QUICK SAFE DASHBOARD"
echo "------------------------------"
python3 quick_safe_dashboard.py > "$DASHBOARD_LOG"
echo "[OK] quick_safe_dashboard.py выполнен безопасно"
echo

echo "КОРОТКИЙ СТАТУС БЕЗОПАСНОСТИ"
echo "----------------------------"
if [ -f reports/quick_safe_dashboard.txt ]; then
  grep -E "^(State:|Action allowed:|Status:|Gate status:|Safety gate OK:|Review required:|Telegram send enabled:|Telegram manual confirm:|Scanner Telegram send enabled:|Scanner Telegram manual confirm:|Telegram message sent:|Telegram API used:|Orders enabled:|Order execution allowed:|Trading enabled:|Telegram sending:|Binance private API used:|Safe to continue:|Blockers:|Warnings:)" reports/quick_safe_dashboard.txt || true
else
  echo "[WARN] reports/quick_safe_dashboard.txt не найден"
fi
echo

echo "МЕНЕДЖЕРСКАЯ СВОДКА"
echo "-------------------"
python3 quick_safe_dashboard.py --manager
echo

echo "БЕЗОПАСНОСТЬ"
echo "------------"
echo "Этот скрипт не создаёт ордера."
echo "Этот скрипт не включает live trading."
echo "Этот скрипт не вызывает Binance private API."
echo "Этот скрипт не отправляет Telegram-сообщения."
echo "Менеджерская сводка — только ручной аналитический отчёт."
