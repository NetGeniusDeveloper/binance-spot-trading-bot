# AI Pair Discovery Roadmap

Status version: scanner-safe-ai-pair-discovery-roadmap-v1

Документ описывает будущую безопасную архитектуру поиска лучших торговых пар для Binance Spot Trading Bot.

Этот документ НЕ включает live trading.
Этот документ НЕ создаёт реальные ордера.
Этот документ НЕ включает Binance private API.
Этот документ НЕ включает автоматическую отправку Telegram.

Текущая база безопасности:

- DRY_RUN=True
- SEND_TELEGRAM_MESSAGE=False
- WALLET_USAGE_PERCENT=0.0
- Orders disabled
- Live trading disabled
- Binance private API disabled for discovery
- Telegram auto-send disabled

---

## Главный принцип

Неправильная схема:

AI нашёл пару -> бот сразу покупает

Правильная безопасная схема:

AI нашёл кандидатов
-> скоринг оценил пары
-> risk filter заблокировал опасные варианты
-> backtest проверил правила
-> manager brief показал человеку результат
-> paper trading тестируется отдельно
-> live trading только после отдельного аудита

AI не должен обходить risk manager.

---

## Безопасная цепочка развития

1. Автоматизированный процесс поиска и составления списка торговых пар.
2. Фильтр ликвидности.
3. Фильтр волатильности.
4. Технический скоринг.
5. Новостной/социальный риск.
6. AI-объяснение.
7. Risk manager.
8. Backtest.
9. Manager brief.
10. Paper trading.
11. Live trading только после отдельного аудита.

---

## 1. Поиск торговых пар

Будущий модуль должен автоматически собирать список кандидатов, а не торговать только одной вручную назначенной монетой.

Источники только безопасные:

- Binance public market data
- exchangeInfo
- 24h ticker statistics
- volume snapshots
- локальный allowlist/watchlist

Примеры стартовых пар:

- BTCUSDT
- ETHUSDT
- BNBUSDT
- SOLUSDT
- XRPUSDT
- ADAUSDT
- DOGEUSDT
- AVAXUSDT
- LINKUSDT

Правило безопасности:

Поиск пар использует только публичные данные и не создаёт ордера.

---

## 2. Фильтр ликвидности

Фильтр должен отсеивать слабые пары.

Проверки:

- минимальный 24h quote volume
- минимальное число сделок
- допустимый spread
- достаточно свечей
- нет провалов ликвидности

Правило безопасности:

Низкая ликвидность блокирует вход. AI не может снять этот блок.

---

## 3. Фильтр волатильности

Фильтр должен понимать, пара слишком спокойная, нормальная или опасно резкая.

Проверки:

- ATR
- диапазон свечей
- резкие pump/dump свечи
- отклонение от средней волатильности

Бакеты:

- too_low_volatility
- normal_volatility
- high_volatility
- extreme_volatility

Правило безопасности:

Extreme volatility блокирует вход. High volatility требует ручной проверки.

---

## 4. Технический скоринг

Скоринг оценивает пару по измеримым признакам.

Возможные индикаторы:

- RSI
- SMA / EMA trend
- MACD
- volume confirmation
- breakout/retest
- support/resistance distance
- trend strength

Важно:

Технический score не является разрешением на сделку.

---

## 5. Новостной и социальный риск

Система должна учитывать риск хайпа, пампа и плохих новостей.

Риски:

- pump hype
- FOMO
- fake breakout
- negative news
- token unlock
- regulatory issue
- suspicious social spike
- weak signal source

Правило безопасности:

Опасный новостной/социальный риск блокирует вход.

---

## 6. AI-объяснение

AI может объяснять, почему пара интересна или опасна.

Разрешённые выводы AI:

- DO_NOT_ENTER
- WATCH_ONLY
- MANUAL_REVIEW_ONLY
- ANALYTICAL_CANDIDATE_ONLY

Запрещённые выводы AI:

- BUY_NOW
- SELL_NOW
- PLACE_ORDER
- ENABLE_LIVE_TRADING
- IGNORE_RISK_MANAGER

AI объясняет и ранжирует, но не разрешает реальные сделки.

---

## 7. Risk manager

Каждый кандидат обязан пройти risk manager.

Проверки:

- DRY_RUN
- лимиты
- confidence threshold
- spread
- liquidity
- volatility
- risk flags
- market confirmation
- journal state

Правило безопасности:

Блок risk manager является финальным.

---

## 8. Backtest

Каждое новое правило должно проверяться через backtest.

Backtest должен подтверждать:

- нет реальных ордеров
- нет Binance private API
- нет live trading
- нет Telegram auto-send
- есть воспроизводимый отчёт
- есть pass/fail статус

Если backtest не пройден, правило не двигается дальше.

---

## 9. Manager brief

Manager brief показывает человеку:

- лучшие пары-кандидаты
- заблокированные пары
- watchlist
- причины
- risk flags
- недостающие подтверждения
- следующий безопасный шаг

Manager brief не является торговым сигналом.

---

## 10. Paper trading

Paper trading возможен только после стабильного discovery, scoring, risk filter и backtest.

Требования:

- DRY_RUN остаётся включён
- сделки только симулируются
- журнал пишет решения
- реальные ордера не создаются
- отчёты проходят проверку

---

## 11. Live trading

Live trading не входит в текущий этап.

Перед live trading нужны:

- стабильный discovery
- стабильный scoring
- стабильный risk manager
- стабильный journal
- стабильные backtest отчёты
- стабильный paper trading
- план rollback
- проверка секретов
- отдельный аудит
- явное подтверждение пользователя

---

## Возможные будущие модули

- pair_universe_scanner.py
- pair_liquidity_filter.py
- pair_volatility_filter.py
- pair_technical_scoring.py
- pair_news_social_risk.py
- ai_pair_analyst.py
- pair_discovery_pipeline.py
- pair_discovery_report.py
- tests/pair_discovery_scenarios.json
- reports/pair_discovery_candidates.json
- reports/pair_discovery_report.txt

---

## Текущий статус

Это документация архитектуры.

Торговая логика не меняется.
Автоматическая торговля не включается.
Реальные ордера не создаются.

Current stable baseline:

scanner-safe-manager-daily-next-step-v1

Proposed roadmap version:

scanner-safe-ai-pair-discovery-roadmap-v1
