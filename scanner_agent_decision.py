import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


REPORTS_DIR = Path("reports")
INPUT_PATH = REPORTS_DIR / "scanner_agent_export.json"
OUTPUT_PATH = REPORTS_DIR / "scanner_agent_decision.json"

BLOCKING_RISKS = {
    "pump_risk",
    "dangerous_fomo",
    "very_wide_spread",
}

CONFIRMATION_FLAGS = {
    "message_wait_confirmation",
    "needs_retest",
}

LIQUIDITY_RISKS = {
    "low_liquidity",
    "thin_liquidity",
}

NO_CONFIRMATION_RISKS = {
    "no_market_confirmation",
    "weak_social_confirmation",
}

BLOCKING_ACTION_HINTS = {
    "entry_forbidden",
}

WAIT_ACTION_HINTS = {
    "wait_retest_confirmation",
    "wait_confirmation",
}

OBSERVE_ACTION_HINTS = {
    "observe_only",
    "watch_only",
}

HIGH_RISK_LEVELS = {
    "high",
    "critical",
}

MEDIUM_RISK_LEVELS = {
    "medium",
}

MIN_CANDIDATE_SCORE = 70.0
MIN_OBSERVE_SCORE = 55.0
MIN_MARKET_CONFIRMATION_SCORE = 60.0


