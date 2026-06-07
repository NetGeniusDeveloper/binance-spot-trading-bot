# SAFE_RELEASES.md

# Стабильные релизы безопасного crypto scanner pipeline

Этот документ фиксирует стабильные точки проекта `binance-spot-trading-bot`.

Назначение файла:

- быстро понять, какой тег за что отвечает;
- знать, к какой версии можно откатиться;
- иметь короткие команды проверки после обновлений;
- не смешивать безопасный аналитический scanner pipeline с торговым ботом;
- сохранить историю стабильных этапов: Telegram, cron, blocked risk, документация, safety gate.

Проект работает в безопасном аналитическом режиме:

- ордера Binance не создаются;
- торговый бот не запускается;
- автоматическая торговля не включается;
- Telegram-уведомления разрешены только через ручные safety-флаги;
- safety gate читает локальные отчёты и не выполняет опасных действий;
- blocked risk report показывает только причины блокировки сигналов.

---

## 1. Актуальная стабильная точка

Актуальная стабильная версия на момент создания этого файла:

```text
tag: scanner-safe-gate-count-fix-v1
commit: f37fdb0
branch: main
```

Описание:

```text
Стабильная сборка с исправленным источником счётчика total_decisions в safety gate.
```

Почему это важно:

Ранее safety gate мог брать `total_decisions` из старого Telegram sender result, если свежий pipeline завершался статусом `no_decisions`. После исправления приоритет источника стал безопаснее: сначала актуальный pipeline/decision report, затем старые вспомогательные отчёты.

Ожидаемый безопасный результат при отсутствии решений:

```text
Final status: no_decisions
Safety gate OK: True
Review required: False
Telegram message sent: False
Total decisions: 0
```

---

## 2. Список стабильных тегов

### scanner-safe-telegram-v1

Назначение:

```text
Стабильный безопасный Telegram pipeline с audit и safety gate.
```

Что проверяет:

- Telegram sender работает только при safety-флагах;
- сообщения не дублируются без проверки;
- Telegram audit фиксирует результат отправки;
- pipeline не создаёт ордера;
- pipeline не запускает торгового бота.

Ключевые файлы:

```text
scanner_agent_telegram_sender.py
scanner_agent_telegram_sender_dry_run.py
scanner_agent_telegram_sender_audit_report.py
scanner_agent_pipeline_summary.py
scanner_agent_safety_gate_report.py
run_scanner_agent_telegram_sender_safe.sh
```

---

### scanner-safe-cron-v1

Назначение:

```text
Стабильная безопасная cron-сборка scanner pipeline.
```

Что добавлено:

- безопасный cron-wrapper;
- cron-лог;
- проверка safety gate после запуска;
- документация по cron;
- `.gitignore` для секретов и runtime-файлов.

Ключевые файлы:

```text
run_daily_scanner_agent_cron_safe.sh
run_daily_scanner_agent_safe.sh
CRON_SETUP.md
README.md
.gitignore
```

Проверка:

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate

bash -n run_daily_scanner_agent_cron_safe.sh
./run_daily_scanner_agent_cron_safe.sh

tail -n 200 reports/daily_scanner_agent_cron_safe.log
cat reports/scanner_agent_safety_gate_report.txt
```

Ожидаемый результат:

```text
Gate status: safe
Safety gate OK: True
Review required: False
No orders were created
Trading bot was not started
```

---

### scanner-safe-risk-reports-v1

Назначение:

```text
Стабильная сборка pipeline с blocked risk report.
```

Что добавлено:

- отдельный отчёт по заблокированным риск-фильтром сигналам;
- интеграция blocked risk report в daily runner;
- интеграция blocked risk report в full pipeline;
- человекочитаемые причины блокировки;
- пояснение для менеджера/пользователя.

Ключевые файлы:

```text
scanner_agent_blocked_risk_report.py
scanner_agent_decision.py
scanner_agent_decision_report.py
scanner_agent_notification_report.py
scanner_agent_telegram_message_preview.py
run_daily_scanner_agent_safe.sh
run_full_scanner_agent_notification_pipeline_safe.sh
```

Проверка:

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
Orders enabled: False
Trading enabled: False
Binance orders created: False
Telegram sending: False
```

Если есть заблокированные сигналы, это не ошибка. Это безопасное состояние:

```text
Blocked risk means: do not use this signal for entry.
This report is only for analytical review.
No orders are created.
```

---

### scanner-safe-risk-docs-v1

Назначение:

```text
Стабильная документация с описанием cron, safety gate и blocked risk reports.
```

Что добавлено:

- обновлённый README.md;
- обновлённый CRON_SETUP.md;
- команды проверки;
- описание stable tags;
- объяснение blocked risk report;
- команды установки cron;
- команды безопасной ручной проверки.

Ключевые файлы:

```text
README.md
CRON_SETUP.md
```

Проверка документации:

```bash
cd /root/binance-spot-trading-bot

grep -n "scanner_agent_blocked_risk_report\|blocked risk\|Safety gate\|cron" README.md CRON_SETUP.md
grep -n 'blocked risk\\scanner_agent_blocked_risk_report' README.md CRON_SETUP.md || echo "[OK] битый grep-шаблон не найден"
grep -n "run_daily_scanner_agentcron\|Можно включать cro[^n]" README.md CRON_SETUP.md || echo "[OK] явные опечатки не найдены"
```

---

### scanner-safe-gate-count-fix-v1

Назначение:

```text
Стабильная сборка с исправленным счётчиком total_decisions в safety gate.
```

Что исправлено:

- safety gate теперь корректно показывает `Total decisions: 0`, если актуальный pipeline завершился статусом `no_decisions`;
- старый `scanner_agent_telegram_sender_result.json` больше не должен сбивать итоговый счётчик в safety gate;
- cron-wrapper корректно проходит при безопасном статусе `no_decisions`.

