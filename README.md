# Binance Spot Trading Bot — безопасный аналитический crypto scanner

Документация на русском языке для проекта `binance-spot-trading-bot`.

Проект сейчас используется как безопасный аналитический сканер крипторынка и публичных Telegram-каналов. Главный принцип: **аналитика разрешена, автоматическая торговля и создание ордеров запрещены**.

---

## 1. Текущее стабильное состояние

Актуальная стабильная сборка с безопасным cron, Telegram-уведомлениями, safety gate и blocked risk отчётами:

```bash
scanner-safe-project-status-map-v2
```

Предыдущие стабильные теги:

```bash
scanner-safe-cron-v1
scanner-safe-telegram-v1
```

Основной репозиторий:

```bash
https://github.com/NetGeniusDeveloper/binance-spot-trading-bot
```

Рабочая директория в Termux/Ubuntu:

```bash
/root/binance-spot-trading-bot
```

---

## 2. Documentation map

Use these files as the current documentation set:

```text
README.md
CRON_SETUP.md
SAFE_RELEASES.md
PROJECT_STATUS.md
```

Purpose:

- `README.md` — main project overview and safe usage guide.
- `CRON_SETUP.md` — safe cron setup instructions.
- `SAFE_RELEASES.md` — stable releases, tags, and rollback map.
- `PROJECT_STATUS.md` — short current project status summary.

Current stable map tag:

```text
scanner-safe-project-status-map-v2
```

---


## 3. Главное правило безопасности

Проект работает только в аналитическом режиме.

Скрипты проекта не должны:

- создавать Binance-ордера;
- запускать торгового бота;
- включать автоматическую торговлю;
- обходить Telegram safety-флаги;
- автоматически менять конфигурацию каналов без ручной проверки.

Telegram-уведомление является только аналитическим сообщением. Это не торговый сигнал и не команда на вход.

---

## 4. Основные безопасные команды

Перейти в проект:

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate
```

Проверить состояние Git:

```bash
git status
git log --oneline -5
```

Запустить ежедневный безопасный pipeline вручную:

```bash
./run_daily_scanner_agent_safe.sh
```

Запустить cron-wrapper вручную:

```bash
./run_daily_scanner_agent_cron_safe.sh
```

Проверить safety gate:

```bash
cat reports/scanner_agent_safety_gate_report.txt
cat reports/scanner_agent_safety_gate_report.json
```

---

## 5. Основные файлы проекта

### Главные runner-скрипты

```bash
run_daily_scanner_agent_safe.sh
run_daily_scanner_agent_cron_safe.sh
run_full_scanner_agent_notification_pipeline_safe.sh
```

### Telegram и scanner pipeline

```bash
telegram_real_messages_preview.py
telegram_real_messages_analyze.py
telegram_real_market_scanner.py
telegram_channel_quality_report.py
telegram_channel_config_recommendations.py
scanner_agent_export.py
scanner_agent_decision.py
scanner_agent_decision_report.py
scanner_agent_blocked_risk_report.py
scanner_agent_notification_report.py
scanner_agent_telegram_message_preview.py
scanner_agent_telegram_sender_dry_run.py
scanner_agent_telegram_sender.py
scanner_agent_telegram_sender_audit_report.py
scanner_agent_pipeline_summary.py
scanner_agent_safety_gate_report.py
```

### Документация

```bash
README.md
CRON_SETUP.md
```

### Requirements

```bash
requirements.txt
requirements-fixed.txt
requirements-py313.txt
```

---

## 6. Основные отчёты

Pipeline создаёт локальные отчёты в папке:

```bash
reports/
```

Главные отчёты:

```bash
reports/scanner_agent_pipeline_summary.txt
reports/scanner_agent_pipeline_summary.json

reports/scanner_agent_safety_gate_report.txt
reports/scanner_agent_safety_gate_report.json

reports/scanner_agent_blocked_risk_report.txt
reports/scanner_agent_blocked_risk_report.json

reports/scanner_agent_telegram_sender_audit_report.txt
reports/scanner_agent_telegram_sender_audit_report.json

reports/telegram_channel_quality_report.txt
reports/telegram_channel_quality_report.json

