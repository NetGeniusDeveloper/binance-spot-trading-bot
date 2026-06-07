# Безопасная настройка ежедневного запуска сканера через cron

Этот файл относится к проекту:

```bash
/root/binance-spot-trading-bot
```

Репозиторий проекта:

```text
https://github.com/NetGeniusDeveloper/binance-spot-trading-bot
```

Документ объясняет, как автоматически запускать crypto scanner agent через `cron` в безопасном аналитическом режиме.

Cron-обёртка **не создаёт ордера Binance**, **не запускает торгового бота**, **не включает автоматическую торговлю**. Она только запускает аналитический pipeline сканера и проверяет итоговый отчёт safety gate.

---

## 1. Текущая стабильная версия

Стабильный тег:

```bash
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

Отчёт safety gate:

```bash
reports/scanner_agent_safety_gate_report.json
reports/scanner_agent_safety_gate_report.txt
```

Cron-лог:

```bash
reports/daily_scanner_agent_cron_safe.log
```

---

## 2. Модель безопасности

Cron-wrapper запускает ежедневный pipeline сканера, затем читает:

```bash
reports/scanner_agent_safety_gate_report.json
```

Wrapper считает безопасными состояния:

```text
safe
duplicate_blocked
```

Wrapper допускает это состояние как неопасное, но требующее ручной проверки:

```text
review_required
```

Wrapper завершится ошибкой при небезопасных или блокирующих состояниях, например:

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
- автоматически менять конфигурацию каналов сканера.

Telegram-отправка управляется только переменными окружения и безопасной логикой sender-а.

---

## 4. Требуемая директория проекта

Wrapper сейчас использует фиксированный путь:

```bash
/root/binance-spot-trading-bot
```

Проверьте, что проект действительно находится там:

```bash
cd /root/binance-spot-trading-bot
pwd
git status
```

Ожидаемый результат:

```text
/root/binance-spot-trading-bot
nothing to commit, working tree clean
```

---

## 5. Как скачать и установить этот файл в проект

Если файл `CRON_SETUP.md` скачан в папку загрузок Android/Termux, скопируйте его в корень проекта:

```bash
cd /root/binance-spot-trading-bot
cp ~/storage/downloads/CRON_SETUP.md ./CRON_SETUP.md
```

Если файл оказался в другой папке, найдите его:

```bash
find ~/storage/downloads -name "CRON_SETUP.md"
```

Затем скопируйте найденный файл:

```bash
cp /путь/к/CRON_SETUP.md /root/binance-spot-trading-bot/CRON_SETUP.md
```

Проверьте:

```bash
cd /root/binance-spot-trading-bot
ls -l CRON_SETUP.md
head -n 20 CRON_SETUP.md
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

Безопасный дубль уведомления может содержать:

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

## 7. Настройка окружения

Откройте `.env`:

```bash
cd /root/binance-spot-trading-bot
nano .env
```

Telegram Bot отправка зависит от credentials проекта и safety-флагов.

Текущий `.env.sample` содержит:

```bash
BINANCE_API_KEY=""
BINANCE_SECRET_KEY=""

TELEGRAM_API_KEY=""
TELEGRAM_USER_ID=""

TELEGRAM_API_ID=""
TELEGRAM_API_HASH=""
TELEGRAM_SESSION_NAME="crypto_scanner_session"

TELEGRAM_ALERT_CHAT_ID=""
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

## 8. Установка cron-задания

Откройте crontab:

```bash
crontab -e
```

Пример запуска один раз в день в 09:00 серверного времени:

```cron
0 9 * * * /root/binance-spot-trading-bot/run_daily_scanner_agent_cron_safe.sh
```

Пример запуска каждые 6 часов:

```cron
0 */6 * * * /root/binance-spot-trading-bot/run_daily_scanner_agent_cron_safe.sh
```

Рекомендуемый первый вариант настройки:

```cron
0 9 * * * /root/binance-spot-trading-bot/run_daily_scanner_agent_cron_safe.sh
```

---

## 9. Проверка установленных cron-заданий

```bash
crontab -l
```

Ожидаемый пример:

```cron
0 9 * * * /root/binance-spot-trading-bot/run_daily_scanner_agent_cron_safe.sh
```

---

## 10. Проверка результата cron

После запланированного выполнения:

```bash
cd /root/binance-spot-trading-bot

tail -n 200 reports/daily_scanner_agent_cron_safe.log
cat reports/scanner_agent_safety_gate_report.txt
cat reports/scanner_agent_pipeline_summary.txt
cat reports/scanner_agent_telegram_sender_audit_report.txt
```

Быстрая JSON-проверка:

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

## 11. Отключение cron-задания

Откройте crontab:

```bash
crontab -e
```

Закомментируйте строку:

```cron
# 0 9 * * * /root/binance-spot-trading-bot/run_daily_scanner_agent_cron_safe.sh
```

Или полностью удалите её.

Проверьте:

```bash
crontab -l
```

---

## 12. Экстренная безопасная остановка

Отключите Telegram-отправку в `.env`:

```bash
SCANNER_TELEGRAM_SEND_ENABLED=false
SCANNER_TELEGRAM_MANUAL_CONFIRM=false
```

Затем проверьте:

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate
./run_daily_scanner_agent_cron_safe.sh
tail -n 160 reports/daily_scanner_agent_cron_safe.log
```

---

## 13. Git workflow после добавления документации

Проверьте статус:

```bash
cd /root/binance-spot-trading-bot
git status
```

Добавьте документацию:

```bash
git add CRON_SETUP.md
git commit -m "Add safe scanner cron setup guide"
git push origin main
```

Проверьте итоговое состояние:

```bash
git status
git log --oneline -5
```

Ожидаемый итог:

```text
nothing to commit, working tree clean
```

---

## 14. Быстрый чек-лист

Перед включением cron:

```bash
cd /root/binance-spot-trading-bot
git status
source .venv/bin/activate
bash -n run_daily_scanner_agent_cron_safe.sh
./run_daily_scanner_agent_cron_safe.sh
cat reports/scanner_agent_safety_gate_report.txt
```

Можно включать cron, если safety gate показывает:

```text
Safety gate OK: True
```

Для режима без автоматической Telegram-отправки держите в `.env`:

```bash
SCANNER_TELEGRAM_SEND_ENABLED=false
SCANNER_TELEGRAM_MANUAL_CONFIRM=false
```

Для контролируемой аналитической отправки:

```bash
SCANNER_TELEGRAM_SEND_ENABLED=true
SCANNER_TELEGRAM_MANUAL_CONFIRM=true
```

Автоордера и запуск торгового бота должны оставаться отключёнными.
