# Project Status

## Project

Repository: `binance-spot-trading-bot`

Current role of the project:

```text
Safe analytical crypto scanner pipeline
```

The project is currently used for market and public Telegram channel analysis only.

It must not:

- create Binance orders;
- start the trading bot;
- enable automatic trading;
- bypass Telegram safety flags;
- treat Telegram/social messages as direct trading entries.

---

## Current stable release

Current stable tag:

scanner-safe-dashboard-manager-only-mode-v1
scanner-safe-status-release-tool-v1
```

Stable commit:

```text
8dd11a0
```

Branch:

```text
main
```

Expected Git state:

```text
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

---

## Current safety baseline

The current baseline confirms:

- `DRY_RUN=True`;
- `WALLET_USAGE_PERCENT=0.0`;
- `SEND_TELEGRAM_MESSAGE=False`;
- Binance private keys are not required for safe DRY_RUN development;
- `.env` is ignored by Git;
- `.env.sample` documents the required safe environment variables;
- scanner Telegram delivery remains blocked unless both explicit safety flags are enabled;
- daily safe runner disables Telegram delivery by default even if local .env flags are enabled;
- ready_for_manual_review is treated as a safe manual-review state when orders and Telegram delivery remain disabled.
- cron safe wrapper accepts safe_manual_review as a successful safe completion when Safety gate OK is True.
- safe_status_release.sh can run a safe snapshot, verify safety gate, commit, push, and create an explicit tag.
- safe_status_release.sh supports --check-only and --with-docs conveyor mode for safer one-command project releases.

Tracked secret-like file review:

```text
credentials.py
```

`credentials.py` is allowed to remain tracked because it contains only environment-variable loading logic and does not store real keys.

Real secrets must remain only in local `.env` and must not be committed.

---

## Main documentation files

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
- `SAFE_RELEASES.md` — stable release map and rollback notes.
- `PROJECT_STATUS.md` — short current project status summary.

---

## Safe manual commands

Enter the project:

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate
```

Check Git state:

```bash
git status
git log --oneline -5
git tag --list
```

Run the safe daily scanner manually:

```bash
./run_daily_scanner_agent_safe.sh
```

Run the safe cron wrapper manually:

```bash
./run_daily_scanner_agent_cron_safe.sh
```

Check final reports:

```bash
cat reports/scanner_agent_pipeline_summary.txt
cat reports/scanner_agent_safety_gate_report.txt
cat reports/scanner_agent_blocked_risk_report.txt
```

---

## Safety criteria

The project is considered safe when the reports show:

```text
Safety gate OK: True
Review required: False
Orders enabled: False
Trading enabled: False
Binance API used: False
Binance orders created: False
```

Allowed safe states:

```text
safe
safe_manual_review
duplicate_blocked
no_decisions
no_signals
all_signals_blocked
```

States that require review:

```text
review_required
telegram_delivery_unknown
blocked
failed
notification_failed
send_attempt_failed
unknown
```

---

## Telegram notification rule

Real Telegram sending is allowed only when both flags are enabled:

```bash
SCANNER_TELEGRAM_SEND_ENABLED=true
SCANNER_TELEGRAM_MANUAL_CONFIRM=true
```

For unattended cron runs, the safe default is:

```bash
SCANNER_TELEGRAM_SEND_ENABLED=false
SCANNER_TELEGRAM_MANUAL_CONFIRM=false
```

The daily safe runner also forces Telegram delivery off by default. To allow analytical Telegram delivery for that runner, start it explicitly with:

```bash
ALLOW_TELEGRAM_SEND_IN_DAILY_SAFE_RUN=true ./run_daily_scanner_agent_safe.sh
```

---

## Blocked risk rule

`blocked_risk` is not a trading signal.

It means:

- do not enter a trade;
- do not create orders;
- keep the item only as an analytical record;
- review risk reasons manually.

---

## Recommended next development step

Continue development only from a clean Git state.

Current recommended stable base:

```text
scanner-safe-status-release-tool-v1
```

Before changing code or documentation:

```bash
cd /root/binance-spot-trading-bot

git status
git log --oneline -5
git tag --list
```

After any successful change:

```bash
git add .
git commit -m "Describe the change"
git push origin main
```

Create a new stable tag only after testing:

```bash
git tag -a <new-stable-tag> -m "Stable release description"
git push origin <new-stable-tag>
```

---

## Termux/Ubuntu main menu integration status

Status version: scanner-safe-project-status-main-menu-docs-v1

The local Termux/Ubuntu main menu integration is completed and documented.

Local menu file:

    /root/main-menu.sh

Recovery documentation:

    docs/TERMUX_MAIN_MENU_BINANCE.md

Current Binance menu title:

    BINANCE SPOT БОТ / БЕЗОПАСНЫЙ СКАНЕР

The Binance menu section includes:

    1) Быстрая безопасная панель
    2) Менеджерская сводка
    3) Короткий статус безопасности
    4) Ежедневный безопасный запуск
    5) Безопасная проверка релиза
    6) Полный безопасный конвейер
    7) Сводка отчётов
    13) Показать безопасные команды запуска

Safety status:

    DRY_RUN=True
    SEND_TELEGRAM_MESSAGE=False
    WALLET_USAGE_PERCENT=0.0
    Orders disabled
    Live trading disabled
    Telegram auto-send disabled

The menu is intended only for safe analytical work. It must not be used to enable live trading or create real Binance orders without a separate audit.

Related stable tags:

    scanner-safe-main-menu-docs-v1
    scanner-safe-project-status-main-menu-docs-v1

---

## Daily manager brief README workflow status

Status version: scanner-safe-readme-manager-brief-daily-use-v1

The README now contains a daily manual workflow for using the manager brief safely.

README section:

    ## Как пользоваться менеджерской сводкой каждый день

Main file:

    README.md

The documented daily workflow explains how to:

    1) open the Termux/Ubuntu main menu;
    2) enter the Binance safe scanner section;
    3) check the short safety status first;
    4) open the manager brief;
    5) treat blocked pairs as no-entry decisions;
    6) review manual cards only as analytical material;
    7) open report summaries when needed.

Safety reminder:

    The manager brief is not a trading signal.
    It does not allow live trading.
    It does not allow real Binance orders.
    It does not allow automatic Telegram sending.
    It is only a manual analytical report.

Related stable tags:

    scanner-safe-readme-manager-brief-daily-use-v1
    scanner-safe-project-status-main-menu-docs-v1
    scanner-safe-main-menu-docs-v1

---

## Manager daily command status

Status version: scanner-safe-manager-daily-docs-menu-v1

The project now includes a dedicated daily manager command:

    manager_daily.sh

The command provides a one-step safe view for:

    short safety status;
    manager brief;
    no-orders reminder;
    no-live-trading reminder;
    no-Binance-private-API reminder;
    no-Telegram-auto-send reminder.

Daily command:

    ./manager_daily.sh

Safety rule:

    manager_daily.sh is analytical only.
    It does not create Binance orders.
    It does not enable live trading.
    It does not call Binance private API.
    It does not send Telegram messages.

Related stable tags:

    scanner-safe-manager-daily-script-v1
    scanner-safe-manager-daily-docs-menu-v1
    scanner-safe-readme-manager-brief-daily-use-v1
