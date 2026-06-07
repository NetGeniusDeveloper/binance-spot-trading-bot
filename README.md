# Binance Spot Trading Bot / Crypto Scanner Agent

Русскоязычная документация проекта безопасного аналитического крипто-сканера.

Проект предназначен для анализа криптовалютных сигналов, публичных Telegram-каналов и рыночных данных в безопасном режиме. Текущая стабильная версия делает аналитический прогон, формирует отчёты, может отправлять аналитическое Telegram-уведомление только через ручные флаги безопасности и не создаёт торговые ордера.

> Важно: текущая стабильная сборка является аналитической. Она не запускает торгового бота, не создаёт Binance-ордера и не включает автоматическую торговлю.

---

## Текущая стабильная версия

Стабильный тег:

```bash
scanner-safe-telegram-v1
```

Текущий основной безопасный cron-wrapper:

```bash
run_daily_scanner_agent_cron_safe.sh
```

Основной ежедневный runner:

```bash
run_daily_scanner_agent_safe.sh
```

Полный безопасный pipeline:

```bash
run_full_scanner_agent_notification_pipeline_safe.sh
```

Safety gate отчёты:

```bash
reports/scanner_agent_safety_gate_report.json
reports/scanner_agent_safety_gate_report.txt
```

Cron-лог:

```bash
reports/daily_scanner_agent_cron_safe.log
```

Подробная инструкция по настройке cron находится здесь:

```bash
CRON_SETUP.md
```

---

## Что уже реализовано

На текущей стадии проект умеет:

- читать публичные Telegram-каналы, указанные в конфигурации;
- собирать preview сообщений;
- извлекать криптовалютные тикеры;
- анализировать социальные сигналы;
- учитывать рыночные данные;
- формировать рейтинг сигналов;
- сохранять результаты в JSON, TXT, Markdown и SQLite;
- строить agent export;
- принимать аналитическое решение по сигналам;
- формировать текст аналитического уведомления;
- выполнять dry-run Telegram sender;
- отправлять Telegram-уведомление только при включённых ручных флагах;
- блокировать повторную отправку одинаковых уведомлений по hash;
- корректно обрабатывать timeout Telegram-доставки как неизвестный статус;
- формировать audit report отправителя;
- формировать финальный safety gate report;
- запускаться через безопасный cron-wrapper.

---

## Главные файлы запуска

### Ежедневный безопасный запуск вручную

```bash
./run_daily_scanner_agent_safe.sh
```

Этот runner:

1. запускает полный аналитический pipeline;
2. формирует отчёты;
3. запускает audit Telegram sender;
4. запускает safety gate;
5. печатает итоговый статус.

### Безопасный cron-wrapper

```bash
./run_daily_scanner_agent_cron_safe.sh
```

Этот wrapper предназначен для запуска через cron. Он:

1. фиксирует git status и последние коммиты;
2. запускает ежедневный безопасный runner;
3. проверяет `reports/scanner_agent_safety_gate_report.json`;
4. завершает работу успешно только при безопасном состоянии;
5. пишет лог в `reports/daily_scanner_agent_cron_safe.log`.

---

## Модель безопасности

Проект должен оставаться в режиме аналитики.

Запрещено для безопасной ветки:

- создавать Binance-ордера;
- запускать торгового бота;
- включать автоматическую торговлю;
- обходить Telegram safety flags;
- автоматически менять конфигурацию каналов без ручной проверки.

Telegram-отправка контролируется только переменными окружения и логикой sender safety.

---

## Безопасные статусы safety gate

Safety gate считает безопасными состояния:

```text
safe
duplicate_blocked
```

Состояние, требующее ручной проверки, но не означающее опасного действия:

```text
review_required
```

Небезопасные или блокирующие состояния:

```text
failed
blocked
unknown
```

---

## Установка проекта

### 1. Перейти в директорию проекта

```bash
cd /root/binance-spot-trading-bot
```

Проверить, что вы находитесь в правильном месте:

```bash
pwd
git status
git log --oneline -5
```

