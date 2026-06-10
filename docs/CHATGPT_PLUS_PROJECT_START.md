# ChatGPT Plus Project Start Guide

Status version: scanner-safe-chatgpt-project-start-v1

This file is the entry point for a new ChatGPT Plus chat.

Project: Binance Spot Trading Bot
Repository: https://github.com/NetGeniusDeveloper/binance-spot-trading-bot
Default path: /root/binance-spot-trading-bot

## Main rule

Do not work from old memory.
Always inspect the current repository first.

Required first command:

    cd /root/binance-spot-trading-bot
    git status
    git branch --show-current
    git log --oneline -5
    find . -maxdepth 3 -type f | sort

## Current mode

The project is a safe analytical crypto scanner and Binance Spot bot laboratory.

Safety baseline:

    DRY_RUN=True
    SEND_TELEGRAM_MESSAGE=False
    WALLET_USAGE_PERCENT=0.0
    no real orders
    no live trading
    no Binance private API for discovery
    no automatic Telegram sending

## Read first

A new chat should read:

    README.md
    PROJECT_STATUS.md
    SAFE_RELEASES.md
    docs/AI_PAIR_DISCOVERY_ROADMAP.md
    docs/TERMUX_MAIN_MENU_BINANCE.md
    docs/CHATGPT_PLUS_PROJECT_START.md
    manager_daily.sh

## Safe daily commands

    ./manager_daily.sh
    ./safe_status_release.sh --check-only

## Forbidden actions

A new chat must not:

    enable live trading
    create real Binance orders
    ask for real API keys unnecessarily
    remove DRY_RUN without explicit audit
    bypass risk manager
    treat AI output as permission to buy
    commit .env, secrets, databases, logs, caches, or runtime artifacts

## Future direction

Future automation must follow:


    pair discovery
    -> liquidity filter
    -> volatility filter
    -> technical scoring
    -> news/social risk
    -> AI explanation
    -> risk manager
    -> backtest
    -> manager brief
    -> paper trading
    -> live trading only after separate audit

Current stable roadmap baseline:

    scanner-safe-ai-pair-discovery-roadmap-v1

Current guide version:

    scanner-safe-chatgpt-project-start-v1
