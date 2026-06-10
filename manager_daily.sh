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

echo
echo "ЧТО ДЕЛАТЬ ДАЛЬШЕ"
echo "-----------------"

dashboard_file="reports/quick_safe_dashboard.txt"

get_report_value() {
  local key="$1"
  local file="$2"

  if [ ! -f "$file" ]; then
    echo "unknown"
    return
  fi

  grep -m1 "^${key}:" "$file" | cut -d':' -f2- | sed 's/^ *//; s/ *$//' || echo "unknown"
}

dashboard_state="$(get_report_value "State" "$dashboard_file")"
pipeline_status="$(get_report_value "Status" "$dashboard_file")"
action_allowed="$(get_report_value "Action allowed" "$dashboard_file")"
safe_to_continue="$(get_report_value "Safe to continue" "$dashboard_file")"

echo "Состояние: ${dashboard_state}"
echo "Pipeline: ${pipeline_status}"
echo "Action allowed: ${action_allowed}"
echo "Safe to continue: ${safe_to_continue}"
echo

case "$dashboard_state" in
  no_decisions)
    echo "Рекомендация: новых аналитических решений нет."
    echo "Действие: не входить в рынок, не создавать ордера."
    echo "Можно: повторить безопасный сбор данных позже или открыть отчёты."
    echo "Команды:"
    echo "  ./run_daily_scanner_agent_safe.sh"
    echo "  ./manager_daily.sh"
    ;;
  all_decisions_blocked)
    echo "Рекомендация: все текущие решения заблокированы."
    echo "Действие: ничего не покупать, открыть отчёты и причины блокировки."
    echo "Команды:"
    echo "  cat reports/manager_brief_report.txt"
    echo "  cat reports/manual_review_cards.txt"
    echo "  cat reports/scanner_agent_risk_filter_backtest.txt"
    ;;
  watchlist_only)
    echo "Рекомендация: есть пары только для наблюдения."
    echo "Действие: не входить, ждать подтверждений рынка и повторной проверки."
    echo "Команды:"
    echo "  cat reports/manual_review_cards.txt"
    echo "  ./run_daily_scanner_agent_safe.sh"
    ;;
  manual_review_required|safe_manual_review)
    echo "Рекомендация: требуется ручная проверка."
    echo "Действие: открыть карточки и отчёты, но не создавать ордера."
    echo "Команды:"
    echo "  cat reports/manual_review_cards.txt"
    echo "  cat reports/manager_brief_report.txt"
    ;;
  entry_allowed_analytical_only)
    echo "Рекомендация: аналитический кандидат найден, но это НЕ разрешение на сделку."
    echo "Действие: только ручной анализ, backtest и отдельный аудит перед автоматизацией."
    echo "Команды:"
    echo "  cat reports/manager_brief_report.txt"
    echo "  cat reports/scanner_agent_scenario_matrix_report.txt"
    ;;
  *)
    echo "Рекомендация: состояние не распознано или отчёт неполный."
    echo "Действие: не входить в рынок, проверить отчёты вручную."
    echo "Команды:"
    echo "  cat reports/quick_safe_dashboard.txt"
    echo "  ./safe_status_release.sh --check-only"
    ;;
esac

echo
echo "БУДУЩАЯ АВТОМАТИЗАЦИЯ"
echo "---------------------"
echo "Этот блок готовит проект к будущей цепочке:"
echo "AI поиск пар -> скоринг -> risk filter -> backtest -> manager brief -> отдельный аудит."
echo "Live trading и реальные ордера сейчас НЕ включаются."
