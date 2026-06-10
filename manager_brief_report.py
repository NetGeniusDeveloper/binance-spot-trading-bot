import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


REPORTS_DIR = Path("reports")

INPUT_JSON_PATH = REPORTS_DIR / "manual_review_cards.json"
OUTPUT_JSON_PATH = REPORTS_DIR / "manager_brief_report.json"
OUTPUT_TXT_PATH = REPORTS_DIR / "manager_brief_report.txt"


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


def format_list(value: Any) -> str:
    items = clean_list(value)
    return ", ".join(items) if items else "нет"


def format_bool_ru(value: Any) -> str:
    if value is True:
        return "Да"
    if value is False:
        return "Нет"
    if value is None:
        return "нет данных"
    return str(value)


def translate_safe_decision(value: Any) -> str:
    mapping = {
        "DO_NOT_ENTER": "НЕ ВХОДИТЬ",
        "WATCH_ONLY": "ТОЛЬКО НАБЛЮДАТЬ",
        "MANUAL_REVIEW_ONLY": "ТОЛЬКО РУЧНАЯ ПРОВЕРКА",
    }
    return mapping.get(str(value), str(value))


def translate_card_status(value: Any) -> str:
    mapping = {
        "BLOCKED": "ЗАБЛОКИРОВАНО",
        "WATCH_ONLY": "ТОЛЬКО НАБЛЮДЕНИЕ",
        "MANUAL_REVIEW": "РУЧНАЯ ПРОВЕРКА",
    }
    return mapping.get(str(value), str(value))


def translate_risk_flag(value: Any) -> str:
    mapping = {
        "weak_social_confirmation": "слабое Telegram/соцподтверждение",
        "message_possible_news": "сообщение похоже на новостной сигнал",
        "no_market_confirmation": "нет рыночного подтверждения",
        "pump_risk": "риск пампа",
        "dangerous_fomo": "опасный FOMO-сигнал",
        "negative_news_risk": "риск негативной новости",
        "late_entry": "поздний вход",
        "very_close_to_high": "цена близко к максимуму",
        "low_liquidity": "низкая ликвидность",
        "wide_spread": "широкий спред",
        "needs_retest": "нужен ретест",
    }
    return mapping.get(str(value), str(value))


def translate_confirmation(value: Any) -> str:
    mapping = {
        "market_confirmation": "рыночное подтверждение",
        "retest": "ретест",
        "telegram_social_confirmation": "Telegram/соцподтверждение",
        "risk_flag:weak_social_confirmation": "убрать слабое Telegram/соцподтверждение",
        "risk_flag:message_possible_news": "убрать новостной риск сообщения",
        "risk_flag:no_market_confirmation": "получить рыночное подтверждение",
        "action_hint:entry_forbidden": "снять запрет на вход после безопасных проверок",
    }
    return mapping.get(str(value), str(value))


def translate_list(items: Any, translator) -> List[str]:
    return [translator(item) for item in clean_list(items)]


def first_meaningful(items: List[str], limit: int = 3) -> str:
    clean = [str(item).strip() for item in items if str(item).strip()]

    if not clean:
        return "нет"

    return ", ".join(clean[:limit])


def load_manual_review_cards() -> Dict[str, Any]:
    if not INPUT_JSON_PATH.exists():
        return {
            "ok": False,
            "error": "manual_review_cards_json_missing",
            "payload": {},
        }

    try:
        payload = json.loads(INPUT_JSON_PATH.read_text(encoding="utf-8"))
    except Exception as ex:
        return {
            "ok": False,
            "error": f"manual_review_cards_json_read_error: {ex}",
            "payload": {},
        }

    if not isinstance(payload, dict):
        return {
            "ok": False,
            "error": "manual_review_cards_payload_not_dict",
            "payload": {},
        }

    return {
        "ok": True,
        "error": None,
        "payload": payload,
    }


def build_wait_for(card: Dict[str, Any]) -> List[str]:
    gaps = as_dict(card.get("gaps"))
    confirmations = as_dict(card.get("confirmations"))

    wait_for: List[str] = []

    if confirmations.get("market_confirmation") is not True:
        wait_for.append("рыночное подтверждение")

    if confirmations.get("has_retest") is not True:
        wait_for.append("подтверждённый ретест")

    if gaps.get("telegram_score_gap") not in (None, 0, 0.0):
        wait_for.append("усиление Telegram/соцподтверждения")

    if gaps.get("final_score_gap") not in (None, 0, 0.0):
        wait_for.append("рост итоговой оценки до аналитического порога")

    missing = translate_list(gaps.get("missing_confirmations"), translate_confirmation)
    for item in missing:
        if item not in wait_for:
            wait_for.append(item)

    return wait_for


