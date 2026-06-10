# Commercial License

Status version: scanner-safe-commercial-release-docs-v1

This is a draft commercial license for Binance Spot Trading Bot.
It is not legal advice. Before paid distribution, review it with a qualified lawyer.

## 1. License grant

The buyer receives a limited, non-exclusive, non-transferable license to use one copy of the software package.

## 2. Restrictions

The buyer may not:
    resell the software;
    publish the source code;
    share the package with third parties;
    remove safety warnings;
    present the tool as guaranteed-profit software;
    use the software to bypass exchange rules or local law.

## 3. Analytical-only default

The software is distributed as an analytical tool.
Default safe mode must remain:
    DRY_RUN=True
    SEND_TELEGRAM_MESSAGE=False
    WALLET_USAGE_PERCENT=0.0
    no real orders
    no live trading

## 4. No financial advice

The software does not provide financial advice.
All trading decisions are the user's responsibility.
Past tests, reports, or backtests do not guarantee future results.

## 5. Live trading

Live trading is not included in the default commercial release.
Any live trading mode requires a separate audit, explicit manual configuration, and user responsibility.

## 6. Secrets and API keys

The seller does not provide Binance API keys.
The buyer must protect their own API keys.
The buyer must not commit .env files, secrets, databases, logs, caches, or runtime reports.

## 7. No warranty

The software is provided as is.
No profit, uptime, accuracy, or loss-prevention guarantee is provided.

## 8. Termination

The license may be terminated if the buyer redistributes the software, publishes private code, abuses license access, or violates the restrictions.

## 9. Acceptance

By installing or using the software, the buyer accepts this commercial license draft and the analytical-only safety rules.
