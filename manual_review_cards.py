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
        checklist.append(
            "Проверить и дождаться исчезновения флагов риска: "
            + format_translated_list(card["risk_flags"])
        )

    if card["confirmations"].get("market_confirmation") is not True:
        checklist.append("Дождаться рыночного подтверждения.")

    if card["confirmations"].get("has_retest") is not True:
        checklist.append("Дождаться подтверждённого ретеста.")

    if card["gaps"].get("telegram_score_gap") not in (None, 0, 0.0):
        checklist.append("Улучшить Telegram/соцподтверждение до целевого уровня.")

    if card["gaps"].get("final_score_gap") not in (None, 0, 0.0):
        checklist.append("Дождаться улучшения итоговой оценки до аналитического порога.")

    checklist.append("Не включать live-торговлю и не создавать ордера по этой карточке.")
    checklist.append("Решение по карточке: только ручная проверка.")

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




def translate_card_status(status: Any) -> str:
    mapping = {
        "BLOCKED": "ЗАБЛОКИРОВАНО",
        "WATCH_ONLY": "ТОЛЬКО НАБЛЮДЕНИЕ",
        "MANUAL_REVIEW": "РУЧНАЯ ПРОВЕРКА",
    }
    return mapping.get(str(status), str(status))


def translate_safe_decision(decision: Any) -> str:
    mapping = {
        "DO_NOT_ENTER": "НЕ ВХОДИТЬ В СДЕЛКУ",
        "WATCH_ONLY": "ТОЛЬКО НАБЛЮДАТЬ",
        "MANUAL_REVIEW_ONLY": "ТОЛЬКО РУЧНАЯ ПРОВЕРКА",
    }
    return mapping.get(str(decision), str(decision))


def translate_forbidden_action(action: Any) -> str:
    mapping = {
        "NO_ORDERS_NO_LIVE_TRADING_NO_AUTO_TELEGRAM": (
            "НЕ СОЗДАВАТЬ ОРДЕРА, НЕ ВКЛЮЧАТЬ LIVE-ТОРГОВЛЮ, "
            "НЕ ОТПРАВЛЯТЬ TELEGRAM АВТОМАТИЧЕСКИ"
        ),
    }
    return mapping.get(str(action), str(action))


def translate_summary_keys(summary: Any, translator) -> Dict[str, int]:
    result: Dict[str, int] = {}

    for key, value in as_dict(summary).items():
        result[translator(key)] = value

    return result


def translate_runtime_value(value: Any) -> str:
    if value is True:
        return "Да"
    if value is False:
        return "Нет"
    if value is None:
        return "нет данных"
    return str(value)


def translate_field_name(name: Any) -> str:
    mapping = {
        "final_score": "итоговая оценка",
        "market_score": "рыночная оценка",
        "telegram_score": "оценка Telegram/соцсигнала",
        "risk_adjustment": "поправка на риск",
        "message_quality_score": "качество сообщения",
        "final_score_gap": "не хватает до аналитического порога",
        "market_score_gap": "не хватает рыночного подтверждения",
        "telegram_score_gap": "не хватает Telegram/соцподтверждения",
        "missing_confirmations": "недостающие подтверждения",
        "market_confirmation": "рыночное подтверждение",
        "has_retest": "ретест подтверждён",
        "action_hint": "подсказка действия",
        "entry_forbidden": "вход запрещён",
        "weak_social_confirmation": "слабое соц/Telegram-подтверждение",
        "message_possible_news": "сообщение похоже на новостной сигнал",
        "no_market_confirmation": "нет рыночного подтверждения",
        "telegram_social_confirmation": "Telegram/соцподтверждение",
        "retest": "ретест",
        "risk_flag:weak_social_confirmation": "флаг риска: слабое соц/Telegram-подтверждение",
        "risk_flag:message_possible_news": "флаг риска: сообщение похоже на новостной сигнал",
        "risk_flag:no_market_confirmation": "флаг риска: нет рыночного подтверждения",
        "action_hint:entry_forbidden": "подсказка действия: вход запрещён",
    }
    return mapping.get(str(name), str(name))


def format_translated_list(value: Any) -> str:
    items = clean_list(value)

    if not items:
        return "нет"

    return ", ".join(translate_field_name(item) for item in items)


