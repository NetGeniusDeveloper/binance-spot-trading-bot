import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from scanner_agent_risk_filter_backtest import (
    SCENARIOS_PATH,
    as_list,
    format_list,
    normalize_list,
    run_synthetic_scenarios,
)


REPORTS_DIR = Path("reports")

OUTPUT_JSON_PATH = REPORTS_DIR / "scanner_agent_scenario_matrix_report.json"
OUTPUT_TXT_PATH = REPORTS_DIR / "scanner_agent_scenario_matrix_report.txt"


def count_by_field(items: List[Dict[str, Any]], field_name: str) -> Dict[str, int]:
    result: Dict[str, int] = {}

    for item in items:
        key = str(item.get(field_name) or "unknown")
        result[key] = result.get(key, 0) + 1

    return dict(sorted(result.items()))


def build_matrix_rows(synthetic_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for scenario in as_list(synthetic_payload.get("synthetic_scenarios")):
        if not isinstance(scenario, dict):
            continue

        rows.append(
            {
                "scenario_name": scenario.get("scenario_name"),
                "expected_buckets": normalize_list(scenario.get("expected_buckets")),
                "actual_bucket": scenario.get("actual_bucket"),
                "result": "PASS" if scenario.get("passed") else "FAIL",
                "passed": bool(scenario.get("passed")),
                "runtime_safe": bool(scenario.get("runtime_safe")),
                "decision": scenario.get("decision"),
                "pair": scenario.get("pair"),
                "risk_level": scenario.get("risk_level"),
                "risk_flags": normalize_list(scenario.get("risk_flags")),
                "dangerous_runtime_flags": scenario.get("dangerous_runtime_flags", {}),
                "note": scenario.get("note"),
            }
        )

    return rows


def build_payload() -> Dict[str, Any]:
    synthetic = run_synthetic_scenarios()
    rows = build_matrix_rows(synthetic)

    failed_rows = [
        row
        for row in rows
        if not row.get("passed")
    ]

    unsafe_rows = [
        row
        for row in rows
        if not row.get("runtime_safe")
    ]

    blockers: List[str] = []

    if not synthetic.get("synthetic_scenarios_ok"):
        blockers.append("synthetic_scenarios_failed")

    if unsafe_rows:
        blockers.append("synthetic_scenarios_runtime_unsafe")

    return {
        "source": "scanner_agent_scenario_matrix_report",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "scenario_source": str(SCENARIOS_PATH),
        "output_json": str(OUTPUT_JSON_PATH),
        "output_txt": str(OUTPUT_TXT_PATH),
        "analytical_only": True,
        "orders_enabled": False,
        "order_execution_allowed": False,
        "trading_enabled": False,
        "telegram_sending": False,
        "binance_private_api_used": False,
        "safe_to_continue": not blockers,
        "synthetic_scenarios_ok": bool(synthetic.get("synthetic_scenarios_ok")),
        "synthetic_scenario_source_error": synthetic.get("synthetic_scenario_source_error"),
        "scenario_count": len(rows),
        "failed_count": len(failed_rows),
        "unsafe_runtime_count": len(unsafe_rows),
        "summary_by_result": count_by_field(rows, "result"),
        "summary_by_actual_bucket": count_by_field(rows, "actual_bucket"),
        "matrix_rows": rows,
        "failed_rows": failed_rows,
        "unsafe_runtime_rows": unsafe_rows,
        "blockers": blockers,
        "warnings": [],
        "disclaimer": (
            "This report is analytical only. It reads synthetic risk-filter scenarios, "
            "does not create orders, does not start trading, does not call Binance private API, "
            "and does not send Telegram messages."
        ),
    }


def format_table_cell(value: Any, max_len: int = 42) -> str:
    if isinstance(value, list):
        text = ", ".join(str(item) for item in value)
    elif isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)

    text = text.replace("\n", " ").strip()

    if len(text) > max_len:
        return text[: max_len - 3] + "..."

    return text


