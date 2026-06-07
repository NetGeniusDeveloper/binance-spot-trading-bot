# SAFE_RELEASES.md

# Safe Scanner Stable Releases

This document records stable points of the `binance-spot-trading-bot` project.

Purpose:

- quickly understand which tag represents which stable state;
- know which version can be used for rollback;
- keep short validation commands after updates;
- keep the safe analytical scanner pipeline separate from any trading bot behavior;
- preserve the history of stable stages: Telegram, cron, blocked risk, documentation, safety gate, release map, and English documentation.

The project works in safe analytical mode:

- Binance orders are not created;
- the trading bot is not started;
- automated trading is not enabled;
- Telegram notifications require explicit safety flags;
- the safety gate reads local reports and performs no dangerous actions;
- the blocked risk report explains why signals are blocked;
- documentation is now available in English for international users.

---

## 1. Current Stable Baseline

Current stable baseline before installing this English documentation pack:

```text
tag: scanner-safe-docs-map-v1
commit: a4a8e0c
branch: main
```

Description:

```text
Stable build with README.md Documentation map added.
```

Recommended new tag after installing, committing, and validating this English documentation pack:

```text
tag: scanner-safe-english-docs-v1
```

Expected safe result after validation:

```text
Safety gate OK: True
Review required: False
Orders enabled: False
Trading enabled: False
Binance orders created: False
```

---

## 2. Stable Tags

### scanner-safe-telegram-v1

Purpose:

```text
Stable safe Telegram pipeline with audit and safety gate.
```

This stage verifies:

- Telegram sender works only through safety flags;
- duplicate notifications are checked;
- Telegram audit records delivery status;
- the pipeline does not create orders;
- the pipeline does not start the trading bot.

Key files:

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

Purpose:

```text
Stable safe cron scanner pipeline.
```

Added:

- safe cron wrapper;
- cron log;
- safety gate check after run;
- cron documentation;
- `.gitignore` for secrets and runtime files.

Key files:

```text
run_daily_scanner_agent_cron_safe.sh
run_daily_scanner_agent_safe.sh
CRON_SETUP.md
README.md
.gitignore
```

Validation:

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate

bash -n run_daily_scanner_agent_cron_safe.sh
./run_daily_scanner_agent_cron_safe.sh

tail -n 200 reports/daily_scanner_agent_cron_safe.log
cat reports/scanner_agent_safety_gate_report.txt
```

Expected safe result:

```text
Gate status: safe
Safety gate OK: True
Review required: False
No orders were created
Trading bot was not started
```

---

### scanner-safe-risk-reports-v1

Purpose:

```text
Stable pipeline with blocked risk reports.
```

Added:

- separate report for signals blocked by risk filters;
- blocked risk report integration into daily runner;
- blocked risk report integration into full pipeline;
- human-readable blocking reasons;
- manager/user explanations.

Key files:

```text
scanner_agent_blocked_risk_report.py
scanner_agent_decision.py
scanner_agent_decision_report.py
scanner_agent_notification_report.py
scanner_agent_telegram_message_preview.py
run_daily_scanner_agent_safe.sh
run_full_scanner_agent_notification_pipeline_safe.sh
```

Validation:

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate

python -m py_compile scanner_agent_blocked_risk_report.py
python scanner_agent_blocked_risk_report.py

cat reports/scanner_agent_blocked_risk_report.txt
cat reports/scanner_agent_blocked_risk_report.json
```

Expected safe result:

```text
Safe to continue: True
Orders enabled: False
Trading enabled: False
Binance orders created: False
Telegram sending: False
```

If blocked signals exist, this is not an error. It is a safe state:

```text
Blocked risk means: do not use this signal for entry.
This report is only for analytical review.
No orders are created.
```

---

### scanner-safe-risk-docs-v1

Purpose:

```text
Stable documentation describing cron, safety gate, and blocked risk reports.
```

Added:

- updated README;
- updated CRON_SETUP;
- validation commands;
- stable tag descriptions;
- blocked risk report explanation;
- cron setup commands;
- safe manual validation commands.

Key files:

```text
README.md
CRON_SETUP.md
```

Documentation check:

```bash
cd /root/binance-spot-trading-bot

grep -n "scanner_agent_blocked_risk_report\|blocked risk\|Safety gate\|cron" README.md CRON_SETUP.md
```

---

### scanner-safe-gate-count-fix-v1

Purpose:

```text
Stable build with corrected total_decisions source priority in the safety gate.
```

Fixed:

- safety gate now correctly shows `Total decisions: 0` when the current pipeline ends with `no_decisions`;
- old `scanner_agent_telegram_sender_result.json` no longer overrides the current safety gate decision count;
- cron wrapper passes correctly when the final state is safe `no_decisions`.

Key file:

```text
scanner_agent_safety_gate_report.py
```

Validation:

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate

