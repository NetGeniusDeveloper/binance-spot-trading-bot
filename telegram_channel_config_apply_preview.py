import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


RECOMMENDATIONS_JSON_PATH = Path("reports") / "telegram_channel_config_recommendations.json"
CURRENT_CONFIG_PATH = Path("scanner_real_channels.py")

OUTPUT_RECOMMENDED_PY_PATH = Path("reports") / "scanner_real_channels.recommended.py"
OUTPUT_JSON_PATH = Path("reports") / "telegram_channel_config_apply_preview.json"
OUTPUT_TXT_PATH = Path("reports") / "telegram_channel_config_apply_preview.txt"


def load_text_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "ok": False,
            "path": str(path),
            "error": f"File not found: {path}",
            "text": "",
        }

    try:
        return {
            "ok": True,
            "path": str(path),
            "error": None,
            "text": path.read_text(encoding="utf-8"),
        }
    except OSError as ex:
        return {
            "ok": False,
            "path": str(path),
            "error": f"Cannot read file: {ex}",
            "text": "",
        }


def load_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "ok": False,
            "path": str(path),
            "error": f"File not found: {path}",
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
            "error": f"Invalid JSON: {ex}",
            "data": {},
        }
    except OSError as ex:
        return {
            "ok": False,
            "path": str(path),
            "error": f"Cannot read file: {ex}",
            "data": {},
        }


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value

    return []


def build_not_ready_payload(error: str) -> Dict[str, Any]:
    return {
        "source": "telegram_channel_config_apply_preview",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "telegram_messages_read": False,
        "binance_api_used": False,
        "scanner_real_channels_modified": False,
        "recommended_file_created": False,
        "safe_to_continue": False,
        "input_recommendations_json": str(RECOMMENDATIONS_JSON_PATH),
        "current_config_path": str(CURRENT_CONFIG_PATH),
        "output_recommended_py": str(OUTPUT_RECOMMENDED_PY_PATH),
        "output_json": str(OUTPUT_JSON_PATH),
        "output_txt": str(OUTPUT_TXT_PATH),
        "recommendations_count": 0,
        "keep": 0,
        "watch": 0,
        "disable": 0,
        "blockers": ["recommendations_not_ready"],
        "warnings": [],
        "error": error,
        "disclaimer": (
            "This preview does not modify scanner_real_channels.py. "
            "It only writes a recommended copy into reports/ for manual review."
        ),
    }


def build_preview_payload() -> Dict[str, Any]:
    loaded_recommendations = load_json_file(RECOMMENDATIONS_JSON_PATH)

    if not loaded_recommendations["ok"]:
        return build_not_ready_payload(str(loaded_recommendations["error"]))

    recommendations_payload = loaded_recommendations["data"]

    if not recommendations_payload.get("safe_to_continue"):
        return build_not_ready_payload("Recommendations payload is not safe to continue.")

    recommended_code = str(
        recommendations_payload.get("recommended_scanner_real_channels_py", "")
    ).strip()

    if not recommended_code:
        return build_not_ready_payload("recommended_scanner_real_channels_py is empty.")

    current_config = load_text_file(CURRENT_CONFIG_PATH)

    if not current_config["ok"]:
        return build_not_ready_payload(str(current_config["error"]))

    recommendations = safe_list(recommendations_payload.get("recommendations"))

    keep_count = sum(
        1 for item in recommendations
        if isinstance(item, dict) and item.get("final_recommendation") == "keep"
    )
    watch_count = sum(
        1 for item in recommendations
        if isinstance(item, dict) and item.get("final_recommendation") == "watch"
    )
    disable_count = sum(
        1 for item in recommendations
        if isinstance(item, dict) and item.get("final_recommendation") == "disable"
    )

    current_hash = sha256_text(str(current_config.get("text", "")))
    recommended_hash = sha256_text(recommended_code)

    changes_detected = current_hash != recommended_hash

    channel_actions = []

    for item in recommendations:
        if not isinstance(item, dict):
            continue

        channel_actions.append({
            "username": item.get("username"),
            "title": item.get("title"),
            "final_recommendation": item.get("final_recommendation"),
            "current_enabled": item.get("current_enabled"),
            "recommended_enabled": item.get("recommended_enabled"),
            "current_weight": item.get("current_weight"),
            "recommended_weight": item.get("recommended_weight"),
            "current_authority_score": item.get("current_authority_score"),
            "recommended_authority_score": item.get("recommended_authority_score"),
            "quality_score": item.get("quality_score"),
            "reason": item.get("reason"),
            "warnings": item.get("warnings", []),
        })

    return {
        "source": "telegram_channel_config_apply_preview",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "telegram_messages_read": False,
        "binance_api_used": False,
        "scanner_real_channels_modified": False,
        "recommended_file_created": False,
        "safe_to_continue": True,
        "input_recommendations_json": str(RECOMMENDATIONS_JSON_PATH),
        "current_config_path": str(CURRENT_CONFIG_PATH),
        "output_recommended_py": str(OUTPUT_RECOMMENDED_PY_PATH),
        "output_json": str(OUTPUT_JSON_PATH),
        "output_txt": str(OUTPUT_TXT_PATH),
        "recommendations_created_at": recommendations_payload.get("created_at"),
        "recommendations_count": len(recommendations),
        "keep": keep_count,
        "watch": watch_count,
        "disable": disable_count,
        "current_config_sha256": current_hash,
        "recommended_config_sha256": recommended_hash,
        "changes_detected": changes_detected,
        "channel_actions": channel_actions,
        "recommended_code": recommended_code,
        "blockers": [],
        "warnings": [],
        "disclaimer": (
            "This preview does not modify scanner_real_channels.py. "
            "It only writes a recommended copy into reports/ for manual review."
        ),
    }


