import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


REPORTS_DIR = Path("reports")

OUTPUT_JSON_PATH = REPORTS_DIR / "manual_review_cards.json"
OUTPUT_TXT_PATH = REPORTS_DIR / "manual_review_cards.txt"

INPUT_PATHS = {
    "blocked_risk": REPORTS_DIR / "scanner_agent_blocked_risk_report.json",
    "watchlist": REPORTS_DIR / "scanner_agent_watchlist_report.json",
    "risk_filter_backtest": REPORTS_DIR / "scanner_agent_risk_filter_backtest.json",
    "quick_dashboard": REPORTS_DIR / "quick_safe_dashboard.json",
}


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "ok": False,
            "path": str(path),
            "error": "file_not_found",
            "data": {},
        }

    try:
        return {
            "ok": True,
            "path": str(path),
            "error": None,
            "data": json.loads(path.read_text(encoding="utf-8")),
        }
    except json.JSONDecodeError as ex:
        return {
            "ok": False,
            "path": str(path),
            "error": f"invalid_json: {ex}",
            "data": {},
        }
    except OSError as ex:
        return {
            "ok": False,
            "path": str(path),
            "error": f"read_error: {ex}",
            "data": {},
        }


def as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def clean_list(value: Any) -> List[str]:
    result: List[str] = []

    for item in as_list(value):
        text = str(item).strip()
        if text and text not in result:
            result.append(text)

    return result


def first_existing(item: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, "", [], {}):
            return value
    return default


def format_bool(value: Any) -> str:
    if value is True:
        return "True"
    if value is False:
        return "False"
    if value is None:
        return "n/a"
    return str(value)


def format_list(value: Any) -> str:
    items = clean_list(value)
    return ", ".join(items) if items else "none"


def pair_key(item: Dict[str, Any]) -> str:
    return str(first_existing(item, ["pair", "symbol", "ticker"], "UNKNOWN"))


def merge_unique(existing: List[str], incoming: Any) -> List[str]:
    result = list(existing)

    for item in clean_list(incoming):
        if item not in result:
            result.append(item)

    return result


def extract_gap_from_backtest(item: Dict[str, Any]) -> Dict[str, Any]:
    gap = as_dict(item.get("gap"))

    return {
        "final_score_gap": first_existing(
            item,
            ["final_score_gap", "unlock_score_gap", "score_gap_to_unlock_target"],
            gap.get("final_score_gap"),
        ),
        "market_score_gap": first_existing(
            item,
            ["market_score_gap"],
            gap.get("market_score_gap"),
        ),
        "telegram_score_gap": first_existing(
            item,
            ["telegram_score_gap", "telegram_score_gap_to_confirmation_target"],
            gap.get("telegram_score_gap"),
        ),
        "missing_confirmations": clean_list(gap.get("missing_confirmations")),
    }


def extract_gap_from_blocked(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "final_score_gap": item.get("score_gap_to_unlock_target"),
        "market_score_gap": None,
        "telegram_score_gap": item.get("telegram_score_gap_to_confirmation_target"),
        "missing_confirmations": [],
    }


def empty_card(pair: str) -> Dict[str, Any]:
    return {
        "pair": pair,
        "ticker": None,
        "exchange": None,
        "card_status": "MANUAL_REVIEW",
        "safe_decision": "MANUAL_REVIEW_ONLY",
        "forbidden_action": "NO_ORDERS_NO_LIVE_TRADING_NO_AUTO_TELEGRAM",
        "source_groups": [],
        "decision": None,
        "watch_status": None,
        "risk_level": None,
        "risk_flags": [],
        "message_risk_flags": [],
        "block_reasons": [],
        "reasons": [],
        "risk_explanation": None,
        "manager_note": None,
        "recommended_next_step": None,
        "unlock_conditions": [],
        "scores": {
            "final_score": None,
            "market_score": None,
            "telegram_score": None,
            "risk_adjustment": None,
            "message_quality_score": None,
        },
        "gaps": {
            "final_score_gap": None,
            "market_score_gap": None,
            "telegram_score_gap": None,
            "missing_confirmations": [],
        },
        "confirmations": {
            "market_confirmation": None,
            "has_retest": None,
            "action_hint": None,
        },
        "runtime_safety": {
            "analytical_only": True,
            "orders_enabled": False,
            "order_execution_allowed": False,
            "trading_enabled": False,
        },
        "human_checklist": [],
        "sources": [],
    }