reports/telegram_channel_config_recommendations.txt
reports/telegram_channel_config_recommendations.json
```

---

## 7. Safety gate

Safety gate — финальная проверка безопасного состояния pipeline.

Файлы:

```bash
reports/scanner_agent_safety_gate_report.json
reports/scanner_agent_safety_gate_report.txt
```

Скрипт:

```bash
python scanner_agent_safety_gate_report.py
```

Безопасные состояния:

```text
safe
duplicate_blocked
```

Состояние, которое не считается опасным, но требует ручной проверки:

```text
review_required
```

Опасные или блокирующие состояния:

```text
failed
blocked
unknown
```

Ожидаемый успешный результат:

```text
Gate status: safe
Safety gate OK: True
Review required: False
Blockers: none
Warnings: none
```

---

## 7. Telegram safety-флаги

Telegram-отправка управляется только флагами окружения и безопасной логикой sender-а.

Рекомендуемый безопасный режим для unattended cron:

```bash
SCANNER_TELEGRAM_SEND_ENABLED=false
SCANNER_TELEGRAM_MANUAL_CONFIRM=false
```

Контролируемая аналитическая отправка после ручного решения:

```bash
SCANNER_TELEGRAM_SEND_ENABLED=true
SCANNER_TELEGRAM_MANUAL_CONFIRM=true
```

Даже при включённых Telegram-флагах проект не должен создавать ордера и не должен запускать торгового бота.

---

## 8. .env

Файл `.env` должен храниться только локально и не попадать в GitHub.

Пример полей:

```bash
BINANCE_API_KEY=""
BINANCE_SECRET_KEY=""

TELEGRAM_API_KEY=""
TELEGRAM_USER_ID=""

TELEGRAM_API_ID=""
TELEGRAM_API_HASH=""
TELEGRAM_SESSION_NAME="crypto_scanner_session"

TELEGRAM_ALERT_CHAT_ID=""

