# Termux/Ubuntu: главное меню для Binance Spot Bot

Версия документации: `scanner-safe-main-menu-docs-v1`

Этот документ фиксирует локальную интеграцию проекта **Binance Spot Trading Bot** в главное меню Termux/Ubuntu.

Файл меню находится здесь:

    /root/main-menu.sh

Важно: `/root/main-menu.sh` находится вне Git-репозитория Binance. Поэтому в Git сохраняется не сам файл меню, а инструкция по его восстановлению.

---

## 1. Назначение меню

Binance-раздел меню нужен для безопасного запуска аналитических режимов:

- быстрая безопасная панель;
- менеджерская сводка;
- короткий статус безопасности;
- ежедневный безопасный запуск;
- безопасная проверка релиза;
- полный безопасный конвейер;
- сводка отчётов;
- безопасные команды запуска.

Меню не включает live-trading и не создаёт реальные ордера.

---

## 2. Финальный вид Binance-раздела

    ======================================
     BINANCE SPOT БОТ / БЕЗОПАСНЫЙ СКАНЕР
    ======================================
    Папка: /root/binance-spot-trading-bot
    Режим по умолчанию: safe / analytical only
    --------------------------------------
    1) Быстрая безопасная панель
    2) Менеджерская сводка
    3) Короткий статус безопасности
    4) Ежедневный безопасный запуск
    5) Безопасная проверка релиза
    6) Полный безопасный конвейер
    7) Сводка отчётов
    --------------------------------------
    8) Открыть папку проекта
    9) Git: статус / pull / последние коммиты
    10) Найти файлы сканера/агента/Telegram/уведомлений
    11) Проверить Python-файлы
    12) Отправить изменения в GitHub
    13) Показать безопасные команды запуска
    14) Старый прямой запуск проекта
    0) Назад

---

## 3. Основные команды

Быстрая безопасная панель:

    python3 quick_safe_dashboard.py

Менеджерская сводка:

    python3 quick_safe_dashboard.py --manager

Безопасная проверка релиза:

    ./safe_status_release.sh --check-only

Ежедневный безопасный запуск:

    ./run_daily_scanner_agent_safe.sh

Полный безопасный конвейер:

    ./run_full_scanner_agent_notification_pipeline_safe.sh

---

## 4. Короткий статус безопасности

Пункт меню:

    3) Короткий статус безопасности

Он должен показывать примерно такие строки:

    Git: clean
    Branch: main
    DRY_RUN: True
    SEND_TELEGRAM_MESSAGE: False
    WALLET_USAGE_PERCENT: 0.0
    Safe to continue: True
    Action allowed: False
    Orders: disabled
    Telegram: disabled
    Mode: analytical only

---

## 5. Сводка отчётов

Пункт меню:

    7) Сводка отчётов

Порядок отчётов:

    reports/manager_brief_report.txt
    reports/manual_review_cards.txt
    reports/quick_safe_dashboard.txt
    reports/scanner_agent_scenario_matrix_report.txt
    reports/scanner_agent_risk_filter_backtest.txt
    reports/scanner_agent_pipeline_summary.txt

Сначала идут менеджерские отчёты, затем технические.

---

## 6. Проверка после восстановления меню

Выполнить:

    cd /root/binance-spot-trading-bot
    bash -n /root/main-menu.sh
    python3 quick_safe_dashboard.py --manager
    ./safe_status_release.sh --check-only
    git status

Ожидаемо:

    /root/main-menu.sh: синтаксис OK
    менеджерская сводка работает
    safe release check проходит
    git status clean

---

## 7. Правила безопасности

По умолчанию должны сохраняться значения:

    DRY_RUN=True
    SEND_TELEGRAM_MESSAGE=False
    WALLET_USAGE_PERCENT=0.0

Без отдельного аудита запрещено:

- включать live-trading;
- создавать реальные ордера;
- отправлять реальные Telegram-сообщения;
- коммитить `.env`, API-ключи, базы данных, логи, кэши и runtime-файлы.

---

## 8. Backup-файлы локального меню

Во время настройки могли создаваться backup-файлы:

    /root/main-menu.sh.before-binance-manager-brief-v1
    /root/main-menu.sh.before-reports-summary-manager-first-v1
    /root/main-menu.sh.before-status-snapshot-v1
    /root/main-menu.sh.before-commands-help-v1
    /root/main-menu.sh.before-russian-binance-menu-v1

Они находятся вне Git и нужны только для локального восстановления.