def apply_common_fields(card: Dict[str, Any], item: Dict[str, Any], source_name: str) -> None:
    card["ticker"] = first_existing(item, ["ticker", "symbol"], card.get("ticker"))
    card["exchange"] = first_existing(item, ["exchange"], card.get("exchange"))

    source_group = item.get("source_group")
    if source_group and source_group not in card["source_groups"]:
        card["source_groups"].append(source_group)

    if source_name not in card["sources"]:
        card["sources"].append(source_name)

    card["decision"] = first_existing(item, ["decision"], card.get("decision"))
    card["risk_level"] = first_existing(item, ["risk_level"], card.get("risk_level"))
    card["recommended_next_step"] = first_existing(
        item,
        ["recommended_next_step"],
        card.get("recommended_next_step"),
    )
    card["manager_note"] = first_existing(item, ["manager_note"], card.get("manager_note"))
    card["risk_explanation"] = first_existing(
        item,
        ["risk_explanation"],
        card.get("risk_explanation"),
    )

    card["risk_flags"] = merge_unique(card["risk_flags"], item.get("risk_flags"))
    card["message_risk_flags"] = merge_unique(
        card["message_risk_flags"],
        item.get("message_risk_flags"),
    )
    card["block_reasons"] = merge_unique(card["block_reasons"], item.get("block_reasons"))
    card["reasons"] = merge_unique(card["reasons"], item.get("reasons"))
    card["unlock_conditions"] = merge_unique(
        card["unlock_conditions"],
        item.get("unlock_conditions"),
    )

    card["scores"]["final_score"] = first_existing(
        item,
        ["final_score"],
        card["scores"].get("final_score"),
    )
    card["scores"]["market_score"] = first_existing(
        item,
        ["market_score"],
        card["scores"].get("market_score"),
    )
    card["scores"]["telegram_score"] = first_existing(
        item,
        ["telegram_score"],
        card["scores"].get("telegram_score"),
    )
    card["scores"]["risk_adjustment"] = first_existing(
        item,
        ["risk_adjustment"],
        card["scores"].get("risk_adjustment"),
    )
    card["scores"]["message_quality_score"] = first_existing(
        item,
        ["message_quality_score"],
        card["scores"].get("message_quality_score"),
    )

    card["confirmations"]["market_confirmation"] = first_existing(
        item,
        ["market_confirmation"],
        card["confirmations"].get("market_confirmation"),
    )
    card["confirmations"]["has_retest"] = first_existing(
        item,
        ["has_retest"],
        card["confirmations"].get("has_retest"),
    )
    card["confirmations"]["action_hint"] = first_existing(
        item,
        ["action_hint"],
        card["confirmations"].get("action_hint"),
    )

    analytical_only = item.get("analytical_only")
    orders_enabled = item.get("orders_enabled")
    order_execution_allowed = item.get("order_execution_allowed")
    trading_enabled = item.get("trading_enabled")

    if analytical_only is not None:
        card["runtime_safety"]["analytical_only"] = analytical_only
    if orders_enabled is not None:
        card["runtime_safety"]["orders_enabled"] = orders_enabled
    if order_execution_allowed is not None:
        card["runtime_safety"]["order_execution_allowed"] = order_execution_allowed
    if trading_enabled is not None:
        card["runtime_safety"]["trading_enabled"] = trading_enabled


def apply_gap(card: Dict[str, Any], gap: Dict[str, Any]) -> None:
    for key in ["final_score_gap", "market_score_gap", "telegram_score_gap"]:
        if gap.get(key) is not None:
            card["gaps"][key] = gap.get(key)

    card["gaps"]["missing_confirmations"] = merge_unique(
        card["gaps"].get("missing_confirmations", []),
        gap.get("missing_confirmations"),
    )


