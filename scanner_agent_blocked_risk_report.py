import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


REPORTS_DIR = Path("reports")

INPUT_PATH = REPORTS_DIR / "scanner_agent_decision.json"
OUTPUT_JSON_PATH = REPORTS_DIR / "scanner_agent_blocked_risk_report.json"
OUTPUT_TXT_PATH = REPORTS_DIR / "scanner_agent_blocked_risk_report.txt"


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "ok": False,
            "error": f"File not found: {path}",
            "data": {},
        }

    try:
        return {
            "ok": True,
            "error": None,
            "data": json.loads(path.read_text(encoding="utf-8")),
        }
    except json.JSONDecodeError as ex:
        return {
            "ok": False,
            "error": f"Invalid JSON: {ex}",
            "data": {},
        }
    except OSError as ex:
        return {
            "ok": False,
            "error": f"Cannot read file: {ex}",
            "data": {},
        }


def as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value

    return []


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


def format_score(value: Any) -> str:
    try:
        return str(round(float(value), 2))
    except Exception:
        return "n/a"


def select_blocked_items(decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    blocked: List[Dict[str, Any]] = []

    for item in decisions:
        if not isinstance(item, dict):
            continue

        decision = str(item.get("decision", "")).strip()

        if decision == "blocked_risk":
            blocked.append(item)

    blocked.sort(
        key=lambda item: (
            int(item.get("priority") or 0),
            float(item.get("final_score") or 0.0),
        ),
        reverse=True,
    )

    return blocked


def count_by_risk_level(items: List[Dict[str, Any]]) -> Dict[str, int]:
    result: Dict[str, int] = {}

    for item in items:
        risk_level = str(item.get("risk_level") or "unknown")
        result[risk_level] = result.get(risk_level, 0) + 1

    return dict(sorted(result.items()))


def count_risk_flags(items: List[Dict[str, Any]]) -> Dict[str, int]:
    result: Dict[str, int] = {}

    for item in items:
        for flag in normalize_list(item.get("risk_flags")):
            result[flag] = result.get(flag, 0) + 1

    return dict(sorted(result.items()))


def build_report_payload() -> Dict[str, Any]:
    loaded = load_json(INPUT_PATH)
    data = loaded.get("data", {})

    if not loaded.get("ok"):
        return {
            "source": "scanner_agent_blocked_risk_report",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "input_file": str(INPUT_PATH),
            "output_json": str(OUTPUT_JSON_PATH),
            "output_txt": str(OUTPUT_TXT_PATH),
            "analytical_only": True,
            "orders_enabled": False,
            "trading_enabled": False,
            "safe_to_continue": False,
            "total_decisions": 0,
            "blocked_count": 0,
            "blocked_items": [],
            "summary_by_risk_level": {},
            "summary_by_risk_flag": {},
            "blockers": ["decision_file_not_ready"],
            "warnings": [],
            "error": loaded.get("error"),
            "disclaimer": (
                "This report is analytical only. "
                "It does not create orders, does not start trading, "
                "does not call Binance API, and does not send Telegram messages."
            ),
        }

    decisions = as_list(data.get("decisions"))
    blocked_items = select_blocked_items(decisions)

    return {
        "source": "scanner_agent_blocked_risk_report",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_file": str(INPUT_PATH),
        "output_json": str(OUTPUT_JSON_PATH),
        "output_txt": str(OUTPUT_TXT_PATH),
        "input_created_at": data.get("created_at"),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "safe_to_continue": True,
        "total_decisions": len(decisions),
        "blocked_count": len(blocked_items),
        "blocked_items": blocked_items,
        "summary_by_risk_level": count_by_risk_level(blocked_items),
        "summary_by_risk_flag": count_risk_flags(blocked_items),
        "blockers": [],
        "warnings": [],
        "disclaimer": (
            "This report is analytical only. "
            "Blocked signals are not trading entries. "
            "No orders are created."
        ),
    }


def build_text_report(payload: Dict[str, Any]) -> str:
    lines: List[str] = []

    lines.append("SCANNER AGENT BLOCKED RISK REPORT")
    lines.append("=================================")
    lines.append(f"Created at: {payload.get('created_at')}")
    lines.append(f"Input file: {payload.get('input_file')}")
    lines.append("")
    lines.append("SAFETY")
    lines.append("======")
    lines.append("Analytical only: True")
    lines.append("Orders enabled: False")
    lines.append("Trading enabled: False")
    lines.append("Binance orders created: False")
    lines.append("Telegram sending: False")
    lines.append("")
    lines.append("SUMMARY")
    lines.append("=======")
    lines.append(f"Safe to continue: {payload.get('safe_to_continue')}")
    lines.append(f"Total decisions: {payload.get('total_decisions')}")
    lines.append(f"Blocked risk items: {payload.get('blocked_count')}")
    lines.append(f"Summary by risk level: {payload.get('summary_by_risk_level')}")
    lines.append(f"Summary by risk flag: {payload.get('summary_by_risk_flag')}")
    lines.append(f"Blockers: {format_list(payload.get('blockers'))}")
    lines.append(f"Warnings: {format_list(payload.get('warnings'))}")

    if payload.get("error"):
        lines.append(f"Error: {payload.get('error')}")

    lines.append("")
    lines.append("BLOCKED ITEMS")
    lines.append("=============")

    blocked_items = as_list(payload.get("blocked_items"))

    if not blocked_items:
        lines.append("No blocked risk items.")
    else:
        for item in blocked_items:
            pair = item.get("pair")
            lines.append("")
            lines.append(f"{pair} — BLOCKED")
            lines.append("-" * (len(str(pair)) + 10))
            lines.append(f"Ticker: {item.get('ticker')}")
            lines.append(f"Source group: {item.get('source_group')}")
            lines.append(f"Risk level: {item.get('risk_level')}")
            lines.append(f"Action hint: {item.get('action_hint')}")
            lines.append(
                "Scores: "
                f"final={format_score(item.get('final_score'))}, "
                f"market={format_score(item.get('market_score'))}, "
                f"telegram={format_score(item.get('telegram_score'))}, "
                f"risk_adjustment={format_score(item.get('risk_adjustment'))}"
            )
            lines.append(f"Market confirmation: {item.get('market_confirmation')}")
            lines.append(f"Retest confirmed: {item.get('has_retest')}")
            lines.append(f"Risk flags: {format_list(item.get('risk_flags'))}")
            lines.append(f"Message intent: {item.get('message_intent')}")
            lines.append(f"Message quality: {format_score(item.get('message_quality_score'))}")
            lines.append(f"Message flags: {format_list(item.get('message_risk_flags'))}")
            lines.append("")
            lines.append("Human block reasons:")

            block_reasons = normalize_list(item.get("block_reasons"))

            if block_reasons:
                for reason in block_reasons:
                    lines.append(f"- {reason}")
            else:
                lines.append("- none")

            lines.append("")
            lines.append(f"Risk explanation: {item.get('risk_explanation')}")
            lines.append(f"Manager note: {item.get('manager_note')}")
            lines.append(f"Recommended next step: {item.get('recommended_next_step')}")

    lines.append("")
    lines.append("FINAL NOTE")
    lines.append("==========")
    lines.append("Blocked risk means: do not use this signal for entry.")
    lines.append("This report is only for analytical review.")
    lines.append("No orders are created.")
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
    print("SCANNER AGENT BLOCKED RISK REPORT")
    print("=================================")
    print("Mode: analytical only")
    print("Orders enabled:", payload.get("orders_enabled"))
    print("Trading enabled:", payload.get("trading_enabled"))
    print("Input file:", payload.get("input_file"))
    print("JSON output:", json_path)
    print("TXT output:", txt_path)
    print()

    print("SUMMARY")
    print("=======")
    print("Safe to continue:", payload.get("safe_to_continue"))
    print("Total decisions:", payload.get("total_decisions"))
    print("Blocked risk items:", payload.get("blocked_count"))
    print("Summary by risk level:", payload.get("summary_by_risk_level"))
    print("Summary by risk flag:", payload.get("summary_by_risk_flag"))

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
    print("[OK] This report did not call Binance API.")
    print("[OK] This report did not send Telegram messages.")
    print("[OK] This report only reads scanner_agent_decision.json.")


def main() -> None:
    payload = build_report_payload()
    json_path = save_json(payload)
    txt_path = save_text(build_text_report(payload))
    print_summary(payload, json_path, txt_path)


if __name__ == "__main__":
    main()
