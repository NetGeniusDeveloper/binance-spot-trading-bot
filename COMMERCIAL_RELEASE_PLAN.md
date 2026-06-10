# Commercial Release Plan

Status version: scanner-safe-commercial-release-docs-v1

This document describes how to prepare Binance Spot Trading Bot for paid distribution.

Current commercial baseline candidate:

    scanner-safe-chatgpt-start-links-v1

Important: this product must be sold as a safe analytical scanner, not as a profit-guaranteeing trading bot.

## Product positioning

Sell:
    safe crypto analytics;
    scanner reports;
    risk manager workflow;
    manager brief;
    backtest laboratory;
    AI-assisted research roadmap.

Do not sell:
    guaranteed profit;
    automatic income;
    live trading promises;
    ready-to-use real-money trading without audit.

## Repository policy

Recommended action:
    make GitHub repository private after final safe baseline;
    keep source code closed;
    distribute stable packages only to paid users;
    do not publish .env, secrets, databases, logs, caches, or runtime reports.

## Paid access models

Basic:
    stable ZIP package;
    install guide;
    safe daily commands.

Pro:
    stable package updates;
    private support channel;
    AI pair discovery roadmap access.

Developer / Partner:
    private GitHub access;
    source code access;
    setup consultation;
    live trading still requires separate audit.

## Sales platforms

Possible platforms:
    Lemon Squeezy for digital products, license keys, subscriptions, and webhooks;
    Gumroad for simple digital downloads and license keys;
    Boosty or Telegram community for manual paid access;
    own website later for automated checkout and license verification.

## Delivery flow

1. Buyer pays on selected platform.
2. Buyer receives ZIP package or private download link.
3. Buyer receives license key or order ID.
4. Buyer reads docs/CHATGPT_PLUS_PROJECT_START.md.
5. Buyer runs only safe startup commands.
6. Buyer confirms DRY_RUN=True and live trading disabled.

## Future license automation

Future files may include:
    license_check.py
    LICENSE_KEY.example
    install_new_device_safe.sh

License checks should not enable trading.
License checks should only control access to paid features or updates.

## Commercial release checklist

Before closing the repository:
    run ./safe_status_release.sh --check-only;
    verify README.md links;
    verify PROJECT_STATUS.md;
    verify docs/CHATGPT_PLUS_PROJECT_START.md;
    verify no secrets are committed;
    create final commercial baseline tag;
    then make GitHub repository private.

## Safety rule

Commercial release does not change trading safety.
Live trading remains disabled.
Real Binance orders remain forbidden without separate audit.