def build_human_checklist(card: Dict[str, Any]) -> List[str]:
    checklist: List[str] = []

    if card["card_status"] == "BLOCKED":
        checklist.append("Не входить в сделку по этой паре.")
        checklist.append("Оставить пару только для ручного наблюдения и повторного анализа.")

    if card["risk_flags"]:
        checklist.append("Проверить и дождаться исчезновения risk flags: " + format_list(card["risk_flags"]))

    if card["confirmations"].get("market_confirmation") is not True:
        checklist.append("Дождаться market confirmation.")

    if card["confirmations"].get("has_retest") is not True:
        checklist.append("Дождаться подтверждённого ретеста.")

    if card["gaps"].get("telegram_score_gap") not in (None, 0, 0.0):
        checklist.append("Улучшить Telegram/social confirmation до целевого уровня.")

    if card["gaps"].get("final_score_gap") not in (None, 0, 0.0):
        checklist.append("Дождаться улучшения final score до аналитического порога.")

    checklist.append("Не включать live-trading и не создавать ордера по этой карточке.")
    checklist.append("Решение по карточке: manual review only.")

    return checklist


def build_cards(
    blocked_risk: Dict[str, Any],
    watchlist: Dict[str, Any],
    risk_filter: Dict[str, Any],
) -> List[Dict[str, Any]]:
    cards: Dict[str, Dict[str, Any]] = {}

    def get_card(item: Dict[str, Any]) -> Dict[str, Any]:
        pair = pair_key(item)
        if pair not in cards:
            cards[pair] = empty_card(pair)
        return cards[pair]

    for raw_item in as_list(blocked_risk.get("blocked_items")):
        item = as_dict(raw_item)
        if not item:
            continue

        card = get_card(item)
        card["card_status"] = "BLOCKED"
        card["safe_decision"] = "DO_NOT_ENTER"
        apply_common_fields(card, item, "blocked_risk")
        apply_gap(card, extract_gap_from_blocked(item))

    for raw_item in as_list(watchlist.get("watchlist_items")):
        item = as_dict(raw_item)
        if not item:
            continue

        card = get_card(item)
        if card["card_status"] != "BLOCKED":
            card["card_status"] = "WATCH_ONLY"
            card["safe_decision"] = "WATCH_ONLY"

        card["watch_status"] = first_existing(item, ["watch_status"], card.get("watch_status"))
        apply_common_fields(card, item, "watchlist")

    for raw_item in as_list(risk_filter.get("backtest_items")):
        item = as_dict(raw_item)
        if not item:
            continue

        card = get_card(item)
        if item.get("backtest_bucket") == "BLOCKED":
            card["card_status"] = "BLOCKED"
            card["safe_decision"] = "DO_NOT_ENTER"

        apply_common_fields(card, item, "risk_filter_backtest")
        apply_gap(card, extract_gap_from_backtest(item))

    for raw_item in as_list(risk_filter.get("closest_to_unlock")):
        item = as_dict(raw_item)
        if not item:
            continue

        card = get_card(item)
        apply_common_fields(card, item, "closest_to_unlock")
        apply_gap(card, extract_gap_from_backtest(item))

    result = list(cards.values())

    for card in result:
        card["human_checklist"] = build_human_checklist(card)

    def sort_key(card: Dict[str, Any]) -> Tuple[int, float, str]:
        status_order = {
            "BLOCKED": 0,
            "WATCH_ONLY": 1,
            "MANUAL_REVIEW": 2,
        }

        raw_gap = card.get("gaps", {}).get("final_score_gap")
        try:
            gap = float(raw_gap)
        except Exception:
            gap = 999999.0

        return (status_order.get(card.get("card_status"), 99), gap, str(card.get("pair")))

    return sorted(result, key=sort_key)


