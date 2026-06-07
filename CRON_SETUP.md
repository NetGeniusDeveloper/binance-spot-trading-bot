# Безопасная настройка ежедневного запуска сканера через cron

Этот документ объясняет, как автоматически запускать `crypto scanner agent` через `cron` в безопасном аналитическом режиме.

Cron-wrapper не создаёт Binance-ордера, не запускает торгового бота и не включает автоматическую торговлю. Он только запускает аналитический scanner pipeline и проверяет финальный safety gate.

---

## 1. Текущая стабильная версия

Стабильный тег:

```bash
scanner-safe-risk-reports-v1
```

Предыдущие стабильные теги:

```bash
scanner-safe-cron-v1
scanner-safe-telegram-v1
```

Текущий безопасный cron-wrapper:

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

Safety gate report:

```bash
reports/scanner_agent_safety_gate_report.json
reports/scanner_agent_safety_gate_report.txt
```

Blocked risk report:

```bash
reports/scanner_agent_blocked_risk_report.json
reports/scanner_agent_blocked_risk_report.txt
```

Cron log:

```bash
reports/daily_scanner_agent_cron_safe.log
```

---

## 2. Safety model

Cron-wrapper запускает ежедневный scanner pipeline, затем читает:

```bash
reports/scanner_agent_safety_gate_report.json
```

Wrapper считает эти состояния безопасными:

```text
safe
duplicate_blocked
```

Wrapper допускает это состояние как неопасное, но требующее ручной проверки:

```text
review_required
```

Wrapper останавливается на небезопасных или блокирующих состояниях:

```text
failed
blocked
unknown
```

---

## 3. Важные правила безопасности

Проект должен оставаться только аналитическим.

Cron-wrapper не должен:

- создавать Binance-ордера;
- запускать торгового бота;
- включать торговлю;
- обходить Telegram safety-флаги;
- автоматически менять конфигурацию scanner-каналов;
- удалять историю SQLite без отдельной ручной команды;
- отправлять повторные уведомления в обход duplicate-protection.

Telegram-отправка управляется только environment-флагами и безопасной логикой sender-а.

---

## 4. Рабочая директория проекта

Wrapper использует фиксированный путь:

```bash
/root/binance-spot-trading-bot
```

Проверьте, что проект действительно там:

```bash
cd /root/binance-spot-trading-bot
pwd
git status
git log --oneline -5
```

Ожидаемый результат:

```text
/root/binance-spot-trading-bot
nothing to commit, working tree clean
```

---

## 5. Активация окружения

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate
```

Проверка Python:

```bash
python --version
```

---

## 6. Проверка wrapper-а вручную перед cron

Перед добавлением в cron обязательно выполните ручную проверку:

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate

bash -n run_daily_scanner_agent_cron_safe.sh
./run_daily_scanner_agent_cron_safe.sh
```

Проверьте cron-лог:

```bash
tail -n 160 reports/daily_scanner_agent_cron_safe.log
```

Проверьте safety gate:

```bash
cat reports/scanner_agent_safety_gate_report.txt
cat reports/scanner_agent_safety_gate_report.json
```

Успешный результат должен содержать:

```text
Gate status: safe
Safety gate OK: True
Review required: False
```

Безопасный duplicate-результат может содержать:

```text
Gate status: duplicate_blocked
Safety gate OK: True
```

Состояние ручной проверки может содержать:

```text
Gate status: review_required
Review required: True
```

В этом случае нужно вручную проверить Telegram-чат перед повторным запуском sender-а.

---

## 7. Environment configuration

Откройте `.env`:

```bash
cd /root/binance-spot-trading-bot
nano .env
```

Telegram Bot sending зависит от project credentials и safety-флагов.

Пример `.env`:

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

Рекомендуемые безопасные значения по умолчанию для автоматического cron без присмотра:

```bash
SCANNER_TELEGRAM_SEND_ENABLED=false
SCANNER_TELEGRAM_MANUAL_CONFIRM=false
```

Для контролируемой аналитической Telegram-отправки только после ручного решения:

```bash
SCANNER_TELEGRAM_SEND_ENABLED=true
SCANNER_TELEGRAM_MANUAL_CONFIRM=true
```

Не включайте никакие флаги исполнения ордеров.

---

## 8. Blocked risk report в cron/pipeline

В безопасный ежедневный pipeline добавлен отдельный отчёт по сигналам, которые были заблокированы риск-фильтром.

Файлы:

```bash
reports/scanner_agent_blocked_risk_report.txt
reports/scanner_agent_blocked_risk_report.json
```

Скрипт:

```bash
python scanner_agent_blocked_risk_report.py
```

Отчёт помогает быстро понять, почему scanner agent не разрешил использовать сигнал даже для ручного рассмотрения.

Он показывает:

- пару, например `BTCUSDT` или `SOLUSDT`;
- source group;
- risk level;
- action hint;
- final score;
- market score;
- telegram score;
- risk adjustment;
- risk flags;
- market confirmation;
- retest status;
- human block reasons;
- risk explanation;
- manager note;
- recommended next step.

Ручной запуск:

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate

python -m py_compile scanner_agent_blocked_risk_report.py
python scanner_agent_blocked_risk_report.py