Ожидаемый путь:

```text
/root/binance-spot-trading-bot
```

Ожидаемое состояние после синхронизации:

```text
nothing to commit, working tree clean
```

### 2. Создать и активировать виртуальное окружение

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Установить зависимости

Обычная установка:

```bash
pip install -r requirements.txt
```

Если используется Python 3.13 и есть отдельный файл зависимостей:

```bash
pip install -r requirements-py313.txt
```

Если используется зафиксированный набор зависимостей:

```bash
pip install -r requirements-fixed.txt
```

---

## Настройка `.env`

Откройте файл:

```bash
nano .env
```

Пример структуры:

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

### Рекомендуемый безопасный режим для cron

```bash
SCANNER_TELEGRAM_SEND_ENABLED=false
SCANNER_TELEGRAM_MANUAL_CONFIRM=false
```

### Контролируемая аналитическая Telegram-отправка

Использовать только после ручного решения:

```bash
SCANNER_TELEGRAM_SEND_ENABLED=true
SCANNER_TELEGRAM_MANUAL_CONFIRM=true
```

Не включайте никакие флаги исполнения ордеров.

---

## Проверка проекта перед запуском

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate

python -m py_compile   credentials.py   scanner_agent_telegram_sender.py   scanner_agent_telegram_message_preview.py   scanner_agent_telegram_sender_dry_run.py   scanner_agent_telegram_sender_audit_report.py   scanner_agent_pipeline_summary.py   scanner_agent_safety_gate_report.py

bash -n run_daily_scanner_agent_safe.sh
bash -n run_daily_scanner_agent_cron_safe.sh
bash -n run_full_scanner_agent_notification_pipeline_safe.sh
```

---

## Ручной безопасный запуск

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate

./run_daily_scanner_agent_safe.sh
```

Проверить итоговые отчёты:

```bash
cat reports/scanner_agent_safety_gate_report.txt
cat reports/scanner_agent_pipeline_summary.txt
cat reports/scanner_agent_telegram_sender_audit_report.txt
```

Быстрый JSON-статус:

```bash
python - <<'PY'
import json
from pathlib import Path

path = Path("reports/scanner_agent_safety_gate_report.json")
payload = json.loads(path.read_text(encoding="utf-8"))

print("Gate status:", payload.get("gate_status"))
print("Safety gate OK:", payload.get("safety_gate_ok"))
print("Review required:", payload.get("review_required"))
print("Blockers:", ", ".join(payload.get("blockers", [])) or "none")
print("Warnings:", ", ".join(payload.get("warnings", [])) or "none")
PY
```

---

## Cron-настройка

Подробная инструкция находится в отдельном файле:

```bash
CRON_SETUP.md
```

Краткая версия:

```bash
crontab -e
```

Запуск один раз в день в 09:00 серверного времени:

```cron
0 9 * * * /root/binance-spot-trading-bot/run_daily_scanner_agent_cron_safe.sh
```

Запуск каждые 6 часов:

```cron
0 */6 * * * /root/binance-spot-trading-bot/run_daily_scanner_agent_cron_safe.sh
```

Проверить установленные cron-задачи:

```bash
crontab -l
```

Проверить результат после выполнения:

```bash
cd /root/binance-spot-trading-bot

tail -n 200 reports/daily_scanner_agent_cron_safe.log
cat reports/scanner_agent_safety_gate_report.txt
```

---

## Основные отчёты

После запуска создаются или обновляются:

```bash
reports/telegram_real_messages_preview.json
reports/telegram_real_social_signals.json
reports/telegram_real_market_rated_signals.json
reports/telegram_channel_quality_report.json
reports/telegram_channel_quality_report.txt
reports/telegram_channel_config_recommendations.json
reports/telegram_channel_config_recommendations.txt
reports/social_scanner_demo_report.md
reports/scanner_agent_export.json
reports/scanner_agent_decision.json
reports/scanner_agent_notification_report.txt
reports/scanner_agent_telegram_message_preview.txt
reports/scanner_agent_telegram_sender_dry_run.json
reports/scanner_agent_telegram_sender_result.json
reports/scanner_agent_telegram_sender_audit_report.json
reports/scanner_agent_telegram_sender_audit_report.txt
reports/scanner_agent_pipeline_summary.json
reports/scanner_agent_pipeline_summary.txt
reports/scanner_agent_safety_gate_report.json
reports/scanner_agent_safety_gate_report.txt
reports/daily_scanner_agent_cron_safe.log
```