def build_payload() -> Dict[str, Any]:
    loaded = {
        name: load_json(path)
        for name, path in INPUT_PATHS.items()
    }

    blocked_risk = as_dict(loaded["blocked_risk"].get("data"))
    watchlist = as_dict(loaded["watchlist"].get("data"))
    risk_filter = as_dict(loaded["risk_filter_backtest"].get("data"))
    quick_dashboard = as_dict(loaded["quick_dashboard"].get("data"))

    missing_or_invalid = [
        name
        for name, item in loaded.items()
        if not item.get("ok")
    ]

    cards = build_cards(
        blocked_risk=blocked_risk,
        watchlist=watchlist,
        risk_filter=risk_filter,
    )

    blockers: List[str] = []

    if missing_or_invalid:
        blockers.append("manual_review_source_reports_missing_or_invalid")

    warnings: List[str] = []

    for name, item in loaded.items():
        if not item.get("ok"):
            warnings.append(f"{name}:{item.get('error')}")

    dashboard = as_dict(quick_dashboard.get("dashboard"))
    cockpit = as_dict(dashboard.get("decision_cockpit"))

    return {
        "source": "manual_review_cards",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_files": {
            name: {
                "ok": item.get("ok"),
                "path": item.get("path"),
                "error": item.get("error"),
            }
            for name, item in loaded.items()
        },
        "output_json": str(OUTPUT_JSON_PATH),
        "output_txt": str(OUTPUT_TXT_PATH),
        "analytical_only": True,
        "orders_enabled": False,
        "order_execution_allowed": False,
        "trading_enabled": False,
        "telegram_sending": False,
        "binance_private_api_used": False,
        "safe_to_continue": not blockers,
        "quick_dashboard_state": cockpit.get("state"),
        "cards_count": len(cards),
        "summary_by_status": count_by(cards, "card_status"),
        "summary_by_safe_decision": count_by(cards, "safe_decision"),
        "cards": cards,
        "blockers": blockers,
        "warnings": sorted(set(warnings)),
        "disclaimer": (
            "Manual review cards are analytical only. They do not create orders, "
            "do not start trading, do not call Binance private API, and do not send Telegram messages."
        ),
    }


