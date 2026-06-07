import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from credentials import TELEGRAM_ALERT_CHAT_ID


INPUT_PATH = Path("reports") / "scanner_agent_decision.json"
NOTIFICATION_REPORT_PATH = Path("reports") / "scanner_agent_notification_report.txt"
OUTPUT_PATH = Path("reports") / "scanner_agent_telegram_message_preview.txt"

MAX_TELEGRAM_MESSAGE_LENGTH = 3500

DECISION_TITLES = {
    "candidate": "🔥 СИЛЬНЫЕ АНАЛИТИЧЕСКИЕ КАНДИДАТЫ",
    "wait_confirmation": "⏳ ЖДАТЬ ПОДТВЕРЖДЕНИЯ",
    "wait_retest": "🔁 ЖДАТЬ РЕТЕСТ",
    "observe": "👀 ТОЛЬКО НАБЛЮДАТЬ",
    "blocked_risk": "🚫 ЗАБЛОКИРОВАНО РИСКОМ",
    "ignore": "⚪ ИГНОР",
}

DECISION_ORDER = [
    "candidate",
    "wait_confirmation",
    "wait_retest",
    "observe",
    "blocked_risk",
    "ignore",
]


def load_decision_payload(path: Path = INPUT_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {
            "error": f"Decision file not found: {path}",
            "decisions": [],
            "blockers": ["decision_file_not_found"],
            "warnings": [],
            "safe_to_continue": False,
        }

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as ex:
        return {
            "error": f"Invalid decision JSON: {ex}",
            "decisions": [],
            "blockers": ["invalid_decision_json"],
            "warnings": [],
            "safe_to_continue": False,
        }


def normalize_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]

    if isinstance(value, str) and value.strip():
        return [
            item.strip()
            for item in value.split(",")
            if item.strip()
        ]

    return []


def format_list(value: Any) -> str:
    items = normalize_list(value)
    return ", ".join(items) if items else "none"