def build_table(rows: List[Dict[str, Any]]) -> List[str]:
    columns = [
        ("scenario_name", "scenario_name", 40),
        ("expected", "expected_buckets", 34),
        ("actual", "actual_bucket", 30),
        ("result", "result", 8),
        ("runtime_safe", "runtime_safe", 12),
        ("risk_flags", "risk_flags", 44),
    ]

    rendered_rows: List[List[str]] = []

    header = [
        title
        for title, _, _ in columns
    ]
    rendered_rows.append(header)

    for row in rows:
        rendered_rows.append([
            format_table_cell(row.get(field), max_len=max_len)
            for _, field, max_len in columns
        ])

    widths = [
        max(len(rendered[index]) for rendered in rendered_rows)
        for index in range(len(columns))
    ]

    lines: List[str] = []

    for row_index, rendered in enumerate(rendered_rows):
        line = " | ".join(
            rendered[index].ljust(widths[index])
            for index in range(len(columns))
        )
        lines.append(line)

        if row_index == 0:
            lines.append("-+-".join("-" * width for width in widths))

    return lines


def build_text_report(payload: Dict[str, Any]) -> str:
    lines: List[str] = []

    lines.append("SCANNER AGENT SCENARIO MATRIX REPORT")
    lines.append("====================================")
    lines.append(f"Created at: {payload.get('created_at')}")
    lines.append(f"Scenario source: {payload.get('scenario_source')}")
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
    lines.append("SUMMARY")
    lines.append("=======")
    lines.append(f"Safe to continue: {payload.get('safe_to_continue')}")
    lines.append(f"Synthetic scenarios OK: {payload.get('synthetic_scenarios_ok')}")
    lines.append(f"Scenario source error: {payload.get('synthetic_scenario_source_error')}")
    lines.append(f"Scenario count: {payload.get('scenario_count')}")
    lines.append(f"Failed count: {payload.get('failed_count')}")
    lines.append(f"Unsafe runtime count: {payload.get('unsafe_runtime_count')}")
    lines.append(f"Summary by result: {payload.get('summary_by_result')}")
    lines.append(f"Summary by actual bucket: {payload.get('summary_by_actual_bucket')}")
    lines.append(f"Blockers: {format_list(payload.get('blockers'))}")
    lines.append(f"Warnings: {format_list(payload.get('warnings'))}")
    lines.append("")
    lines.append("SCENARIO MATRIX")
    lines.append("===============")

    rows = as_list(payload.get("matrix_rows"))

    if rows:
        lines.extend(build_table(rows))
    else:
        lines.append("No scenario rows.")

    lines.append("")
    lines.append("FINAL NOTE")
    lines.append("==========")
    lines.append("PASS means the scenario matched expected bucket and runtime stayed safe.")
    lines.append("ENTRY_ALLOWED_ANALYTICAL_ONLY is still not permission to trade.")
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
    print("SCANNER AGENT SCENARIO MATRIX REPORT")
    print("====================================")
    print("Mode: analytical only")
    print("Scenario source:", payload.get("scenario_source"))
    print("JSON output:", json_path)
    print("TXT output:", txt_path)
    print()

    print("SUMMARY")
    print("=======")
    print("Safe to continue:", payload.get("safe_to_continue"))
    print("Synthetic scenarios OK:", payload.get("synthetic_scenarios_ok"))
    print("Scenario count:", payload.get("scenario_count"))
    print("Failed count:", payload.get("failed_count"))
    print("Unsafe runtime count:", payload.get("unsafe_runtime_count"))
    print("Summary by result:", payload.get("summary_by_result"))
    print("Summary by actual bucket:", payload.get("summary_by_actual_bucket"))

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
    print("[OK] This matrix report did not create orders.")
    print("[OK] This matrix report did not start trading bot.")
    print("[OK] This matrix report did not call Binance private API.")
    print("[OK] This matrix report did not send Telegram messages.")
    print("[OK] This matrix report only reads synthetic scenarios.")


def main() -> None:
    payload = build_payload()
    json_path = save_json(payload)
    txt_path = save_text(build_text_report(payload))
    print_summary(payload, json_path, txt_path)


if __name__ == "__main__":
    main()
