import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from scanner_real_channels import REAL_CHANNELS


QUALITY_JSON_PATH = Path("reports") / "telegram_channel_quality_report.json"
OUTPUT_JSON_PATH = Path("reports") / "telegram_channel_config_recommendations.json"
OUTPUT_TXT_PATH = Path("reports") / "telegram_channel_config_recommendations.txt"


def safe_float(value: Any, default: float = 1.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 50) -> int:
    try:
        return int(value)
    except Exception:
        return default


def normalize_channel(channel: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "username": str(channel.get("username", "")).strip().lstrip("@"),
        "title": str(channel.get("title", "")).strip(),
        "enabled": bool(channel.get("enabled", True)),
        "weight": safe_float(channel.get("weight", 1.0), 1.0),
        "authority_score": safe_int(channel.get("authority_score", 50), 50),
    }


def load_json_file(path: Path) -> Dict[str, Any]:
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


def index_quality_channels(quality_payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}

    channels = quality_payload.get("channels", [])

    if not isinstance(channels, list):
        return result

    for item in channels:
        if not isinstance(item, dict):
            continue

        username = str(item.get("channel", "")).strip().lstrip("@")

        if username:
            result[username] = item

    return result


def calculate_recommended_settings(
    current_channel: Dict[str, Any],
    quality_item: Dict[str, Any] | None,
) -> Dict[str, Any]:
    username = current_channel["username"]
    current_weight = safe_float(current_channel.get("weight", 1.0), 1.0)
    current_authority = safe_int(current_channel.get("authority_score", 50), 50)

    if quality_item is None:
        return {
            "username": username,
            "title": current_channel.get("title") or username,
            "current_enabled": current_channel.get("enabled"),
            "current_weight": current_weight,
            "current_authority_score": current_authority,
            "quality_score": None,
            "quality_recommendation": None,
            "final_recommendation": "disable",
            "recommended_enabled": False,
            "recommended_weight": 0.3,
            "recommended_authority_score": max(20, min(current_authority, 40)),
            "reason": "channel_has_no_usable_recent_messages_in_quality_report",
            "reasons": [
                "configured_channel_missing_from_quality_report",
                "no_recent_analyzable_messages",
            ],
            "warnings": [
                "manual_review_required_before_disabling",
            ],
        }

    quality_score = safe_int(quality_item.get("quality_score"), 0)
    quality_recommendation = str(quality_item.get("recommendation", "watch")).strip()
    fresh_24h = safe_int(quality_item.get("fresh_messages_24h"), 0)
    messages = safe_int(quality_item.get("messages"), 0)
    unique_tickers = quality_item.get("unique_tickers", [])
    quality_warnings = quality_item.get("warnings", [])

    if not isinstance(unique_tickers, list):
        unique_tickers = []

    if not isinstance(quality_warnings, list):
        quality_warnings = []

    if quality_recommendation == "keep" and quality_score >= 70:
        final_recommendation = "keep"
        recommended_enabled = True
        recommended_weight = current_weight
        recommended_authority = current_authority
        reason = "channel_quality_is_good"

    elif quality_recommendation == "watch":
        final_recommendation = "watch"
        recommended_enabled = True
        recommended_weight = max(0.7, round(min(current_weight, 0.9), 2))
        recommended_authority = max(45, min(current_authority, 60))
        reason = "channel_is_useful_but_should_have_lower_weight"

    else:
        final_recommendation = "disable"
        recommended_enabled = False
        recommended_weight = 0.3
        recommended_authority = max(20, min(current_authority, 40))
        reason = "channel_quality_is_too_low_or_stale"

    reasons = [
        "quality_score=" + str(quality_score),
        "quality_recommendation=" + quality_recommendation,
        "messages=" + str(messages),
        "fresh_24h=" + str(fresh_24h),
        "tickers=" + ",".join(str(ticker) for ticker in unique_tickers) if unique_tickers else "tickers=none",
    ]

    warnings = list(quality_warnings)

    if final_recommendation == "disable":
        warnings.append("manual_review_required_before_disabling")

    if final_recommendation == "watch":
        warnings.append("manual_review_recommended_before_changing_weight")

    return {
        "username": username,
        "title": current_channel.get("title") or quality_item.get("channel_title") or username,
        "current_enabled": current_channel.get("enabled"),
        "current_weight": current_weight,
        "current_authority_score": current_authority,
        "quality_score": quality_score,
        "quality_recommendation": quality_recommendation,
        "final_recommendation": final_recommendation,
        "recommended_enabled": recommended_enabled,
        "recommended_weight": recommended_weight,
        "recommended_authority_score": recommended_authority,
        "reason": reason,
        "reasons": reasons,
        "warnings": sorted(set(str(item) for item in warnings if str(item).strip())),
    }