def load_agent_export(path: Path = INPUT_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {
            "error": f"Agent export file not found: {path}",
            "candidates": [],
            "watchlist_candidates": [],
            "blockers": ["agent_export_file_not_found"],
            "warnings": [],
            "safe_to_continue": False,
        }

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as ex:
        return {
            "error": f"Invalid agent export JSON: {ex}",
            "candidates": [],
            "watchlist_candidates": [],
            "blockers": ["invalid_agent_export_json"],
            "warnings": [],
            "safe_to_continue": False,
        }


def normalize_risk_flags(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]

    if isinstance(value, str) and value.strip():
        return [
            item.strip()
            for item in value.split(",")
            if item.strip()
        ]

    return []


def has_any(items: List[str], flags: set[str]) -> bool:
    return any(item in flags for item in items)




RISK_FLAG_LABELS = {
    "pump_risk": "обнаружен риск пампа или перегретого движения",
    "dangerous_fomo": "сообщение похоже на FOMO/агрессивный призыв",
    "late_entry": "вход выглядит поздним после сильного движения",
    "very_close_to_high": "цена находится слишком близко к локальному максимуму",
    "low_liquidity": "низкая ликвидность для безопасного сценария",
    "thin_liquidity": "тонкая ликвидность, повышенный риск проскальзывания",
    "wide_spread": "широкий спред",
    "very_wide_spread": "очень широкий спред",
    "no_market_confirmation": "нет рыночного подтверждения",
    "weak_social_confirmation": "слабое подтверждение со стороны Telegram/соцсигнала",
    "needs_retest": "нужен ретест перед любыми действиями",
    "message_wait_confirmation": "сообщение требует ожидания подтверждения",
    "message_pump_fomo": "текст сообщения похож на памп/FOMO",
}


def explain_risk_flag(flag: str) -> str:
    return RISK_FLAG_LABELS.get(str(flag), str(flag))


def build_block_reasons(
    decision: str,
    risk_flags: List[str],
    message_flags: List[str],
    market_confirmation: bool,
    has_retest: bool,
    action_hint: str,
) -> List[str]:
    reasons: List[str] = []

    for flag in risk_flags:
        explanation = explain_risk_flag(flag)
        if explanation not in reasons:
            reasons.append(explanation)

    for flag in message_flags:
        explanation = explain_risk_flag(flag)
        if explanation not in reasons:
            reasons.append(explanation)

    if not market_confirmation:
        explanation = explain_risk_flag("no_market_confirmation")
        if explanation not in reasons:
            reasons.append(explanation)

    if not has_retest and decision in {"wait_retest", "blocked_risk"}:
        explanation = explain_risk_flag("needs_retest")
        if explanation not in reasons:
            reasons.append(explanation)

    if action_hint == "entry_forbidden":
        reasons.append("вход запрещён безопасной логикой сканера")

    if not reasons:
        reasons.append("нет отдельной блокирующей причины, требуется ручная оценка")

    return reasons


def build_risk_explanation(
    decision: str,
    risk_level: str,
    block_reasons: List[str],
) -> str:
    if decision == "blocked_risk":
        return (
            "Сигнал заблокирован риск-фильтром. Причины: "
            + "; ".join(block_reasons)
            + "."
        )

    if decision == "wait_retest":
        return (
            "Сигнал не заблокирован полностью, но вход запрещён до ретеста "
            "или дополнительного подтверждения."
        )

    if decision == "wait_confirmation":
        return (
            "Сигнал требует подтверждения. Без подтверждения вход запрещён."
        )

    if decision == "observe":
        return (
            "Сигнал подходит только для наблюдения. Автоматический вход запрещён."
        )

    if decision == "candidate":
        return (
            "Сильный аналитический кандидат, но это всё равно не команда на вход. "
            "Нужна ручная проверка."
        )

    return (
        "Сигнал слабый, нейтральный или не подходит для действия. "
        f"Уровень риска: {risk_level}."
    )


def build_manager_note(
    item: Dict[str, Any],
    decision: str,
    risk_level: str,
    block_reasons: List[str],
) -> str:
    pair = item.get("pair")
    final_score = float(item.get("final_score") or 0.0)
    market_score = float(item.get("market_score") or 0.0)
    telegram_score = float(item.get("telegram_score") or 0.0)

    if decision == "blocked_risk":
        return (
            f"{pair}: не использовать для входа. "
            f"Риск: {risk_level}. "
            f"Оценки final={final_score}, market={market_score}, telegram={telegram_score}. "
            f"Главные причины: {'; '.join(block_reasons[:4])}."
        )

    if decision in {"wait_retest", "wait_confirmation"}:
        return (
            f"{pair}: наблюдать, но вход запрещён до подтверждения. "
            f"Оценки final={final_score}, market={market_score}, telegram={telegram_score}."
        )

    if decision == "observe":
        return (
            f"{pair}: только наблюдение. Для действия недостаточно подтверждений."
        )

    if decision == "candidate":
        return (
            f"{pair}: сильный аналитический кандидат, требуется ручная проверка."
        )

    return f"{pair}: сигнал слабый или нейтральный, действие не требуется."


def build_recommended_next_step(
    decision: str,
    risk_flags: List[str],
    message_flags: List[str],
    has_retest: bool,
) -> str:
    all_flags = set(risk_flags + message_flags)

    if decision == "blocked_risk":
        if "pump_risk" in all_flags or "dangerous_fomo" in all_flags:
            return "Не входить. Дождаться охлаждения рынка и новых независимых подтверждений."
        if "low_liquidity" in all_flags or "thin_liquidity" in all_flags:
            return "Не входить. Проверить ликвидность позже или исключить инструмент из активного наблюдения."
        if "no_market_confirmation" in all_flags:
            return "Не входить. Ждать рыночного подтверждения и повторного анализа."
        return "Не входить. Оставить только в аналитическом журнале."

    if decision == "wait_retest":
        return "Ждать ретест уровня и повторный сигнал. До ретеста вход запрещён."

    if decision == "wait_confirmation":
        return "Ждать подтверждения объёмом, ценой и новым сообщением. До подтверждения вход запрещён."

    if decision == "observe":
        return "Продолжить наблюдение без отправки команды на вход."

    if decision == "candidate":
        if has_retest:
            return "Перед любыми действиями выполнить ручную проверку графика, ликвидности и риска."
        return "Сначала дождаться ретеста, затем выполнить ручную проверку."

    return "Игнорировать сигнал и продолжить сбор данных."


def build_decision_reason(
    item: Dict[str, Any],
    decision: str,
    risk_flags: List[str],
    message_flags: List[str],
) -> List[str]:
    reasons: List[str] = []

    status = str(item.get("suggested_status", ""))
    final_score = float(item.get("final_score") or 0.0)
    market_score = float(item.get("market_score") or 0.0)
    telegram_score = float(item.get("telegram_score") or 0.0)
    has_retest = bool(item.get("has_retest"))
    market_confirmation = bool(item.get("market_confirmation"))
    risk_level = str(item.get("risk_level") or "unknown")
    action_hint = str(item.get("action_hint") or "unknown")
    message_intent = str(item.get("message_intent") or "")

    reasons.append(f"status={status}")
    reasons.append(f"final_score={final_score}")
    reasons.append(f"market_score={market_score}")
    reasons.append(f"telegram_score={telegram_score}")
    reasons.append(f"has_retest={has_retest}")
    reasons.append(f"market_confirmation={market_confirmation}")
    reasons.append(f"risk_level={risk_level}")
    reasons.append(f"action_hint={action_hint}")

    if message_intent:
        reasons.append(f"message_intent={message_intent}")

    if risk_flags:
        reasons.append("risk_flags=" + ",".join(risk_flags))
    else:
        reasons.append("risk_flags=none")

    if message_flags:
        reasons.append("message_flags=" + ",".join(message_flags))

    if decision == "blocked_risk":
        reasons.append("blocked because dangerous or weak-risk conditions were detected")

    if decision == "wait_confirmation":
        reasons.append("message asks to wait for confirmation")

    if decision == "wait_retest":
        reasons.append("нужен ретест или подтверждение перед любыми действиями")

    if decision == "observe":
        reasons.append("сигнал подходит только для наблюдения")

    if decision == "candidate":
        reasons.append("strong analytical candidate, still not a trade entry")

    if decision == "ignore":
        reasons.append("сигнал слабый, нейтральный или не подходит для действия")

    return reasons


def decide_item(item: Dict[str, Any], source_group: str) -> Dict[str, Any]:
    risk_flags = normalize_risk_flags(item.get("risk_flags", []))
    message_flags = normalize_risk_flags(item.get("message_risk_flags", []))

    status = str(item.get("suggested_status", ""))
    final_score = float(item.get("final_score") or 0.0)
    market_score = float(item.get("market_score") or 0.0)
    telegram_score = float(item.get("telegram_score") or 0.0)
    has_retest = bool(item.get("has_retest"))
    market_confirmation = bool(item.get("market_confirmation"))
    risk_level = str(item.get("risk_level") or "unknown").strip().lower()
    action_hint = str(item.get("action_hint") or "unknown").strip().lower()
    message_intent = str(item.get("message_intent") or "")

    decision = "ignore"
    priority = 0

    high_risk = risk_level in HIGH_RISK_LEVELS
    medium_risk = risk_level in MEDIUM_RISK_LEVELS
    blocking_action = action_hint in BLOCKING_ACTION_HINTS
    wait_action = action_hint in WAIT_ACTION_HINTS
    observe_action = action_hint in OBSERVE_ACTION_HINTS

    if high_risk or has_any(risk_flags, BLOCKING_RISKS):
        decision = "blocked_risk"
        priority = 95

    elif blocking_action and (
        has_any(risk_flags, LIQUIDITY_RISKS)
        or has_any(risk_flags, NO_CONFIRMATION_RISKS)
        or final_score < MIN_OBSERVE_SCORE
    ):
        decision = "blocked_risk"
        priority = 85

    elif has_any(risk_flags, LIQUIDITY_RISKS) and final_score < MIN_OBSERVE_SCORE:
        decision = "blocked_risk"
        priority = 75

    elif wait_action or has_any(risk_flags, CONFIRMATION_FLAGS) or has_any(message_flags, CONFIRMATION_FLAGS):
        if has_retest and final_score >= MIN_OBSERVE_SCORE and market_confirmation:
            decision = "wait_confirmation"
            priority = 65
        else:
            decision = "wait_retest"
            priority = 60

    elif not has_retest and status in {"ждать ретест"}:
        decision = "wait_retest"
        priority = 58

    elif (
        status in {"движение возможно", "ждать ретест"}
        and final_score >= MIN_CANDIDATE_SCORE
        and market_score >= MIN_MARKET_CONFIRMATION_SCORE
        and market_confirmation
        and has_retest
        and not blocking_action
        and not medium_risk
    ):
        decision = "candidate"
        priority = 80

    elif observe_action and final_score >= MIN_OBSERVE_SCORE:
        decision = "observe"
        priority = 55

    elif status == "только наблюдать" and final_score >= MIN_OBSERVE_SCORE:
        decision = "observe"
        priority = 50

    elif (
        final_score >= MIN_OBSERVE_SCORE
        and market_score >= MIN_MARKET_CONFIRMATION_SCORE
        and market_confirmation
        and not blocking_action
    ):
        decision = "observe"
        priority = 45

    elif message_intent == "neutral" and telegram_score < 30:
        decision = "ignore"
        priority = 10

    else:
        decision = "ignore"
        priority = 20

    block_reasons = build_block_reasons(
        decision=decision,
        risk_flags=risk_flags,
        message_flags=message_flags,
        market_confirmation=market_confirmation,
        has_retest=has_retest,
        action_hint=action_hint,
    )
    risk_explanation = build_risk_explanation(
        decision=decision,
        risk_level=risk_level,
        block_reasons=block_reasons,
    )
    manager_note = build_manager_note(
        item=item,
        decision=decision,
        risk_level=risk_level,
        block_reasons=block_reasons,
    )
    recommended_next_step = build_recommended_next_step(
        decision=decision,
        risk_flags=risk_flags,
        message_flags=message_flags,
        has_retest=has_retest,
    )

    return {
        "source": "scanner_agent_decision",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "orders_enabled": False,
        "order_execution_allowed": False,
        "trading_enabled": False,
        "decision": decision,
        "priority": priority,
        "source_group": source_group,
        "ticker": item.get("ticker"),
        "pair": item.get("pair"),
        "exchange": item.get("exchange"),
        "suggested_status": status,
        "final_score": final_score,
        "telegram_score": telegram_score,
        "market_score": market_score,
        "risk_adjustment": item.get("risk_adjustment"),
        "risk_level": risk_level,
        "action_hint": action_hint,
        "risk_flags": risk_flags,
        "has_retest": has_retest,
        "market_confirmation": market_confirmation,
        "message_intent": item.get("message_intent"),
        "message_quality_score": item.get("message_quality_score"),
        "message_score_adjustment": item.get("message_score_adjustment"),
        "message_risk_flags": message_flags,
        "message_reasons": item.get("message_reasons", []),
        "message_intent_counts": item.get("message_intent_counts", {}),
        "block_reasons": block_reasons,
        "risk_explanation": risk_explanation,
        "manager_note": manager_note,
        "recommended_next_step": recommended_next_step,
        "reasons": build_decision_reason(
            item=item,
            decision=decision,
            risk_flags=risk_flags,
            message_flags=message_flags,
        ),
        "safe_note": (
            "This is an analytical decision only. "
            "It is not a trading entry and it cannot create orders."
        ),
    }


def build_not_ready_payload(export_payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": "scanner_agent_decision",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_file": str(INPUT_PATH),
        "output_file": str(OUTPUT_PATH),
        "analytical_only": True,
        "orders_enabled": False,
        "order_execution_allowed": False,
        "trading_enabled": False,
        "safe_to_continue": False,
        "decisions": [],
        "total_decisions": 0,
        "summary_by_decision": {},
        "blockers": export_payload.get("blockers", []) or ["agent_export_not_ready"],
        "warnings": export_payload.get("warnings", []),
        "error": export_payload.get("error"),
        "disclaimer": (
            "Telegram/social signal is not a trading entry. "
            "This decision layer is analytical only. "
            "No orders are created."
        ),
    }


def count_by_decision(decisions: List[Dict[str, Any]]) -> Dict[str, int]:
    summary: Dict[str, int] = {}

    for item in decisions:
        decision = str(item.get("decision", "unknown"))
        summary[decision] = summary.get(decision, 0) + 1

    return dict(sorted(summary.items()))


def build_decision_payload(export_payload: Dict[str, Any]) -> Dict[str, Any]:
    if export_payload.get("error"):
        return build_not_ready_payload(export_payload)

    candidates = export_payload.get("candidates", [])
    watchlist_candidates = export_payload.get("watchlist_candidates", [])

    if not isinstance(candidates, list):
        candidates = []

    if not isinstance(watchlist_candidates, list):
        watchlist_candidates = []

    decisions: List[Dict[str, Any]] = []

    for item in candidates:
        if isinstance(item, dict):
            source_group = str(item.get("export_group") or "candidate")
            decisions.append(decide_item(item, source_group=source_group))

    for item in watchlist_candidates:
        if isinstance(item, dict):
            source_group = str(item.get("export_group") or "watchlist")
            decisions.append(decide_item(item, source_group=source_group))

    decisions.sort(
        key=lambda item: (
            int(item.get("priority", 0)),
            float(item.get("final_score") or 0.0),
        ),
        reverse=True,
    )

    return {
        "source": "scanner_agent_decision",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_file": str(INPUT_PATH),
        "output_file": str(OUTPUT_PATH),
        "input_source": export_payload.get("source"),
        "input_created_at": export_payload.get("created_at"),
        "analytical_only": True,
        "orders_enabled": False,
        "order_execution_allowed": False,
        "trading_enabled": False,
        "safe_to_continue": True,
        "total_input_candidates": len(candidates),
        "total_input_watchlist_candidates": len(watchlist_candidates),
        "total_decisions": len(decisions),
        "summary_by_decision": count_by_decision(decisions),
        "decisions": decisions,
        "blockers": [],
        "warnings": [],
        "disclaimer": (
            "Telegram/social signal is not a trading entry. "
            "This decision layer is analytical only. "
            "No orders are created."
        ),
    }


def save_decision_payload(payload: Dict[str, Any], path: Path = OUTPUT_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return path


def format_flags(flags: Any) -> str:
    if isinstance(flags, list):
        return ", ".join(str(item) for item in flags) or "none"

    if flags:
        return str(flags)

    return "none"


def print_decision_item(item: Dict[str, Any]) -> None:
    print(
        str(item.get("pair")).ljust(10),
        "decision=" + str(item.get("decision")),
        "priority=" + str(item.get("priority")),
        "status=" + str(item.get("suggested_status")),
        "final=" + str(item.get("final_score")),
        "market=" + str(item.get("market_score")),
        "telegram=" + str(item.get("telegram_score")),
        "retest=" + str(item.get("has_retest")),
        "risks=" + format_flags(item.get("risk_flags")),
        "message=" + str(item.get("message_intent")),
    )


def print_decision_summary(payload: Dict[str, Any], output_path: Path) -> None:
    print("SCANNER AGENT DECISION")
    print("======================")
    print("Mode: analytical only")
    print("Orders enabled:", payload.get("order_execution_allowed"))
    print("Trading enabled:", payload.get("trading_enabled"))
    print("Input file:", payload.get("input_file"))
    print("Output file:", output_path)
    print()

    if payload.get("error"):
        print("[FAIL]", payload.get("error"))

    print("SUMMARY")
    print("=======")
    print("Safe to continue:", payload.get("safe_to_continue"))
    print("Input candidates:", payload.get("total_input_candidates", 0))
    print("Input watchlist candidates:", payload.get("total_input_watchlist_candidates", 0))
    print("Total decisions:", payload.get("total_decisions", 0))
    print("Summary by decision:", payload.get("summary_by_decision", {}))

    if payload.get("blockers"):
        print("Blockers:", ", ".join(str(item) for item in payload["blockers"]))
    else:
        print("Blockers: none")

    if payload.get("warnings"):
        print("Warnings:", ", ".join(str(item) for item in payload["warnings"]))
    else:
        print("Warnings: none")

    print()
    print("DECISIONS")
    print("=========")

    decisions = payload.get("decisions", [])

    if not decisions:
        print("No decisions.")
    else:
        for item in decisions:
            print_decision_item(item)

    print()
    print("SAFETY")
    print("======")
    print("[OK] This decision layer did not create orders.")
    print("[OK] This decision layer did not start trading bot.")
    print("[OK] This decision layer did not call Binance API.")
    print("[OK] This decision layer used only scanner_agent_export.json.")

    print()
    print("NEXT STEP")
    print("=========")

    if not decisions:
        print("No analytical decisions found. Add stronger real Telegram messages or rerun scanner.")
        return

    print("Decision JSON is ready for the future agent layer.")
    print("Keep order execution disabled until a separate manual approval layer exists.")


def main() -> None:
    export_payload = load_agent_export()
    decision_payload = build_decision_payload(export_payload)
    output_path = save_decision_payload(decision_payload)
    print_decision_summary(decision_payload, output_path)


if __name__ == "__main__":
    main()