def count_by(items: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    result: Dict[str, int] = {}

    for item in items:
        value = str(item.get(key) or "UNKNOWN")
        result[value] = result.get(value, 0) + 1

    return dict(sorted(result.items()))


def build_text_report(payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    cards = as_list(payload.get("cards"))

    lines.append("MANUAL REVIEW CARDS")
    lines.append("===================")
    lines.append(f"Created at: {payload.get('created_at')}")
    lines.append(f"Safe to continue: {payload.get('safe_to_continue')}")
    lines.append(f"Quick dashboard state: {payload.get('quick_dashboard_state')}")
    lines.append(f"Cards count: {payload.get('cards_count')}")
    lines.append(f"Summary by status: {payload.get('summary_by_status')}")
    lines.append(f"Summary by safe decision: {payload.get('summary_by_safe_decision')}")
    lines.append(f"Blockers: {format_list(payload.get('blockers'))}")
    lines.append(f"Warnings: {format_list(payload.get('warnings'))}")
    lines.append("")

    lines.append("SAFETY")
    lines.append("======")
    lines.append("Analytical only: True")
    lines.append("Orders enabled: False")
    lines.append("Order execution allowed: False")
    lines.append("Trading enabled: False")
    lines.append("Telegram sending: False")
    lines.append("Binance private API used: False")
    lines.append("")

    if not cards:
        lines.append("CARDS")
        lines.append("=====")
        lines.append("No manual review cards.")
        lines.append("")
    else:
        for index, raw_card in enumerate(cards, 1):
            card = as_dict(raw_card)
            scores = as_dict(card.get("scores"))
            gaps = as_dict(card.get("gaps"))
            confirmations = as_dict(card.get("confirmations"))

            lines.append(f"CARD {index}: {card.get('pair')} — {card.get('card_status')}")
            lines.append("-" * (len(lines[-1])))
            lines.append(f"Safe decision: {card.get('safe_decision')}")
            lines.append(f"Forbidden action: {card.get('forbidden_action')}")
            lines.append(f"Ticker: {card.get('ticker')}")
            lines.append(f"Risk level: {card.get('risk_level')}")
            lines.append(f"Decision: {card.get('decision')}")
            lines.append(f"Watch status: {card.get('watch_status')}")
            lines.append(f"Source groups: {format_list(card.get('source_groups'))}")
            lines.append(f"Sources: {format_list(card.get('sources'))}")
            lines.append("")
            lines.append("Scores:")
            lines.append(f"- final_score: {scores.get('final_score')}")
            lines.append(f"- market_score: {scores.get('market_score')}")
            lines.append(f"- telegram_score: {scores.get('telegram_score')}")
            lines.append(f"- risk_adjustment: {scores.get('risk_adjustment')}")
            lines.append(f"- message_quality_score: {scores.get('message_quality_score')}")
            lines.append("")
            lines.append("Gaps:")
            lines.append(f"- final_score_gap: {gaps.get('final_score_gap')}")
            lines.append(f"- market_score_gap: {gaps.get('market_score_gap')}")
            lines.append(f"- telegram_score_gap: {gaps.get('telegram_score_gap')}")
            lines.append(f"- missing_confirmations: {format_list(gaps.get('missing_confirmations'))}")
            lines.append("")
            lines.append("Confirmations:")
            lines.append(f"- market_confirmation: {format_bool(confirmations.get('market_confirmation'))}")
            lines.append(f"- has_retest: {format_bool(confirmations.get('has_retest'))}")
            lines.append(f"- action_hint: {confirmations.get('action_hint')}")
            lines.append("")
            lines.append(f"Risk flags: {format_list(card.get('risk_flags'))}")
            lines.append(f"Message risk flags: {format_list(card.get('message_risk_flags'))}")
            lines.append(f"Block reasons: {format_list(card.get('block_reasons'))}")
            lines.append(f"Reasons: {format_list(card.get('reasons'))}")
            lines.append("")
            lines.append(f"Risk explanation: {card.get('risk_explanation')}")
            lines.append(f"Manager note: {card.get('manager_note')}")
            lines.append(f"Recommended next step: {card.get('recommended_next_step')}")
            lines.append("")
            lines.append("Unlock conditions:")
            unlock_conditions = clean_list(card.get("unlock_conditions"))
            if unlock_conditions:
                for item in unlock_conditions:
                    lines.append(f"- {item}")
            else:
                lines.append("- none")
            lines.append("")
            lines.append("Human checklist:")
            checklist = clean_list(card.get("human_checklist"))
            if checklist:
                for item in checklist:
                    lines.append(f"- {item}")
            else:
                lines.append("- none")
            lines.append("")

    lines.append("FINAL NOTE")
    lines.append("==========")
    lines.append("These cards are for manual review only.")
    lines.append("Do not use them as permission to trade.")
    lines.append("No orders are created.")
    lines.append("No Telegram messages are sent.")
    lines.append("")

    return "\n".join(lines)


def save_json(payload: Dict[str, Any], path: Path = OUTPUT_JSON_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def save_text(text: str, path: Path = OUTPUT_TXT_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def print_summary(payload: Dict[str, Any], json_path: Path, txt_path: Path) -> None:
    print("MANUAL REVIEW CARDS")
    print("===================")
    print("Mode: analytical only")
    print("Safe to continue:", payload.get("safe_to_continue"))
    print("Quick dashboard state:", payload.get("quick_dashboard_state"))
    print("Cards count:", payload.get("cards_count"))
    print("Summary by status:", payload.get("summary_by_status"))
    print("Summary by safe decision:", payload.get("summary_by_safe_decision"))
    print("JSON output:", json_path)
    print("TXT output:", txt_path)

    if payload.get("blockers"):
        print("Blockers:", ", ".join(str(item) for item in payload["blockers"]))
    else:
        print("Blockers: none")

    if payload.get("warnings"):
        print("Warnings:", ", ".join(str(item) for item in payload["warnings"]))
    else:
        print("Warnings: none")

    print()
    print("SAFETY")
    print("======")
    print("[OK] This report did not create orders.")
    print("[OK] This report did not start trading bot.")
    print("[OK] This report did not call Binance private API.")
    print("[OK] This report did not send Telegram messages.")
    print("[OK] This report only reads existing JSON reports.")


def main() -> None:
    payload = build_payload()
    json_path = save_json(payload)
    txt_path = save_text(build_text_report(payload))
    print_summary(payload, json_path, txt_path)


if __name__ == "__main__":
    main()