def build_recommended_real_channels_py(recommendations: List[Dict[str, Any]]) -> str:
    lines: List[str] = []

    lines.append("from typing import Any, Dict, List")
    lines.append("")
    lines.append("")
    lines.append("# Real public Telegram channels for analytical social scanner.")
    lines.append("#")
    lines.append("# Generated recommendation preview.")
    lines.append("# Review manually before replacing scanner_real_channels.py.")
    lines.append("#")
    lines.append("# Safety:")
    lines.append("# - analytical only;")
    lines.append("# - no orders;")
    lines.append("# - no trading bot launch;")
    lines.append("# - no private-channel bypassing.")
    lines.append("")
    lines.append("")
    lines.append("REAL_CHANNELS: List[Dict[str, Any]] = [")

    for item in recommendations:
        lines.append("    {")
        lines.append(f'        "username": "{item.get("username")}",')
        lines.append(f'        "title": "{item.get("title")}",')
        lines.append(f'        "enabled": {str(bool(item.get("recommended_enabled")))},')
        lines.append(f'        "weight": {item.get("recommended_weight")},')
        lines.append(f'        "authority_score": {item.get("recommended_authority_score")},')
        lines.append(f'        # final_recommendation={item.get("final_recommendation")}')
        lines.append(f'        # reason={item.get("reason")}')
        lines.append("    },")

    lines.append("]")

    return "\n".join(lines)


def build_payload() -> Dict[str, Any]:
    loaded = load_json_file(QUALITY_JSON_PATH)

    if not loaded["ok"]:
        return {
            "source": "telegram_channel_config_recommendations",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "analytical_only": True,
            "orders_enabled": False,
            "trading_enabled": False,
            "telegram_messages_read": False,
            "scanner_real_channels_modified": False,
            "safe_to_continue": False,
            "input_file": str(QUALITY_JSON_PATH),
            "output_json": str(OUTPUT_JSON_PATH),
            "output_txt": str(OUTPUT_TXT_PATH),
            "recommendations": [],
            "keep": 0,
            "watch": 0,
            "disable": 0,
            "blockers": ["quality_report_not_ready"],
            "warnings": [],
            "error": loaded["error"],
        }

    quality_payload = loaded["data"]
    quality_index = index_quality_channels(quality_payload)

    current_channels = [
        normalize_channel(channel)
        for channel in REAL_CHANNELS
    ]

    recommendations = [
        calculate_recommended_settings(
            current_channel=channel,
            quality_item=quality_index.get(channel["username"]),
        )
        for channel in current_channels
    ]

    keep_count = sum(1 for item in recommendations if item.get("final_recommendation") == "keep")
    watch_count = sum(1 for item in recommendations if item.get("final_recommendation") == "watch")
    disable_count = sum(1 for item in recommendations if item.get("final_recommendation") == "disable")

    full_preview = build_recommended_real_channels_py(recommendations)

    return {
        "source": "telegram_channel_config_recommendations",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "telegram_messages_read": False,
        "scanner_real_channels_modified": False,
        "safe_to_continue": True,
        "input_file": str(QUALITY_JSON_PATH),
        "output_json": str(OUTPUT_JSON_PATH),
        "output_txt": str(OUTPUT_TXT_PATH),
        "quality_report_created_at": quality_payload.get("created_at"),
        "quality_channels_analyzed": quality_payload.get("channels_analyzed"),
        "current_real_channels": len(current_channels),
        "recommendations": recommendations,
        "keep": keep_count,
        "watch": watch_count,
        "disable": disable_count,
        "recommended_scanner_real_channels_py": full_preview,
        "blockers": [],
        "warnings": [],
        "disclaimer": (
            "This report only recommends scanner_real_channels.py settings. "
            "It does not modify files, does not read Telegram, does not call Binance API, "
            "does not create orders, and does not start trading."
        ),
    }