def translate_reasons_text(value: Any) -> str:
    text = format_list(value)

    replacements = {
        "blocked because dangerous or weak-risk conditions were detected": (
            "заблокировано: обнаружены опасные или слабые риск-условия"
        ),
        "status=пропустить": "статус=пропустить",
        "final_score": "итоговая оценка",
        "market_score": "рыночная оценка",
        "telegram_score": "оценка Telegram/соцсигнала",
        "has_retest": "ретест подтверждён",
        "market_confirmation": "рыночное подтверждение",
        "risk_level": "уровень риска",
        "action_hint": "подсказка действия",
        "message_intent": "смысл сообщения",
        "risk_flags": "флаги риска",
        "message_flags": "флаги сообщения",
        "entry_forbidden": "вход запрещён",
        "possible_news": "похоже на новость",
        "weak_social_confirmation": "слабое соц/Telegram-подтверждение",
        "message_possible_news": "сообщение похоже на новостной сигнал",
        "no_market_confirmation": "нет рыночного подтверждения",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def translate_unlock_condition(text: Any) -> str:
    raw = str(text)

    replacements = {
        "final_score must improve by": "итоговая оценка должна вырасти на",
        "points to reach analytical target": "пунктов, чтобы достичь аналитического порога",
        "market confirmation must become True": "должно появиться рыночное подтверждение",
        "retest must be confirmed before entry review": "перед рассмотрением входа должен быть подтверждён ретест",
        "Telegram/social confirmation must improve toward score": "Telegram/соцподтверждение должно улучшиться до оценки",
        "risk flags must be cleared or reduced": "флаги риска должны исчезнуть или снизиться",
        "action_hint must move away from entry_forbidden after safety checks": (
            "после безопасных проверок подсказка действия должна перестать быть «вход запрещён»"
        ),
        "weak_social_confirmation": "слабое соц/Telegram-подтверждение",
        "message_possible_news": "сообщение похоже на новостной сигнал",
        "no_market_confirmation": "нет рыночного подтверждения",
    }

    for old, new in replacements.items():
        raw = raw.replace(old, new)

    return raw


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

    lines.append("КАРТОЧКИ РУЧНОЙ ПРОВЕРКИ")
    lines.append("========================")
    lines.append(f"Создано: {payload.get('created_at')}")
    lines.append(f"Можно продолжать безопасный анализ: {translate_runtime_value(payload.get('safe_to_continue'))}")
    lines.append(f"Состояние quick dashboard: {payload.get('quick_dashboard_state')}")
    lines.append(f"Всего карточек: {payload.get('cards_count')}")
    lines.append(
        "Сводка по статусам: "
        f"{translate_summary_keys(payload.get('summary_by_status'), translate_card_status)}"
    )
    lines.append(
        "Сводка по решениям безопасности: "
        f"{translate_summary_keys(payload.get('summary_by_safe_decision'), translate_safe_decision)}"
    )
    lines.append(f"Блокеры: {format_translated_list(payload.get('blockers'))}")
    lines.append(f"Предупреждения: {format_translated_list(payload.get('warnings'))}")
    lines.append("")

    lines.append("БЕЗОПАСНОСТЬ")
    lines.append("============")
    lines.append("Только аналитика: Да")
    lines.append("Ордера включены: Нет")
    lines.append("Создание ордеров разрешено: Нет")
    lines.append("Торговля включена: Нет")
    lines.append("Отправка Telegram включена: Нет")
    lines.append("Binance private API использовался: Нет")
    lines.append("")

    if not cards:
        lines.append("КАРТОЧКИ")
        lines.append("========")
        lines.append("Карточек для ручной проверки нет.")
        lines.append("")
    else:
        for index, raw_card in enumerate(cards, 1):
            card = as_dict(raw_card)
            scores = as_dict(card.get("scores"))
            gaps = as_dict(card.get("gaps"))
            confirmations = as_dict(card.get("confirmations"))

            card_title = (
                f"КАРТОЧКА {index}: {card.get('pair')} — "
                f"{translate_card_status(card.get('card_status'))}"
            )
            lines.append(card_title)
            lines.append("-" * len(card_title))
            lines.append(f"Решение безопасности: {translate_safe_decision(card.get('safe_decision'))}")
            lines.append(f"Запрещённое действие: {translate_forbidden_action(card.get('forbidden_action'))}")
            lines.append(f"Тикер: {card.get('ticker')}")
            lines.append(f"Уровень риска: {card.get('risk_level')}")
            lines.append(f"Решение сканера: {card.get('decision')}")
            lines.append(f"Статус наблюдения: {card.get('watch_status')}")
            lines.append(f"Группа источника: {format_list(card.get('source_groups'))}")
            lines.append(f"Источники данных: {format_list(card.get('sources'))}")
            lines.append("")

            lines.append("Оценки:")
            lines.append(f"- Итоговая оценка: {scores.get('final_score')}")
            lines.append(f"- Рыночная оценка: {scores.get('market_score')}")
            lines.append(f"- Оценка Telegram/соцсигнала: {scores.get('telegram_score')}")
            lines.append(f"- Поправка на риск: {scores.get('risk_adjustment')}")
            lines.append(f"- Качество сообщения: {scores.get('message_quality_score')}")
            lines.append("")

            lines.append("Разрывы до допуска:")
            lines.append(f"- Не хватает до аналитического порога: {gaps.get('final_score_gap')}")
            lines.append(f"- Не хватает рыночного подтверждения: {gaps.get('market_score_gap')}")
            lines.append(f"- Не хватает Telegram/соцподтверждения: {gaps.get('telegram_score_gap')}")
            lines.append(
                "- Недостающие подтверждения: "
                f"{format_translated_list(gaps.get('missing_confirmations'))}"
            )
            lines.append("")

            lines.append("Подтверждения:")
            lines.append(
                "- Рыночное подтверждение: "
                f"{translate_runtime_value(confirmations.get('market_confirmation'))}"
            )
            lines.append(
                "- Ретест подтверждён: "
                f"{translate_runtime_value(confirmations.get('has_retest'))}"
            )
            lines.append(
                "- Подсказка действия: "
                f"{translate_field_name(confirmations.get('action_hint'))}"
            )
            lines.append("")

            lines.append(f"Флаги риска: {format_translated_list(card.get('risk_flags'))}")
            lines.append(
                "Флаги риска из сообщения: "
                f"{format_translated_list(card.get('message_risk_flags'))}"
            )
            lines.append(f"Причины блокировки: {format_list(card.get('block_reasons'))}")
            lines.append(f"Подробные причины: {translate_reasons_text(card.get('reasons'))}")
            lines.append("")

            lines.append(f"Объяснение риска: {card.get('risk_explanation')}")
            lines.append(f"Заметка для менеджера: {card.get('manager_note')}")
            lines.append(f"Рекомендуемый следующий шаг: {card.get('recommended_next_step')}")
            lines.append("")

            lines.append("Условия для разблокировки:")
            unlock_conditions = clean_list(card.get("unlock_conditions"))
            if unlock_conditions:
                for item in unlock_conditions:
                    lines.append(f"- {translate_unlock_condition(item)}")
            else:
                lines.append("- нет")
            lines.append("")

            lines.append("Чек-лист для человека:")
            checklist = clean_list(card.get("human_checklist"))
            if checklist:
                for item in checklist:
                    lines.append(f"- {item}")
            else:
                lines.append("- нет")
            lines.append("")

    lines.append("ИТОГОВОЕ ПРИМЕЧАНИЕ")
    lines.append("===================")
    lines.append("Эти карточки предназначены только для ручного анализа.")
    lines.append("Они не являются разрешением на сделку.")
    lines.append("Ордера не создаются.")
    lines.append("Telegram-сообщения не отправляются.")
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
    print("КАРТОЧКИ РУЧНОЙ ПРОВЕРКИ")
    print("========================")
    print("Режим: только аналитика")
    print("Можно продолжать безопасный анализ:", payload.get("safe_to_continue"))
    print("Состояние quick dashboard:", payload.get("quick_dashboard_state"))
    print("Всего карточек:", payload.get("cards_count"))
    print(
        "Сводка по статусам:",
        translate_summary_keys(payload.get("summary_by_status"), translate_card_status),
    )
    print(
        "Сводка по решениям безопасности:",
        translate_summary_keys(payload.get("summary_by_safe_decision"), translate_safe_decision),
    )
    print("JSON output:", json_path)
    print("TXT output:", txt_path)

    if payload.get("blockers"):
        print("Блокеры:", ", ".join(str(item) for item in payload["blockers"]))
    else:
        print("Блокеры: нет")

    if payload.get("warnings"):
        print("Предупреждения:", ", ".join(str(item) for item in payload["warnings"]))
    else:
        print("Предупреждения: нет")

    print()
    print("БЕЗОПАСНОСТЬ")
    print("============")
    print("[OK] Этот отчёт не создавал ордера.")
    print("[OK] Этот отчёт не запускал торгового бота.")
    print("[OK] Этот отчёт не вызывал Binance private API.")
    print("[OK] Этот отчёт не отправлял Telegram-сообщения.")
    print("[OK] Этот отчёт только читает существующие JSON-отчёты.")


def main() -> None:
    payload = build_payload()
    json_path = save_json(payload)
    txt_path = save_text(build_text_report(payload))
    print_summary(payload, json_path, txt_path)


if __name__ == "__main__":
    main()