cat reports/scanner_agent_blocked_risk_report.txt
cat reports/scanner_agent_blocked_risk_report.json
```

В ежедневном safe-run отчёт запускается автоматически:

```bash
./run_daily_scanner_agent_safe.sh
```

В полном pipeline отчёт также встроен:

```bash
./run_full_scanner_agent_notification_pipeline_safe.sh
```

### Безопасность blocked risk отчёта

Отчёт является только аналитическим.

Он не должен:

- создавать ордера;
- запускать торгового бота;
- отправлять Telegram-сообщения;
- вызывать Binance API;
- изменять конфигурацию каналов.

Он только читает:

```bash
reports/scanner_agent_decision.json
```

и создаёт:

```bash
reports/scanner_agent_blocked_risk_report.txt
reports/scanner_agent_blocked_risk_report.json
```

Для cron это означает: даже если все найденные сигналы заблокированы риск-фильтром, это безопасное состояние. Такие сигналы остаются только в аналитическом отчёте.

---

## 9. Установка cron-задания

Откройте crontab:

```bash
crontab -e
```

Пример: запуск один раз в день в 09:00 по времени сервера:

```cron
0 9 * * * /root/binance-spot-trading-bot/run_daily_scanner_agent_cron_safe.sh
```

Пример: запуск каждые 6 часов:

```cron
0 */6 * * * /root/binance-spot-trading-bot/run_daily_scanner_agent_cron_safe.sh
```

Рекомендуемый первый вариант:

```cron
0 9 * * * /root/binance-spot-trading-bot/run_daily_scanner_agent_cron_safe.sh
```

---

## 10. Проверка установленных cron-заданий

```bash
crontab -l
```

Ожидаемый пример:

```cron
0 9 * * * /root/binance-spot-trading-bot/run_daily_scanner_agent_cron_safe.sh
```

---

## 11. Проверка результата cron

После планового запуска:

```bash
cd /root/binance-spot-trading-bot

tail -n 200 reports/daily_scanner_agent_cron_safe.log
cat reports/scanner_agent_safety_gate_report.txt
cat reports/scanner_agent_pipeline_summary.txt
cat reports/scanner_agent_blocked_risk_report.txt
cat reports/scanner_agent_telegram_sender_audit_report.txt
```

Быстрая JSON-проверка safety gate:

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

Быстрая JSON-проверка blocked risk:

```bash
python - <<'PY'
import json
from pathlib import Path

path = Path("reports/scanner_agent_blocked_risk_report.json")
payload = json.loads(path.read_text(encoding="utf-8"))

print("Safe to continue:", payload.get("safe_to_continue"))
print("Blocked count:", payload.get("blocked_count"))
print("Risk levels:", payload.get("summary_by_risk_level"))
print("Risk flags:", payload.get("summary_by_risk_flag"))
print("Blockers:", ", ".join(payload.get("blockers", [])) or "none")
print("Warnings:", ", ".join(payload.get("warnings", [])) or "none")
PY
```

---

## 12. Отключение cron-задания

Откройте crontab:

```bash
crontab -e
```

Закомментируйте строку:

```cron
# 0 9 * * * /root/binance-spot-trading-bot/run_daily_scanner_agent_cron_safe.sh
```

Или удалите её полностью.

Проверка:

```bash
crontab -l
```

---

## 13. Emergency safe stop

Отключите Telegram-отправку в `.env`:

```bash
SCANNER_TELEGRAM_SEND_ENABLED=false
SCANNER_TELEGRAM_MANUAL_CONFIRM=false
```

Потом проверьте:

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate

./run_daily_scanner_agent_cron_safe.sh
tail -n 160 reports/daily_scanner_agent_cron_safe.log
cat reports/scanner_agent_safety_gate_report.txt
```

---

## 14. Полная ручная проверка перед включением cron

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

Можно включать cron, если safety gate показывает:

```text
Safety gate OK: True
Blockers: none
```

---

## 15. Git workflow после изменения cron-документации

Проверить статус:

```bash
cd /root/binance-spot-trading-bot
git status
```

Добавить документацию:

```bash
git add README.md CRON_SETUP.md
```

Коммит:

```bash
git commit -m "Update scanner cron and blocked risk documentation"
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

Ожидаемый финальный статус:

```text
nothing to commit, working tree clean
```

---

## 16. Установка готовых файлов из Android Download

Если готовые файлы скачаны в папку Android Download:

```bash
./../../storage/emulated/0/Download/
```

замените документацию так:

```bash
cd /root/binance-spot-trading-bot

cp README.md README.md.before_update.backup
cp CRON_SETUP.md CRON_SETUP.md.before_update.backup

mv ./../../storage/emulated/0/Download/README.md README.md
mv ./../../storage/emulated/0/Download/CRON_SETUP.md CRON_SETUP.md

git status
```

Проверка содержимого:

```bash
grep -n "blocked risk\|scanner_agent_blocked_risk_report\|Safety gate\|cron" README.md CRON_SETUP.md
```

Проверка runner-ов:

```bash
bash -n run_daily_scanner_agent_safe.sh
bash -n run_full_scanner_agent_notification_pipeline_safe.sh
bash -n run_daily_scanner_agent_cron_safe.sh
```

Коммит:

```bash
git add README.md CRON_SETUP.md
git commit -m "Update docs for blocked risk scanner reports"
git push origin main
```

Финальная проверка:

```bash
git status
git log --oneline -5
```

---

## 17. Итог

Cron можно использовать только для безопасного аналитического pipeline.

Главные признаки безопасного результата:

```text
Safe pipeline: True
Safety gate OK: True
Review required: False
Orders enabled: False
Trading enabled: False
Binance orders created: False
Blockers: none
```

Если есть `blocked_risk`, это не ошибка. Это безопасное состояние, означающее: **сигнал заблокирован и не должен использоваться для входа**.