Ключевой файл:

```text
scanner_agent_safety_gate_report.py
```

Проверка:

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate

python -m py_compile scanner_agent_safety_gate_report.py
python scanner_agent_safety_gate_report.py

cat reports/scanner_agent_safety_gate_report.txt
cat reports/scanner_agent_safety_gate_report.json
```

Ожидаемый результат при no_decisions:

```text
Gate status: safe
Pipeline final status: no_decisions
Safety gate OK: True
Review required: False
Total decisions: 0
Telegram message sent: False
```

---

## 3. Полная ручная проверка актуальной стабильной сборки

Перед любыми новыми изменениями выполните:

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate

git status
git log --oneline -5
git tag --list
```

Ожидаемо:

```text
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

Проверка Python-файлов:

```bash
python -m py_compile \
  scanner_agent_safety_gate_report.py \
  scanner_agent_blocked_risk_report.py \
  scanner_agent_decision.py \
  scanner_agent_decision_report.py \
  scanner_agent_notification_report.py \
  scanner_agent_telegram_message_preview.py \
  scanner_agent_telegram_sender.py \
  scanner_agent_pipeline_summary.py
```

Проверка bash runner-ов:

```bash
bash -n run_daily_scanner_agent_safe.sh
bash -n run_daily_scanner_agent_cron_safe.sh
bash -n run_full_scanner_agent_notification_pipeline_safe.sh
bash -n run_scanner_agent_telegram_sender_safe.sh
```

Полный безопасный daily запуск:

```bash
./run_daily_scanner_agent_safe.sh

cat reports/scanner_agent_pipeline_summary.txt
cat reports/scanner_agent_safety_gate_report.txt
cat reports/scanner_agent_blocked_risk_report.txt
```

Cron-wrapper вручную:

```bash
./run_daily_scanner_agent_cron_safe.sh

tail -n 200 reports/daily_scanner_agent_cron_safe.log
cat reports/scanner_agent_safety_gate_report.txt
cat reports/scanner_agent_blocked_risk_report.txt
```

---

## 4. Критерии безопасного состояния

Сборка считается безопасной, если:

```text
Safety gate OK: True
Review required: False
Orders enabled: False
Trading enabled: False
Binance API used: False
Binance orders created: False
```

Допустимые безопасные статусы:

```text
safe
duplicate_blocked
no_decisions
no_signals
all_signals_blocked
```

Статусы, требующие внимания:

```text
review_required
telegram_delivery_unknown
```

Статусы, при которых нельзя продолжать без проверки:

```text
blocked
failed
notification_failed
send_attempt_failed
unknown
```

---

## 5. Важное правило по Telegram

Telegram-отправка разрешена только при двух флагах:

```bash
SCANNER_TELEGRAM_SEND_ENABLED=true
SCANNER_TELEGRAM_MANUAL_CONFIRM=true
```

Для cron без присмотра рекомендуемый безопасный режим:

```bash
SCANNER_TELEGRAM_SEND_ENABLED=false
SCANNER_TELEGRAM_MANUAL_CONFIRM=false
```

Если `total_decisions=0`, Telegram sender должен быть пропущен:

```text
Telegram sender safe run skipped to avoid empty notification.
```

---

## 6. Важное правило по blocked risk

`blocked_risk` — это не торговый сигнал.

Это означает:

- вход запрещён;
- сигнал не использовать для сделки;
- сигнал можно сохранить только как аналитическую запись;
- нужен ручной анализ;
- автоордера запрещены.

Пример безопасного blocked risk результата:

```text
Decision: blocked_risk
Action: не использовать, заблокировано риском
Recommended next step: Не входить.
```

---

## 7. Быстрый откат к стабильной версии

Посмотреть теги:

```bash
cd /root/binance-spot-trading-bot
git tag --list
```

Откатиться для проверки к конкретному тегу без изменения ветки:

```bash
git checkout scanner-safe-gate-count-fix-v1
```

Вернуться обратно на main:

```bash
git checkout main
git pull origin main
```

Если нужно создать новую ветку от стабильного тега:

```bash
git checkout -b test-from-safe-gate-count scanner-safe-gate-count-fix-v1
```

---

## 8. Git workflow после изменения release notes

После установки или изменения этого файла:

```bash
cd /root/binance-spot-trading-bot

git status
git add SAFE_RELEASES.md
git commit -m "Add safe scanner release notes"
git push origin main

git status
git log --oneline -5
```

Если нужно создать новый стабильный тег после проверки:

```bash
git tag -a scanner-safe-release-notes-v1 -m "Stable safe scanner release notes"
git push origin scanner-safe-release-notes-v1

git tag --list
git log --oneline -5
```

---

## 9. Установка этого файла из Download

Если файл скачан в папку Android Download, установить его можно так:

```bash
cd /root/binance-spot-trading-bot

cp ./../../storage/emulated/0/Download/SAFE_RELEASES.md SAFE_RELEASES.md

git status
cat SAFE_RELEASES.md
```

После проверки:

```bash
git add SAFE_RELEASES.md
git commit -m "Add safe scanner release notes"
git push origin main
```

---

## 10. Текущая рекомендуемая база для дальнейшей разработки

Продолжать разработку лучше от:

```text
scanner-safe-gate-count-fix-v1
```

Причина:

- уже есть безопасный cron;
- есть документация;
- есть blocked risk report;
- исправлен safety gate decision count;
- GitHub синхронизирован;
- рабочее дерево было чистым после последней проверки.

Следующий разумный этап после этого файла:

```text
Добавить SAFE_RELEASES.md в README.md как ссылку на карту стабильных релизов.
```