SQLite база:

```bash
data/social_scanner.db
```

---

## Проверка Telegram sender

Dry-run:

```bash
./run_scanner_agent_telegram_sender_dry_run.sh
```

Полный безопасный sender runner:

```bash
./run_scanner_agent_telegram_sender_safe.sh
```

Проверить результат:

```bash
cat reports/scanner_agent_telegram_sender_result.json
cat reports/scanner_agent_telegram_sender_audit_report.txt
```

---

## Защита от дублей Telegram-уведомлений

Проект сохраняет hash последнего отправленного аналитического уведомления:

```bash
reports/scanner_agent_last_sent_hash.json
```

Если следующий текст уведомления совпадает с предыдущим после нормализации времени создания, повторная отправка блокируется.

Безопасный статус:

```text
duplicate_blocked
```

Это означает, что повторное одинаковое уведомление не отправлено, и это считается безопасным состоянием.

---

## Обработка Telegram timeout

Если Telegram API вернул timeout, доставка может быть неизвестной. Проект помечает это состояние отдельно.

В таком случае возможен статус:

```text
review_required
```

Нужно вручную проверить Telegram-чат, чтобы понять, пришло ли уведомление, и только потом запускать sender повторно.

---

## Каналы Telegram

Конфигурация реальных каналов:

```bash
scanner_real_channels.py
```

Отчёт качества каналов:

```bash
reports/telegram_channel_quality_report.txt
reports/telegram_channel_quality_report.json
```

Рекомендации по конфигурации:

```bash
reports/telegram_channel_config_recommendations.txt
reports/telegram_channel_config_recommendations.json
```

Важно: рекомендации не должны автоматически менять `scanner_real_channels.py` без ручной проверки.

---

## Экстренная безопасная остановка

Отключите Telegram-отправку в `.env`:

```bash
SCANNER_TELEGRAM_SEND_ENABLED=false
SCANNER_TELEGRAM_MANUAL_CONFIRM=false
```

После этого проверьте:

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate

./run_daily_scanner_agent_cron_safe.sh
tail -n 160 reports/daily_scanner_agent_cron_safe.log
```

---

## Git workflow

Перед изменениями:

```bash
cd /root/binance-spot-trading-bot
git status
git pull origin main
git log --oneline -5
```

После изменения файлов:

```bash
git status
git add README.md
git commit -m "Update Russian README with cron setup link"
git push origin main
```

Проверка финального состояния:

```bash
git status
git log --oneline -5
```

Ожидаемый результат:

```text
nothing to commit, working tree clean
```

---

## Быстрое восстановление стабильной версии

Стабильная версия отмечена тегом:

```bash
scanner-safe-telegram-v1
```

Проверить теги:

```bash
git tag --list
```

Посмотреть текущий коммит:

```bash
git log --oneline -5
```

---

## Текущий рекомендуемый следующий этап разработки

После стабильной безопасной Telegram/cron-сборки логичный следующий этап:

1. улучшить документацию запуска и восстановления;
2. добавить `.gitignore` для локальных отчётов, `.env`, `__pycache__`, `.session`;
3. расширить тестовые проверки safety gate;
4. улучшить устойчивость Telegram timeout/retry без риска дублей;
5. подготовить отдельный режим paper-trading без реальных ордеров;
6. только после этого обсуждать торговую логику, строго отдельно от безопасного аналитического режима.

---

## Важное предупреждение

Этот проект не является финансовой рекомендацией. Все сигналы являются аналитическими. Решение принимает только пользователь. Автоматическое исполнение ордеров в текущем безопасном pipeline отключено.