def save_recommended_py(payload: Dict[str, Any]) -> Path | None:
    if not payload.get("safe_to_continue"):
        return None

    code = str(payload.get("recommended_code", "")).rstrip() + "\n"

    OUTPUT_RECOMMENDED_PY_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_RECOMMENDED_PY_PATH.write_text(code, encoding="utf-8")

    payload["recommended_file_created"] = True

    return OUTPUT_RECOMMENDED_PY_PATH


def save_json_report(payload: Dict[str, Any], path: Path = OUTPUT_JSON_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def build_text_report(payload: Dict[str, Any]) -> str:
    lines: List[str] = []

    lines.append("TELEGRAM CHANNEL CONFIG APPLY PREVIEW")
    lines.append("=====================================")
    lines.append(f"Created at: {payload.get('created_at')}")
    lines.append("Mode: analytical only")
    lines.append(f"Safe to continue: {payload.get('safe_to_continue')}")
    lines.append(f"scanner_real_channels.py modified: {payload.get('scanner_real_channels_modified')}")
    lines.append(f"Recommended file created: {payload.get('recommended_file_created')}")
    lines.append("")
    lines.append("SUMMARY")
    lines.append("=======")
    lines.append(f"Recommendations count: {payload.get('recommendations_count')}")
    lines.append(f"Keep: {payload.get('keep')}")
    lines.append(f"Watch: {payload.get('watch')}")
    lines.append(f"Disable: {payload.get('disable')}")
    lines.append(f"Changes detected: {payload.get('changes_detected')}")
    lines.append(f"Recommended file: {payload.get('output_recommended_py')}")
    lines.append("")

    blockers = payload.get("blockers", [])
    warnings = payload.get("warnings", [])

    lines.append("BLOCKERS")
    lines.append("========")
    lines.append(", ".join(str(item) for item in blockers) if blockers else "none")
    lines.append("")
    lines.append("WARNINGS")
    lines.append("========")
    lines.append(", ".join(str(item) for item in warnings) if warnings else "none")
    lines.append("")
    lines.append("CHANNEL ACTIONS")
    lines.append("===============")

    actions = payload.get("channel_actions", [])

    if not actions:
        lines.append("No channel actions.")
    else:
        for item in actions:
            lines.append("")
            lines.append(f"@{item.get('username')}")
            lines.append("-" * (len(str(item.get("username"))) + 1))
            lines.append(f"Title: {item.get('title')}")
            lines.append(f"Final recommendation: {item.get('final_recommendation')}")
            lines.append(f"Current enabled: {item.get('current_enabled')}")
            lines.append(f"Recommended enabled: {item.get('recommended_enabled')}")
            lines.append(f"Current weight: {item.get('current_weight')}")
            lines.append(f"Recommended weight: {item.get('recommended_weight')}")
            lines.append(f"Current authority: {item.get('current_authority_score')}")
            lines.append(f"Recommended authority: {item.get('recommended_authority_score')}")
            lines.append(f"Quality score: {item.get('quality_score')}")
            lines.append(f"Reason: {item.get('reason')}")

            item_warnings = item.get("warnings", [])

            if item_warnings:
                lines.append("Warnings:")
                for warning in item_warnings:
                    lines.append("- " + str(warning))

    lines.append("")
    lines.append("NEXT MANUAL STEP")
    lines.append("================")
    lines.append("Review reports/scanner_real_channels.recommended.py.")
    lines.append("If everything is correct, replace scanner_real_channels.py manually.")
    lines.append("")
    lines.append("SAFETY")
    lines.append("======")
    lines.append("[OK] This preview did not modify scanner_real_channels.py.")
    lines.append("[OK] This preview did not read Telegram.")
    lines.append("[OK] This preview did not call Binance API.")
    lines.append("[OK] This preview did not create orders.")
    lines.append("[OK] The generated file is for manual review only.")
    lines.append("")

    return "\n".join(lines)


def save_text_report(payload: Dict[str, Any], path: Path = OUTPUT_TXT_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(build_text_report(payload), encoding="utf-8")
    return path


def print_summary(payload: Dict[str, Any], json_path: Path, txt_path: Path) -> None:
    print("TELEGRAM CHANNEL CONFIG APPLY PREVIEW")
    print("=====================================")
    print("Mode: analytical only")
    print("Orders enabled:", payload.get("orders_enabled"))
    print("Trading enabled:", payload.get("trading_enabled"))
    print("Telegram messages read:", payload.get("telegram_messages_read"))
    print("Binance API used:", payload.get("binance_api_used"))
    print("scanner_real_channels.py modified:", payload.get("scanner_real_channels_modified"))
    print("Recommended file created:", payload.get("recommended_file_created"))
    print("Safe to continue:", payload.get("safe_to_continue"))
    print("Recommended PY:", payload.get("output_recommended_py"))
    print("JSON output:", json_path)
    print("TXT output:", txt_path)
    print()

    print("SUMMARY")
    print("=======")
    print("Recommendations count:", payload.get("recommendations_count"))
    print("Keep:", payload.get("keep"))
    print("Watch:", payload.get("watch"))
    print("Disable:", payload.get("disable"))
    print("Changes detected:", payload.get("changes_detected"))

    blockers = payload.get("blockers", [])
    warnings = payload.get("warnings", [])

    print("Blockers:", ", ".join(str(x) for x in blockers) if blockers else "none")
    print("Warnings:", ", ".join(str(x) for x in warnings) if warnings else "none")
    print()

    print("CHANNEL ACTIONS")
    print("===============")

    actions = payload.get("channel_actions", [])

    if not actions:
        print("No channel actions.")
    else:
        for item in actions:
            print(
                ("@" + str(item.get("username"))).ljust(28),
                "final=" + str(item.get("final_recommendation")),
                "enabled=" + str(item.get("recommended_enabled")),
                "weight=" + str(item.get("recommended_weight")),
                "authority=" + str(item.get("recommended_authority_score")),
                "quality=" + str(item.get("quality_score")),
            )

    print()
    print("SAFETY")
    print("======")
    print("[OK] This script did not modify scanner_real_channels.py.")
    print("[OK] This script did not read Telegram.")
    print("[OK] This script did not call Binance API.")
    print("[OK] This script did not create orders.")
    print("[OK] Output is for manual review only.")


def main() -> None:
    payload = build_preview_payload()
    save_recommended_py(payload)
    json_path = save_json_report(payload)
    txt_path = save_text_report(payload)
    print_summary(payload, json_path, txt_path)


if __name__ == "__main__":
    main()