def group_decisions(decisions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for item in decisions:
        decision = str(item.get("decision", "unknown"))
        grouped.setdefault(decision, []).append(item)

    for items in grouped.values():
        items.sort(
            key=lambda item: (
                int(item.get("priority", 0)),
                float(item.get("final_score") or 0.0),
            ),
            reverse=True,
        )

    return grouped


def build_compact_item_line(item: Dict[str, Any]) -> str:
    pair = item.get("pair")
    decision = item.get("decision")
    final_score = item.get("final_score")
    market_score = item.get("market_score")
    telegram_score = item.get("telegram_score")
    has_retest = item.get("has_retest")
    risk_flags = format_list(item.get("risk_flags"))
    message_intent = item.get("message_intent")

    return (
        f"{pair}: {decision}\n"
        f"final={final_score} | market={market_score} | telegram={telegram_score} | "
        f"retest={has_retest}\n"
        f"risks={risk_flags} | message={message_intent}"
    )


def build_decision_reason_line(item: Dict[str, Any]) -> str:
    reasons = normalize_list(item.get("reasons", []))

    if not reasons:
        return "Причина: нет подробного объяснения."

    important_reasons: List[str] = []

    for reason in reasons:
        text = str(reason)

        if (
            "message asks" in text
            or "needs retest" in text
            or "suitable only for observation" in text
            or "strong analytical candidate" in text
            or "blocked" in text
        ):
            important_reasons.append(text)

    if not important_reasons:
        important_reasons = reasons[-2:]

    return "Причина: " + "; ".join(important_reasons[:2])


def build_telegram_preview_text(payload: Dict[str, Any]) -> str:
    created_at = datetime.now().isoformat(timespec="seconds")
    decisions = payload.get("decisions", [])

    if not isinstance(decisions, list):
        decisions = []

    grouped = group_decisions(decisions)

    lines: List[str] = []

    lines.append("📡 Crypto Scanner Agent")
    lines.append("АНАЛИТИЧЕСКОЕ УВЕДОМЛЕНИЕ")
    lines.append("")
    lines.append(f"Создано: {created_at}")
    lines.append("Режим: аналитика без торговли")
    lines.append("Ордера: отключены")
    lines.append("Доставка: preview, сообщение не отправлено")
    lines.append("Binance orders: отключены")
    lines.append("")
    lines.append("Сводка:")
    lines.append(f"- всего решений: {payload.get('total_decisions', 0)}")
    lines.append(f"- candidates: {payload.get('total_input_candidates', 0)}")
    lines.append(f"- watchlist: {payload.get('total_input_watchlist_candidates', 0)}")
    lines.append(f"- by decision: {payload.get('summary_by_decision', {})}")
    lines.append("")

    if payload.get("error"):
        lines.append("Ошибка:")
        lines.append(str(payload.get("error")))
        lines.append("")

    has_items = False

    for decision in DECISION_ORDER:
        items = grouped.get(decision, [])

        if not items:
            continue

        has_items = True
        title = DECISION_TITLES.get(decision, decision.upper())

        lines.append(title)
        lines.append("-" * min(len(title), 32))

        for item in items[:5]:
            lines.append(build_compact_item_line(item))
            lines.append(build_decision_reason_line(item))
            lines.append("")

    unknown_decisions = sorted(
        decision
        for decision in grouped
        if decision not in DECISION_ORDER
    )

    for decision in unknown_decisions:
        items = grouped.get(decision, [])

        if not items:
            continue

        has_items = True
        lines.append("UNKNOWN: " + decision)
        lines.append("-" * 20)

        for item in items[:5]:
            lines.append(build_compact_item_line(item))
            lines.append(build_decision_reason_line(item))
            lines.append("")

    if not has_items:
        lines.append("Нет решений для уведомления.")
        lines.append("Сначала запустите полный безопасный сканер.")
        lines.append("")

    lines.append("Важно:")
    lines.append("Это не торговый сигнал и не команда на вход.")
    lines.append("Решение принимает только пользователь.")
    lines.append("Автоордера отключены.")

    text = "\n".join(lines)

    if len(text) <= MAX_TELEGRAM_MESSAGE_LENGTH:
        return text

    truncated = text[:MAX_TELEGRAM_MESSAGE_LENGTH - 120].rstrip()
    truncated += "\n\n[Обрезано для безопасной длины Telegram preview]"
    return truncated


def build_payload_status(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "safe_to_continue": bool(payload.get("safe_to_continue")),
        "telegram_send_enabled": False,
        "orders_enabled": False,
        "trading_enabled": False,
        "binance_api_used": False,
        "telegram_api_used": False,
        "telegram_alert_chat_configured": bool(TELEGRAM_ALERT_CHAT_ID),
        "input_file": str(INPUT_PATH),
        "notification_report_file_exists": NOTIFICATION_REPORT_PATH.exists(),
        "output_file": str(OUTPUT_PATH),
        "total_decisions": payload.get("total_decisions", 0),
        "summary_by_decision": payload.get("summary_by_decision", {}),
        "blockers": payload.get("blockers", []),
        "warnings": payload.get("warnings", []),
        "error": payload.get("error"),
    }


def save_telegram_preview_text(text: str, path: Path = OUTPUT_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def print_preview_summary(status: Dict[str, Any], output_path: Path) -> None:
    print("SCANNER AGENT TELEGRAM MESSAGE PREVIEW")
    print("======================================")
    print("Mode: analytical only")
    print("Telegram send enabled:", status["telegram_send_enabled"])
    print("Orders enabled:", status["orders_enabled"])
    print("Trading enabled:", status["trading_enabled"])
    print("Binance API used:", status["binance_api_used"])
    print("Telegram API used:", status["telegram_api_used"])
    print("Telegram alert chat configured:", status["telegram_alert_chat_configured"])
    print("Input file:", status["input_file"])
    print("Notification report exists:", status["notification_report_file_exists"])
    print("Output file:", output_path)
    print()

    print("SUMMARY")
    print("=======")
    print("Safe to continue:", status["safe_to_continue"])
    print("Total decisions:", status["total_decisions"])
    print("Summary by decision:", status["summary_by_decision"])

    if status.get("blockers"):
        print("Blockers:", ", ".join(str(item) for item in status["blockers"]))
    else:
        print("Blockers: none")

    if status.get("warnings"):
        print("Warnings:", ", ".join(str(item) for item in status["warnings"]))
    else:
        print("Warnings: none")

    if status.get("error"):
        print("Error:", status["error"])

    print()
    print("SAFETY")
    print("======")
    print("[OK] This script did not create orders.")
    print("[OK] This script did not start trading bot.")
    print("[OK] This script did not call Binance API.")
    print("[OK] This script did not read Telegram.")
    print("[OK] This script did not send Telegram messages.")
    print("[OK] This script only builds a local Telegram message preview.")

    print()
    print("NEXT STEP")
    print("=========")
    print("Review reports/scanner_agent_telegram_message_preview.txt.")
    print("Only after review, build a separate dry-run Telegram sender.")


def main() -> None:
    payload = load_decision_payload()
    text = build_telegram_preview_text(payload)
    output_path = save_telegram_preview_text(text)
    status = build_payload_status(payload)
    print_preview_summary(status, output_path)


if __name__ == "__main__":
    main()