def build_brief_items(cards: List[Any]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []

    for raw_card in cards:
        card = as_dict(raw_card)
        if not card:
            continue

        scores = as_dict(card.get("scores"))
        gaps = as_dict(card.get("gaps"))

        risk_flags = translate_list(card.get("risk_flags"), translate_risk_flag)
        block_reasons = clean_list(card.get("block_reasons"))
        wait_for = build_wait_for(card)

        result.append(
            {
                "pair": card.get("pair"),
                "ticker": card.get("ticker"),
                "status": card.get("card_status"),
                "status_ru": translate_card_status(card.get("card_status")),
                "safe_decision": card.get("safe_decision"),
                "safe_decision_ru": translate_safe_decision(card.get("safe_decision")),
                "forbidden_action": card.get("forbidden_action"),
                "risk_level": card.get("risk_level"),
                "final_score": scores.get("final_score"),
                "market_score": scores.get("market_score"),
                "telegram_score": scores.get("telegram_score"),
                "final_score_gap": gaps.get("final_score_gap"),
                "risk_flags_ru": risk_flags,
                "block_reasons": block_reasons,
                "manager_reason": first_meaningful(block_reasons or risk_flags, limit=4),
                "wait_for": wait_for,
                "wait_for_short": first_meaningful(wait_for, limit=4),
                "recommended_next_step": card.get("recommended_next_step"),
                "manager_note": card.get("manager_note"),
            }
        )

    def sort_key(item: Dict[str, Any]) -> tuple:
        try:
            gap = float(item.get("final_score_gap"))
        except Exception:
            gap = 999999.0

        return (gap, str(item.get("pair")))

    return sorted(result, key=sort_key)


def build_payload() -> Dict[str, Any]:
    loaded = load_manual_review_cards()

    blockers: List[str] = []
    warnings: List[str] = []

    if not loaded["ok"]:
        blockers.append(str(loaded["error"]))

    source_payload = as_dict(loaded.get("payload"))
    cards = as_list(source_payload.get("cards"))
    brief_items = build_brief_items(cards)

    summary_by_safe_decision = source_payload.get("summary_by_safe_decision", {})
    summary_by_status = source_payload.get("summary_by_status", {})

    all_blocked = bool(brief_items) and all(
        item.get("safe_decision") == "DO_NOT_ENTER"
        for item in brief_items
    )

    if all_blocked:
        final_summary = "Все текущие пары заблокированы. Вход запрещён."
    elif brief_items:
        final_summary = "Есть пары для ручного просмотра. Автоматический вход запрещён."
    else:
        final_summary = "Карточек для ручной проверки нет."

    return {
        "source": "manager_brief_report",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_json": str(INPUT_JSON_PATH),
        "output_json": str(OUTPUT_JSON_PATH),
        "output_txt": str(OUTPUT_TXT_PATH),
        "analytical_only": True,
        "orders_enabled": False,
        "order_execution_allowed": False,
        "trading_enabled": False,
        "telegram_sending": False,
        "binance_private_api_used": False,
        "safe_to_continue": not blockers,
        "cards_count": len(brief_items),
        "all_current_pairs_blocked": all_blocked,
        "summary": final_summary,
        "summary_by_status": summary_by_status,
        "summary_by_safe_decision": summary_by_safe_decision,
        "brief_items": brief_items,
        "blockers": blockers,
        "warnings": sorted(set(warnings)),
        "disclaimer_ru": (
            "Краткий отчёт предназначен только для ручного анализа. "
            "Он не является разрешением на сделку."
        ),
    }


def build_text_report(payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    items = as_list(payload.get("brief_items"))

    lines.append("КРАТКИЙ ОТЧЁТ ДЛЯ МЕНЕДЖЕРА")
    lines.append("===========================")
    lines.append(f"Создано: {payload.get('created_at')}")
    lines.append(f"Можно продолжать безопасный анализ: {format_bool_ru(payload.get('safe_to_continue'))}")
    lines.append(f"Всего карточек: {payload.get('cards_count')}")
    lines.append(f"Итог: {payload.get('summary')}")
    lines.append(f"Блокеры: {format_list(payload.get('blockers'))}")
    lines.append(f"Предупреждения: {format_list(payload.get('warnings'))}")
    lines.append("")

    if not items:
        lines.append("ПАРЫ")
        lines.append("====")
        lines.append("Нет пар для краткого отчёта.")
        lines.append("")
    else:
        lines.append("ПАРЫ ДЛЯ РУЧНОГО РАЗБОРА")
        lines.append("========================")
        lines.append("")

        for index, raw_item in enumerate(items, 1):
            item = as_dict(raw_item)

            lines.append(f"{index}. {item.get('pair')} — {item.get('safe_decision_ru')}")
            lines.append(f"   Статус: {item.get('status_ru')}")
            lines.append(f"   Риск: {item.get('risk_level')}")
            lines.append(
                "   Оценки: "
                f"итоговая={item.get('final_score')}, "
                f"рынок={item.get('market_score')}, "
                f"Telegram/соцсигнал={item.get('telegram_score')}"
            )
            lines.append(f"   Причина: {item.get('manager_reason')}")
            lines.append(f"   Что ждать: {item.get('wait_for_short')}")
            lines.append(f"   Следующий шаг: {item.get('recommended_next_step')}")
            lines.append("")

    lines.append("БЕЗОПАСНОСТЬ")
    lines.append("============")
    lines.append("Ордера не создавались.")
    lines.append("Live-торговля не включалась.")
    lines.append("Binance private API не использовался.")
    lines.append("Telegram-сообщения не отправлялись.")
    lines.append("Отчёт только читает существующие JSON-отчёты.")
    lines.append("")
    lines.append("ПРИМЕЧАНИЕ")
    lines.append("==========")
    lines.append(str(payload.get("disclaimer_ru")))
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
    print("КРАТКИЙ ОТЧЁТ ДЛЯ МЕНЕДЖЕРА")
    print("===========================")
    print("Режим: только аналитика")
    print("Можно продолжать безопасный анализ:", payload.get("safe_to_continue"))
    print("Всего карточек:", payload.get("cards_count"))
    print("Итог:", payload.get("summary"))
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
