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

```text
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