python -m py_compile scanner_agent_safety_gate_report.py
python scanner_agent_safety_gate_report.py

cat reports/scanner_agent_safety_gate_report.txt
cat reports/scanner_agent_safety_gate_report.json
```

Expected result for `no_decisions`:

```text
Gate status: safe
Pipeline final status: no_decisions
Safety gate OK: True
Review required: False
Total decisions: 0
Telegram message sent: False
```

---

### scanner-safe-release-notes-v1

Purpose:

```text
Stable build adding SAFE_RELEASES.md.
```

Added:

- release map file;
- stable tag explanations;
- rollback instructions;
- safety validation commands.

Key file:

```text
SAFE_RELEASES.md
```

---

### scanner-safe-release-notes-linked-v1

Purpose:

```text
Stable build linking SAFE_RELEASES.md from README.md.
```

Added:

- README link to `SAFE_RELEASES.md`;
- updated README stable release section;
- stable release map made easier to discover.

Key files:

```text
README.md
SAFE_RELEASES.md
```

---

### scanner-safe-release-map-v1

Purpose:

```text
Stable build with release map updated to the current stable release state.
```

Added/updated:

- `SAFE_RELEASES.md` current stable section updated;
- release map now reflects the README link stage;
- stable history is consolidated before English documentation work.

Key file:

```text
SAFE_RELEASES.md
```

Validation:

```bash
cd /root/binance-spot-trading-bot

grep -n "scanner-safe-release-map-v1\|9890b2c\|SAFE_RELEASES" SAFE_RELEASES.md README.md
git status
git tag --list
git log --oneline -5
```

---

### scanner-safe-english-docs-v1

Purpose:

```text
Recommended stable tag after replacing Russian documentation with English international documentation.
```

Expected additions:

- English `README.md`;
- English `CRON_SETUP.md`;
- English `SAFE_RELEASES.md`;
- international safety explanations;
- installation instructions for Android Download path;
- release map kept in English.

Key files:

```text
README.md
CRON_SETUP.md
SAFE_RELEASES.md
```

Suggested creation after successful validation:

```bash
git tag -a scanner-safe-english-docs-v1 -m "Stable safe scanner English documentation"
git push origin scanner-safe-english-docs-v1
```

---

## 3. Full Manual Validation Of Current Stable Build

Before any new change, run:

```bash
cd /root/binance-spot-trading-bot
source .venv/bin/activate

git status
git log --oneline -5
git tag --list
```

Expected:

```text
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

Compile Python files:

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

Check bash runners:

```bash
bash -n run_daily_scanner_agent_safe.sh
bash -n run_daily_scanner_agent_cron_safe.sh
bash -n run_full_scanner_agent_notification_pipeline_safe.sh
bash -n run_scanner_agent_telegram_sender_safe.sh
```

Run full safe daily pipeline:

```bash
./run_daily_scanner_agent_safe.sh

cat reports/scanner_agent_pipeline_summary.txt
cat reports/scanner_agent_safety_gate_report.txt
cat reports/scanner_agent_blocked_risk_report.txt
```

Run cron wrapper manually:

```bash
./run_daily_scanner_agent_cron_safe.sh

tail -n 200 reports/daily_scanner_agent_cron_safe.log
cat reports/scanner_agent_safety_gate_report.txt
cat reports/scanner_agent_blocked_risk_report.txt
```

---

## 4. Safe State Criteria

A build is safe if:

```text
Safety gate OK: True
Review required: False
Orders enabled: False
Trading enabled: False
Binance API used: False
Binance orders created: False
```

Safe statuses:

```text
safe
duplicate_blocked
no_decisions
no_signals
all_signals_blocked
```

Statuses requiring attention:

```text
review_required
telegram_delivery_unknown
```

Statuses that must not be ignored:

```text
blocked
failed
notification_failed
send_attempt_failed
unknown
```

---

## 5. Telegram Rule

Telegram sending is allowed only when both flags are enabled:

```bash
SCANNER_TELEGRAM_SEND_ENABLED=true
SCANNER_TELEGRAM_MANUAL_CONFIRM=true
```

Recommended unattended cron mode:

```bash
SCANNER_TELEGRAM_SEND_ENABLED=false
SCANNER_TELEGRAM_MANUAL_CONFIRM=false
```

If `total_decisions=0`, Telegram sender must be skipped:

```text
Telegram sender safe run skipped to avoid empty notification.
```

---

## 6. Blocked Risk Rule

`blocked_risk` is not a trading signal.

It means:

- entry is forbidden;
- the signal must not be used for a trade;
- the signal may be saved only as an analytical record;
- manual review may be performed;
- automatic orders are forbidden.

Safe example:

```text
Decision: blocked_risk
Action: do not use, blocked by risk filter
Recommended next step: Do not enter.
```

---

