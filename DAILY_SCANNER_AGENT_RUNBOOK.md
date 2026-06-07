Понял. У вас проблема не в коде, а в том, что большой текст из сообщения копируется в Termux криво: строки ломаются, появляются обрезки, и терминал зависает в режиме >.

Сейчас сделаем проще: не будем вставлять большой документ через блок. Создайте файл через nano.

Сначала выйдите из зависшего режима:

Нажмите:

Ctrl + C

Потом выполните:

cd ~/binance-spot-trading-bot

rm -f DAILY_SCANNER_AGENT_RUNBOOK.md

nano DAILY_SCANNER_AGENT_RUNBOOK.md

Откроется редактор. Вставьте туда обычный текст:

Daily Scanner Agent Runbook

Назначение

run_daily_scanner_agent_safe.sh запускает полный безопасный аналитический pipeline Crypto Scanner Agent.

Pipeline выполняет:

1. Читает ограниченные публичные Telegram-сообщения из настроенных каналов.


2. Анализирует сообщения локальными правилами.


3. Получает публичные рыночные метрики Binance.


4. Формирует scanner_agent_export.json.


5. Формирует scanner_agent_decision.json.


6. Создаёт Telegram preview.


7. Проверяет dry-run отправки.


8. Отправляет Telegram-уведомление только если включены оба ручных флага.


9. Создаёт итоговый summary.



Безопасность

Pipeline не создаёт ордера.

Pipeline не запускает торгового бота.

Pipeline не использует приватные Binance-ордера.

Telegram-отправка защищена двумя флагами:

SCANNER_TELEGRAM_SEND_ENABLED=true

SCANNER_TELEGRAM_MANUAL_CONFIRM=true

Если хотя бы один флаг выключен, сообщение в Telegram не отправляется.

Если total_decisions=0, Telegram sender пропускается.

Ежедневный запуск

Команда запуска:

./run_daily_scanner_agent_safe.sh

Основные отчёты

reports/scanner_agent_pipeline_summary.txt

reports/scanner_agent_pipeline_summary.json

reports/daily_scanner_agent_pipeline.log

reports/scanner_agent_decision.json

reports/scanner_agent_telegram_message_preview.txt

Как читать итог

final_status может быть:

all_signals_blocked — все сигналы заблокированы или пропущены.

no_decisions — сигналы были, но решений нет.

ready_for_manual_review — есть решения, нужно ручное рассмотрение.

notification_sent — аналитическое Telegram-уведомление отправлено.

notification_failed — была попытка отправки, но она не удалась.

Правило

Даже если Telegram-уведомление отправлено, это не торговый сигнал и не команда на вход.

Решение принимает только пользователь.

Автоордера отключены.