SCANNER_TELEGRAM_SEND_ENABLED=false
SCANNER_TELEGRAM_MANUAL_CONFIRM=false
```

Проверка:

```bash
cat .env
```

Не публикуйте реальные ключи, токены и session-файлы.

---

## 9. .gitignore

В проекте должен быть `.gitignore`, который не даёт случайно отправить в GitHub:

- `.env`;
- `__pycache__/`;
- `*.session`;
- локальные отчёты `reports/*.json`;
- локальные отчёты `reports/*.txt`;
- логи;
- локальные базы данных;
- временные patch-файлы.

Проверка:

```bash
git check-ignore -v .env
git check-ignore -v crypto_scanner_session.session
git check-ignore -v reports/scanner_agent_safety_gate_report.json
git check-ignore -v reports/scanner_agent_safety_gate_report.txt
git check-ignore -v reports/daily_scanner_agent_cron_safe.log
git check-ignore -v data/social_scanner.db
```

Проверка, что опасные runtime-файлы не отслеживаются Git:

```bash
git ls-files | grep -E '^\.env$|__pycache__|\.session$|^reports/.*\.(json|txt|log)$|^data/social_scanner\.db$' || echo "[OK] опасные файлы не отслеживаются Git"
```

---

## 10. Safe daily runner

Главный ручной безопасный запуск:

```bash
./run_daily_scanner_agent_safe.sh
```

Что делает runner:

1. проверяет bash-синтаксис полного pipeline;
2. запускает полный безопасный scanner pipeline;
3. создаёт Telegram sender audit;
4. печатает итоговый pipeline summary;
5. создаёт и печатает blocked risk report;
6. печатает channel quality report;
7. печатает channel config recommendations;
8. запускает safety gate;
9. показывает итоговый безопасный статус.

Проверка:

```bash
bash -n run_daily_scanner_agent_safe.sh
./run_daily_scanner_agent_safe.sh
cat reports/scanner_agent_safety_gate_report.txt
```

---

## 11. Full scanner notification pipeline

Полный безопасный pipeline:

```bash
./run_full_scanner_agent_notification_pipeline_safe.sh
```

Он выполняет:

- compile-check Python-файлов;
- bash-check runner-файлов;
- сбор публичных Telegram-сообщений;
- анализ Telegram-сообщений;
- market scanner;
- channel quality report;
- channel config recommendations;
- decision layer;
- decision report;
- blocked risk report;
- notification report;
- Telegram message preview;
- dry-run sender;
- controlled Telegram sender;
- pipeline summary.

Проверка:

```bash
bash -n run_full_scanner_agent_notification_pipeline_safe.sh
./run_full_scanner_agent_notification_pipeline_safe.sh
```

---

## 13. Отчёт blocked risk

В проект добавлен отдельный безопасный отчёт по сигналам, которые были заблокированы риск-фильтром.

Файлы:

```bash
reports/scanner_agent_blocked_risk_report.txt
reports/scanner_agent_blocked_risk_report.json
```

Скрипт:

```bash
python scanner_agent_blocked_risk_report.py
```

Отчёт показывает:

- какие пары были заблокированы;
- источник сигнала;
- уровень риска;
- итоговую оценку;
- market score;
- telegram score;
- risk adjustment;
- риск-флаги;
- рыночное подтверждение;
- наличие или отсутствие ретеста;
- понятные причины блокировки;
- manager note;
- recommended next step.

Пример проверки:

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate

python -m py_compile scanner_agent_blocked_risk_report.py
python scanner_agent_blocked_risk_report.py

cat reports/scanner_agent_blocked_risk_report.txt
cat reports/scanner_agent_blocked_risk_report.json
```

Ожидаемый безопасный результат:

```text
Safe to continue: True
Blockers: none
Warnings: none
[OK] This report did not create orders.
[OK] This report did not start trading bot.
[OK] This report did not call Binance API.
```

Важно:

```text
blocked_risk означает: не использовать сигнал для входа.
```

Blocked risk report является только аналитическим. Он не создаёт ордера, не запускает торгового бота, не отправляет Telegram-сообщения и не вызывает Binance API.

---

## 13. Decision layer

Decision layer читает:

```bash
reports/scanner_agent_export.json
```

и создаёт:

```bash
reports/scanner_agent_decision.json
```

Скрипт:

```bash
python scanner_agent_decision.py
```

Возможные решения:

```text
candidate
wait_confirmation
wait_retest
observe
blocked_risk
ignore
```

Сейчас безопасная логика усиливает риск-фильтр. Слабые сигналы, отсутствие подтверждения, отсутствие ретеста, слабое Telegram-подтверждение и опасные FOMO/pump-флаги приводят к `blocked_risk`, `ignore` или наблюдательному статусу.

---

## 14. Notification report и Telegram preview

Notification report:

```bash
python scanner_agent_notification_report.py
cat reports/scanner_agent_notification_report.txt
```

Telegram preview:

```bash
python scanner_agent_telegram_message_preview.py
cat reports/scanner_agent_telegram_message_preview.txt
```

Эти скрипты:

- не создают ордера;
- не запускают бота;
- не вызывают Binance API;
- не читают Telegram;
- не отправляют Telegram-сообщения.

Telegram preview только формирует локальный текст будущего аналитического уведомления.

---

## 15. Telegram sender dry-run

Dry-run sender:

```bash
./run_scanner_agent_telegram_sender_dry_run.sh
```

Он проверяет:

- наличие preview-файла;
- длину сообщения;
- наличие Telegram token;
- наличие chat id;
- safety-флаги;
- блокеры;
- предупреждения.

Dry-run не отправляет Telegram-сообщение.

---

## 16. Telegram sender safe-run

Safe sender:

```bash
./run_scanner_agent_telegram_sender_safe.sh
```

Реальная Telegram-отправка возможна только если одновременно включены два флага:

```bash
SCANNER_TELEGRAM_SEND_ENABLED=true
SCANNER_TELEGRAM_MANUAL_CONFIRM=true
```

Sender всё равно не создаёт ордера, не запускает торгового бота и не вызывает Binance API.

---

## 17. Cron

Подробная инструкция по cron находится в отдельном файле:

```bash
CRON_SETUP.md
```

Открыть:

```bash
cat CRON_SETUP.md
```

Ручная проверка cron-wrapper:

```bash
bash -n run_daily_scanner_agent_cron_safe.sh
./run_daily_scanner_agent_cron_safe.sh
tail -n 160 reports/daily_scanner_agent_cron_safe.log
cat reports/scanner_agent_safety_gate_report.txt
```

Пример cron-задания на 09:00:

```cron
0 9 * * * /root/binance-spot-trading-bot/run_daily_scanner_agent_cron_safe.sh
```

---

## 18. Проверка после установки или обновления

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate

git status
git log --oneline -5

python -m py_compile \
  scanner_agent_decision.py \
  scanner_agent_blocked_risk_report.py \
  scanner_agent_pipeline_summary.py \
  scanner_agent_safety_gate_report.py \
  scanner_agent_telegram_sender_audit_report.py

bash -n run_daily_scanner_agent_safe.sh
bash -n run_full_scanner_agent_notification_pipeline_safe.sh
bash -n run_daily_scanner_agent_cron_safe.sh

./run_daily_scanner_agent_safe.sh

cat reports/scanner_agent_blocked_risk_report.txt
cat reports/scanner_agent_pipeline_summary.txt
cat reports/scanner_agent_safety_gate_report.txt
```

---

## 19. Ожидаемое безопасное состояние

Успешный pipeline должен показывать:

```text
Safe pipeline: True
Safety gate OK: True
Review required: False
Blockers: none
Warnings: none
Orders enabled: False
Trading enabled: False
Binance orders created: False
```

Допустимый blocked risk результат:

```text
Blocked risk items: 1
Safe to continue: True
Blockers: none
Warnings: none
```

Это безопасно, потому что blocked risk означает запрет входа.

---

## 20. Git workflow

Проверить состояние:

```bash
git status
git log --oneline -5
```

Добавить изменения:

```bash
git add .
```

Коммит:

```bash
git commit -m "описание изменения"
```

Отправить в GitHub:

```bash
git push origin main
```

Проверить итог:

```bash
git status
git log --oneline -5
```

---

## 21. Установка готовых README.md и CRON_SETUP.md из Download

Если файлы скачаны в Android Download, заменить их в проекте можно так:

```bash
cd /root/binance-spot-trading-bot

cp README.md README.md.before_update.backup
cp CRON_SETUP.md CRON_SETUP.md.before_update.backup

mv ./../../storage/emulated/0/Download/README.md README.md
mv ./../../storage/emulated/0/Download/CRON_SETUP.md CRON_SETUP.md

git status
```

Проверить, что документация содержит blocked risk:

```bash
grep -n "blocked risk\|scanner_agent_blocked_risk_report\|заблокированным риск" README.md CRON_SETUP.md
```

После проверки:

```bash
git add README.md CRON_SETUP.md
git commit -m "Update docs for blocked risk scanner reports"
git push origin main

git status
git log --oneline -5
```

---

## 22. Следующий разумный шаг

После стабильной сборки `scanner-safe-risk-reports-v1` следующий безопасный этап:

1. улучшить качество Telegram-сигналов;
2. расширить watchlist;
3. добавить больше источников публичных каналов;
4. улучшить scoring и risk explanations;
5. добавить отдельный отчёт по quality trend каналов;
6. оставить ордера и торгового бота отключёнными.

Автоматическая торговля не включается, пока не будет отдельного ручного approval-layer и отдельной safety-архитектуры.

---

## Как пользоваться менеджерской сводкой каждый день

Менеджерская сводка предназначена только для ручного безопасного анализа. Она не является торговым сигналом и не разрешает вход в сделку.

Ежедневный безопасный сценарий:

1. Откройте главное меню Termux/Ubuntu:

        /root/main-menu.sh

2. Перейдите в раздел:

        BINANCE SPOT БОТ / БЕЗОПАСНЫЙ СКАНЕР

3. Сначала выберите:

        3) Короткий статус безопасности

   Проверьте, что безопасные флаги остаются включёнными:

        DRY_RUN=True
        SEND_TELEGRAM_MESSAGE=False
        WALLET_USAGE_PERCENT=0.0
        Orders disabled
        Live trading disabled
        Telegram auto-send disabled

4. Затем выберите:

        2) Менеджерская сводка

5. Если сводка показывает:

        Все текущие пары заблокированы. Вход запрещён.

   значит входить нельзя. Пары можно оставить только для ручного наблюдения.

6. Если появились карточки ручной проверки, читайте:

   - тикер;
   - решение безопасности;
   - уровень риска;
   - причины блокировки;
   - условия разблокировки;
   - рекомендуемый следующий шаг.

7. Любая карточка со статусом `НЕ ВХОДИТЬ` означает:

        не создавать ордера;
        не включать live trading;
        не отправлять Telegram автоматически;
        оставить пару только в аналитическом журнале.

8. После просмотра можно открыть отчёты:

        7) Сводка отчётов

   Основные отчёты:

        reports/manager_brief_report.txt
        reports/manual_review_cards.txt
        reports/quick_safe_dashboard.txt
        reports/scanner_agent_pipeline_summary.txt
        reports/scanner_agent_safety_gate_report.txt

Правило безопасности:

Менеджерская сводка помогает быстро понять, что требует внимания. Она не заменяет ручной анализ, не включает торговлю и не является разрешением на сделку.

Быстрый запуск без меню:

        ./manager_daily.sh

Эта команда одной операцией показывает короткий статус безопасности и менеджерскую сводку. Она не создаёт ордера, не включает live trading, не вызывает Binance private API и не отправляет Telegram-сообщения.

Документация по восстановлению меню:

        docs/TERMUX_MAIN_MENU_BINANCE.md