def save_json_report(payload: Dict[str, Any], path: Path = OUTPUT_JSON_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def build_text_report(payload: Dict[str, Any]) -> str:
    lines: List[str] = []

    lines.append("TELEGRAM CHANNEL CONFIG RECOMMENDATIONS")
    lines.append("=======================================")
    lines.append(f"Created at: {payload.get('created_at')}")
    lines.append("Mode: analytical only")
    lines.append(f"Safe to continue: {payload.get('safe_to_continue')}")
    lines.append(f"scanner_real_channels.py modified: {payload.get('scanner_real_channels_modified')}")
    lines.append("")
    lines.append("SUMMARY")
    lines.append("=======")
    lines.append(f"Current real channels: {payload.get('current_real_channels')}")
    lines.append(f"Quality channels analyzed: {payload.get('quality_channels_analyzed')}")
    lines.append(f"Keep: {payload.get('keep')}")
    lines.append(f"Watch: {payload.get('watch')}")
    lines.append(f"Disable: {payload.get('disable')}")
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
    lines.append("CHANNEL RECOMMENDATIONS")
    lines.append("=======================")

    recommendations = payload.get("recommendations", [])

    if not recommendations:
        lines.append("No recommendations.")
    else:
        for item in recommendations:
            lines.append("")
            lines.append(f"@{item.get('username')}")
            lines.append("-" * (len(str(item.get("username"))) + 1))
            lines.append(f"Title: {item.get('title')}")
            lines.append(f"Final recommendation: {item.get('final_recommendation')}")
            lines.append(f"Reason: {item.get('reason')}")
            lines.append(f"Current enabled: {item.get('current_enabled')}")
            lines.append(f"Recommended enabled: {item.get('recommended_enabled')}")
            lines.append(f"Current weight: {item.get('current_weight')}")
            lines.append(f"Recommended weight: {item.get('recommended_weight')}")
            lines.append(f"Current authority: {item.get('current_authority_score')}")
            lines.append(f"Recommended authority: {item.get('recommended_authority_score')}")
            lines.append(f"Quality score: {item.get('quality_score')}")
            lines.append(f"Quality recommendation: {item.get('quality_recommendation')}")

            if item.get("reasons"):
                lines.append("Reasons:")
                for reason in item.get("reasons", []):
                    lines.append("- " + str(reason))

            if item.get("warnings"):
                lines.append("Warnings:")
                for warning in item.get("warnings", []):
                    lines.append("- " + str(warning))

    lines.append("")
    lines.append("RECOMMENDED scanner_real_channels.py PREVIEW")
    lines.append("============================================")
    lines.append(str(payload.get("recommended_scanner_real_channels_py", "")))
    lines.append("")
    lines.append("SAFETY")
    lines.append("======")
    lines.append("[OK] This recommendation report did not modify scanner_real_channels.py.")
    lines.append("[OK] This recommendation report did not read Telegram.")
    lines.append("[OK] This recommendation report did not call Binance API.")
    lines.append("[OK] This recommendation report did not create orders.")
    lines.append("[OK] Apply recommendations manually only after review.")
    lines.append("")

    return "\n".join(lines)


def save_text_report(payload: Dict[str, Any], path: Path = OUTPUT_TXT_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(build_text_report(payload), encoding="utf-8")
    return path


def print_summary(payload: Dict[str, Any], json_path: Path, txt_path: Path) -> None:
    print("TELEGRAM CHANNEL CONFIG RECOMMENDATIONS")
    print("=======================================")
    print("Mode: analytical only")
    print("Orders enabled:", payload.get("orders_enabled"))
    print("Trading enabled:", payload.get("trading_enabled"))
    print("Telegram messages read:", payload.get("telegram_messages_read"))
    print("scanner_real_channels.py modified:", payload.get("scanner_real_channels_modified"))
    print("Safe to continue:", payload.get("safe_to_continue"))
    print("JSON output:", json_path)
    print("TXT output:", txt_path)
    print()

    print("SUMMARY")
    print("=======")
    print("Current real channels:", payload.get("current_real_channels"))
    print("Keep:", payload.get("keep"))
    print("Watch:", payload.get("watch"))
    print("Disable:", payload.get("disable"))

    blockers = payload.get("blockers", [])
    warnings = payload.get("warnings", [])

    print("Blockers:", ", ".join(str(x) for x in blockers) if blockers else "none")
    print("Warnings:", ", ".join(str(x) for x in warnings) if warnings else "none")
    print()

    print("RECOMMENDATIONS")
    print("===============")

    recommendations = payload.get("recommendations", [])

    if not recommendations:
        print("No recommendations.")
    else:
        for item in recommendations:
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
    payload = build_payload()
    json_path = save_json_report(payload)
    txt_path = save_text_report(payload)
    print_summary(payload, json_path, txt_path)


if __name__ == "__main__":
    main()