## 7. Quick Rollback To A Stable Version

List tags:

```bash
cd /root/binance-spot-trading-bot
git tag --list
```

Check a stable tag without changing main permanently:

```bash
git checkout scanner-safe-release-map-v1
```

Return to main:

```bash
git checkout main
git pull origin main
```

Create a test branch from a stable tag:

```bash
git checkout -b test-from-safe-release-map scanner-safe-release-map-v1
```

---

## 8. Git Workflow After Editing Release Notes

```bash
cd /root/binance-spot-trading-bot

git status
git add SAFE_RELEASES.md
git commit -m "Update safe scanner release notes"
git push origin main

git status
git log --oneline -5
```

Create a new stable tag after validation:

```bash
git tag -a scanner-safe-english-docs-v1 -m "Stable safe scanner English documentation"
git push origin scanner-safe-english-docs-v1

git tag --list
git log --oneline -5
```

---

## 9. Install This File From Android Download

```bash
cd /root/binance-spot-trading-bot

cp ./../../storage/emulated/0/Download/SAFE_RELEASES.md SAFE_RELEASES.md

git status
cat SAFE_RELEASES.md
```

After review:

```bash
git add SAFE_RELEASES.md
git commit -m "Update safe scanner release notes"
git push origin main
```

---

## 10. Recommended Development Baseline

Continue development from:

```text
scanner-safe-release-map-v1
```

After English documentation is committed and validated, continue from:

```text
scanner-safe-english-docs-v1
```

Reason:

- safe cron exists;
- safety documentation exists;
- blocked risk report exists;
- safety gate decision count is fixed;
- release map exists;
- English international documentation is available;
- GitHub is synchronized;
- working tree should be clean after final validation.

---

## 11. Next Reasonable Step

After installing this English documentation pack:

```text
Run full validation, commit README.md CRON_SETUP.md SAFE_RELEASES.md, push to GitHub, then create scanner-safe-english-docs-v1.
```

### scanner-safe-project-status-v1

Purpose:

```text
Stable build with README.md Documentation map added.
```

What was added:

- `PROJECT_STATUS.md`;
- short English status summary for the project;
- current stable tag reference;
- safe manual run commands;
- safe cron wrapper commands;
- safety criteria;
- Telegram notification rule;
- blocked risk rule;
- recommended Git workflow before future development.

Key files:

```text
PROJECT_STATUS.md
README.md
CRON_SETUP.md
SAFE_RELEASES.md
```

Verification:

```bash
cd /root/binance-spot-trading-bot

git status
cat PROJECT_STATUS.md
grep -n "scanner-safe-project-status-v1\|PROJECT_STATUS" PROJECT_STATUS.md SAFE_RELEASES.md README.md
git tag --list
git log --oneline -5
```

Expected result:

```text
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

Stable point:

```text
tag: scanner-safe-project-status-v1
commit: ea6a4b4
branch: main
```

---

## Recommended next stable map tag

After committing this SAFE_RELEASES.md update, use a new tag because
`scanner-safe-project-status-map-v1` may already exist before this file update.

Recommended new tag:

```text
scanner-safe-project-status-map-v2
```

Commands:

```bash
git tag -a scanner-safe-project-status-map-v2 -m "Stable release map with project status"
git push origin scanner-safe-project-status-map-v2
```

### scanner-safe-docs-map-v1

Purpose:

```text
Stable build with Documentation map added to README.md.
```

What was added:

- `Documentation map` section in `README.md`;
- short list of core documentation files;
- purpose of each documentation file;
- current stable map tag reference in README.

Key files:

```text
README.md
CRON_SETUP.md
SAFE_RELEASES.md
PROJECT_STATUS.md
```

Documentation map contents:

```text
README.md — main project overview and safe usage guide
CRON_SETUP.md — safe cron setup instructions
SAFE_RELEASES.md — stable releases, tags, and rollback map
PROJECT_STATUS.md — short current project status summary
```

Verification:

```bash
cd /root/binance-spot-trading-bot

git status
grep -n "Documentation map\|SAFE_RELEASES\|PROJECT_STATUS\|scanner-safe-project-status-map-v2" README.md
grep -n "scanner-safe-docs-map-v1\|a4a8e0c" SAFE_RELEASES.md
git tag --list
git log --oneline -5
```

Expected result:

```text
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

Stable point:

```text
tag: scanner-safe-docs-map-v1
commit: a4a8e0c
branch: main
```

---

## Recommended next stable map tag

After committing this SAFE_RELEASES.md update, create a new tag because
`scanner-safe-docs-map-v1` already points to the README Documentation map commit.

Recommended new tag for the updated release map:

```text
scanner-safe-docs-map-v2
```

Commands:

```bash
git tag -a scanner-safe-docs-map-v2 -m "Stable release map with README documentation map"
git push origin scanner-safe-docs-map-v2
```

