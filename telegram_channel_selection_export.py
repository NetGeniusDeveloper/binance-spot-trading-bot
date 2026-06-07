import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

from scanner_real_channels import REAL_CHANNELS


REPORTS_DIR = Path("reports")

DISCOVERY_PATH = REPORTS_DIR / "telegram_channel_discovery.json"
OUTPUT_JSON_PATH = REPORTS_DIR / "telegram_channel_selection_export.json"
OUTPUT_TXT_PATH = REPORTS_DIR / "telegram_channel_selection_export.txt"

MIN_ACTIVE_SCORE = 60
MIN_WATCH_SCORE = 35


def normalize_username(value: Any) -> str:
    text = str(value or "").strip()
    text = text.replace("https://t.me/", "")
    text = text.replace("http://t.me/", "")
    text = text.replace("t.me/", "")
    text = text.strip().lstrip("@").strip("/")

    if "/" in text:
        text = text.split("/", 1)[0]

    return text


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


def existing_real_usernames() -> Set[str]:
    usernames: Set[str] = set()

    for channel in REAL_CHANNELS:
        username = normalize_username(channel.get("username"))

        if username:
            usernames.add(username)

    return usernames


def build_channel_quality(item: Dict[str, Any]) -> Dict[str, Any]:
    score = int(item.get("score") or 0)
    verified = bool(item.get("verified", False))
    scam = bool(item.get("scam", False))
    fake = bool(item.get("fake", False))
    tickers = item.get("unique_tickers", [])
    keyword_hits = int(item.get("keyword_hits") or 0)
    messages_checked = int(item.get("messages_checked") or 0)

    if not isinstance(tickers, list):
        tickers = []

    warnings: List[str] = []
    reasons: List[str] = []

    if scam:
        warnings.append("telegram_scam_flag")

    if fake:
        warnings.append("telegram_fake_flag")

    if messages_checked <= 0:
        warnings.append("no_messages_checked")
    else:
        reasons.append("has_checked_messages")

    if tickers:
        reasons.append("has_binance_tickers")
    else:
        warnings.append("no_tickers_found")

    if keyword_hits > 0:
        reasons.append("has_crypto_keywords")
    else:
        warnings.append("no_crypto_keywords_found")

    if verified:
        reasons.append("telegram_verified")

    if score >= 90:
        tier = "A"
        weight = 1.5
        authority_score = 90
    elif score >= 80:
        tier = "B"
        weight = 1.3
        authority_score = 80
    elif score >= 70:
        tier = "C"
        weight = 1.15
        authority_score = 70
    elif score >= 60:
        tier = "D"
        weight = 1.0
        authority_score = 60
    else:
        tier = "WATCH"
        weight = 0.7
        authority_score = 45

    return {
        "tier": tier,
        "weight": weight,
        "authority_score": authority_score,
        "reasons": reasons,
        "warnings": warnings,
    }


def should_select_channel(item: Dict[str, Any]) -> bool:
    if not item.get("ok"):
        return False

    if bool(item.get("scam", False)):
        return False

    if bool(item.get("fake", False)):
        return False

    recommendation = str(item.get("recommendation", ""))
    score = int(item.get("score") or 0)

    if recommendation == "active_candidate" and score >= MIN_ACTIVE_SCORE:
        return True

    return False


def should_watch_channel(item: Dict[str, Any]) -> bool:
    if not item.get("ok"):
        return False

    if bool(item.get("scam", False)):
        return False

    if bool(item.get("fake", False)):
        return False

    recommendation = str(item.get("recommendation", ""))
    score = int(item.get("score") or 0)

    if recommendation == "watch_candidate" and score >= MIN_WATCH_SCORE:
        return True

    return False


def build_real_channel_entry(item: Dict[str, Any]) -> Dict[str, Any]:
    quality = build_channel_quality(item)

    return {
        "username": normalize_username(item.get("username")),
        "title": str(item.get("title") or item.get("username") or ""),
        "enabled": True,
        "weight": quality["weight"],
        "authority_score": quality["authority_score"],
        "discovery_score": int(item.get("score") or 0),
        "discovery_tier": quality["tier"],
        "verified": bool(item.get("verified", False)),
        "unique_tickers": item.get("unique_tickers", []),
        "keyword_hits": int(item.get("keyword_hits") or 0),
        "messages_checked": int(item.get("messages_checked") or 0),
        "selection_reasons": quality["reasons"],
        "selection_warnings": quality["warnings"],
    }


def format_python_channel_item(channel: Dict[str, Any], indent: str = "    ") -> List[str]:
    tickers = channel.get("unique_tickers", [])

    if not isinstance(tickers, list):
        tickers = []

    lines = [
        indent + "{",
        indent + f'    "username": "{channel.get("username")}",',
        indent + f'    "title": "{str(channel.get("title", "")).replace(chr(34), chr(39))}",',
        indent + '    "enabled": True,',
        indent + f'    "weight": {channel.get("weight")},',
        indent + f'    "authority_score": {channel.get("authority_score")},',
        indent + f'    # discovery_score={channel.get("discovery_score")}, tier={channel.get("discovery_tier")}, verified={channel.get("verified")}',
        indent + f'    # tickers={", ".join(str(item) for item in tickers) if tickers else "none"}',
        indent + "},",
    ]

    return lines


def build_python_append_block(selected_channels: List[Dict[str, Any]]) -> str:
    if not selected_channels:
        return "# No selected channels to add."

    lines: List[str] = []

    lines.append("# Add these items manually to REAL_CHANNELS in scanner_real_channels.py")
    lines.append("# Review every channel before enabling it.")
    lines.append("")

    for channel in selected_channels:
        lines.extend(format_python_channel_item(channel))
        lines.append("")

    return "\n".join(lines).rstrip()


def build_full_real_channels_block(
    existing_channels: List[Dict[str, Any]],
    selected_channels: List[Dict[str, Any]],
) -> str:
    merged: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for channel in existing_channels:
        username = normalize_username(channel.get("username"))

        if not username or username in seen:
            continue

        merged.append({
            "username": username,
            "title": str(channel.get("title", username)),
            "enabled": bool(channel.get("enabled", True)),
            "weight": float(channel.get("weight", 1.0)),
            "authority_score": int(channel.get("authority_score", 50)),
            "discovery_score": "existing",
            "discovery_tier": "existing",
            "verified": None,
            "unique_tickers": [],
        })
        seen.add(username)

    for channel in selected_channels:
        username = normalize_username(channel.get("username"))

        if not username or username in seen:
            continue

        merged.append(channel)
        seen.add(username)

    lines: List[str] = []

    lines.append("from typing import Any, Dict, List")
    lines.append("")
    lines.append("")
    lines.append("# Real public Telegram channels for analytical social scanner.")
    lines.append("# Add only public channels that you are allowed to read.")
    lines.append("# Safety:")
    lines.append("# - analytical only;")
    lines.append("# - no orders;")
    lines.append("# - no trading bot launch;")
    lines.append("# - no private-channel bypassing.")
    lines.append("")
    lines.append("REAL_CHANNELS: List[Dict[str, Any]] = [")

    for channel in merged:
        lines.extend(format_python_channel_item(channel))

    lines.append("]")

    return "\n".join(lines)


def build_selection_payload() -> Dict[str, Any]:
    discovery_file = load_json_file(DISCOVERY_PATH)
    existing_usernames = existing_real_usernames()

    if not discovery_file["ok"]:
        return {
            "source": "telegram_channel_selection_export",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "analytical_only": True,
            "orders_enabled": False,
            "trading_enabled": False,
            "safe_to_continue": False,
            "input_file": str(DISCOVERY_PATH),
            "output_json": str(OUTPUT_JSON_PATH),
            "output_txt": str(OUTPUT_TXT_PATH),
            "existing_real_channels_count": len(existing_usernames),
            "selected_channels_count": 0,
            "watch_channels_count": 0,
            "skipped_existing_count": 0,
            "selected_channels": [],
            "watch_channels": [],
            "skipped_existing": [],
            "blockers": ["discovery_file_not_ready"],
            "warnings": [str(discovery_file["error"])],
            "python_append_block": "# Discovery file is not ready.",
            "full_scanner_real_channels_py": "",
            "disclaimer": (
                "This script only exports selected public Telegram channel candidates. "
                "It does not modify scanner_real_channels.py and does not read Telegram."
            ),
        }

    discovery_data = discovery_file["data"]
    channels = discovery_data.get("channels", [])

    if not isinstance(channels, list):
        channels = []

    selected_channels: List[Dict[str, Any]] = []
    watch_channels: List[Dict[str, Any]] = []
    skipped_existing: List[Dict[str, Any]] = []

    for item in channels:
        if not isinstance(item, dict):
            continue

        username = normalize_username(item.get("username"))

        if not username:
            continue

        if username in existing_usernames:
            skipped_existing.append({
                "username": username,
                "title": item.get("title"),
                "reason": "already_exists_in_scanner_real_channels",
            })
            continue

        if should_select_channel(item):
            selected_channels.append(build_real_channel_entry(item))
            continue

        if should_watch_channel(item):
            watch_channels.append(build_real_channel_entry(item))

    selected_channels.sort(
        key=lambda item: (
            int(item.get("discovery_score") or 0),
            float(item.get("weight") or 0.0),
            str(item.get("username")),
        ),
        reverse=True,
    )

    watch_channels.sort(
        key=lambda item: (
            int(item.get("discovery_score") or 0),
            float(item.get("weight") or 0.0),
            str(item.get("username")),
        ),
        reverse=True,
    )

    python_append_block = build_python_append_block(selected_channels)
    full_real_channels_block = build_full_real_channels_block(
        existing_channels=REAL_CHANNELS,
        selected_channels=selected_channels,
    )

    return {
        "source": "telegram_channel_selection_export",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "safe_to_continue": True,
        "input_file": str(DISCOVERY_PATH),
        "output_json": str(OUTPUT_JSON_PATH),
        "output_txt": str(OUTPUT_TXT_PATH),
        "existing_real_channels_count": len(existing_usernames),
        "discovery_channels_count": len(channels),
        "selected_channels_count": len(selected_channels),
        "watch_channels_count": len(watch_channels),
        "skipped_existing_count": len(skipped_existing),
        "selected_channels": selected_channels,
        "watch_channels": watch_channels,
        "skipped_existing": skipped_existing,
        "blockers": [],
        "warnings": [],
        "python_append_block": python_append_block,
        "full_scanner_real_channels_py": full_real_channels_block,
        "disclaimer": (
            "This script only exports selected public Telegram channel candidates. "
            "It does not modify scanner_real_channels.py, does not read Telegram, "
            "does not call Binance private API, and does not create orders."
        ),
    }


def save_json_payload(payload: Dict[str, Any], path: Path = OUTPUT_JSON_PATH) -> Path:
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


def build_text_report(payload: Dict[str, Any]) -> str:
    lines: List[str] = []

    lines.append("TELEGRAM CHANNEL SELECTION EXPORT")
    lines.append("=================================")
    lines.append(f"Created at: {payload.get('created_at')}")
    lines.append("Mode: analytical only")
    lines.append(f"Safe to continue: {payload.get('safe_to_continue')}")
    lines.append("")
    lines.append("SUMMARY")
    lines.append("=======")
    lines.append(f"Discovery channels: {payload.get('discovery_channels_count', 0)}")
    lines.append(f"Existing real channels: {payload.get('existing_real_channels_count', 0)}")
    lines.append(f"Selected channels: {payload.get('selected_channels_count', 0)}")
    lines.append(f"Watch channels: {payload.get('watch_channels_count', 0)}")
    lines.append(f"Skipped existing: {payload.get('skipped_existing_count', 0)}")
    lines.append("")

    blockers = payload.get("blockers", [])
    warnings = payload.get("warnings", [])

    lines.append("BLOCKERS")
    lines.append("========")
    if blockers:
        for blocker in blockers:
            lines.append(f"- {blocker}")
    else:
        lines.append("none")

    lines.append("")
    lines.append("WARNINGS")
    lines.append("========")
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("none")

    lines.append("")
    lines.append("SELECTED CHANNELS")
    lines.append("=================")

    selected = payload.get("selected_channels", [])

    if selected:
        for channel in selected:
            tickers = channel.get("unique_tickers", [])

            if not isinstance(tickers, list):
                tickers = []

            lines.append("")
            lines.append(f"@{channel.get('username')}")
            lines.append("-" * (len(str(channel.get("username"))) + 1))
            lines.append(f"Title: {channel.get('title')}")
            lines.append(f"Discovery score: {channel.get('discovery_score')}")
            lines.append(f"Tier: {channel.get('discovery_tier')}")
            lines.append(f"Weight: {channel.get('weight')}")
            lines.append(f"Authority score: {channel.get('authority_score')}")
            lines.append(f"Verified: {channel.get('verified')}")
            lines.append(f"Messages checked: {channel.get('messages_checked')}")
            lines.append(f"Keyword hits: {channel.get('keyword_hits')}")
            lines.append("Tickers: " + (", ".join(str(item) for item in tickers) if tickers else "none"))
    else:
        lines.append("No selected channels.")

    lines.append("")
    lines.append("WATCH CHANNELS")
    lines.append("==============")

    watch = payload.get("watch_channels", [])

    if watch:
        for channel in watch:
            lines.append("")
            lines.append(f"@{channel.get('username')}")
            lines.append(f"Score: {channel.get('discovery_score')}")
            lines.append(f"Reason: watch_candidate")
    else:
        lines.append("No watch channels.")

    lines.append("")
    lines.append("SKIPPED EXISTING")
    lines.append("================")

    skipped = payload.get("skipped_existing", [])

    if skipped:
        for item in skipped:
            lines.append(f"- @{item.get('username')} ({item.get('reason')})")
    else:
        lines.append("none")

    lines.append("")
    lines.append("PYTHON APPEND BLOCK")
    lines.append("===================")
    lines.append(payload.get("python_append_block", ""))

    lines.append("")
    lines.append("SAFETY")
    lines.append("======")
    lines.append("[OK] This export did not modify scanner_real_channels.py.")
    lines.append("[OK] This export did not read Telegram.")
    lines.append("[OK] This export did not call Binance API.")
    lines.append("[OK] This export did not create orders.")
    lines.append("[OK] Review channels manually before adding them.")
    lines.append("")

    return "\n".join(lines)


def save_text_report(payload: Dict[str, Any], path: Path = OUTPUT_TXT_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(build_text_report(payload), encoding="utf-8")
    return path


def print_summary(payload: Dict[str, Any], json_path: Path, txt_path: Path) -> None:
    print("TELEGRAM CHANNEL SELECTION EXPORT")
    print("=================================")
    print("Mode: analytical only")
    print("Orders enabled:", payload.get("orders_enabled"))
    print("Trading enabled:", payload.get("trading_enabled"))
    print("Safe to continue:", payload.get("safe_to_continue"))
    print("Input file:", payload.get("input_file"))
    print("JSON output:", json_path)
    print("TXT output:", txt_path)
    print()

    print("SUMMARY")
    print("=======")
    print("Discovery channels:", payload.get("discovery_channels_count", 0))
    print("Existing real channels:", payload.get("existing_real_channels_count", 0))
    print("Selected channels:", payload.get("selected_channels_count", 0))
    print("Watch channels:", payload.get("watch_channels_count", 0))
    print("Skipped existing:", payload.get("skipped_existing_count", 0))

    if payload.get("blockers"):
        print("Blockers:", ", ".join(str(item) for item in payload["blockers"]))
    else:
        print("Blockers: none")

    if payload.get("warnings"):
        print("Warnings:", ", ".join(str(item) for item in payload["warnings"]))
    else:
        print("Warnings: none")

    print()
    print("SELECTED")
    print("========")

    selected = payload.get("selected_channels", [])

    if not selected:
        print("No selected channels.")
    else:
        for channel in selected:
            print(
                ("@" + str(channel.get("username"))).ljust(30),
                "score=" + str(channel.get("discovery_score")),
                "tier=" + str(channel.get("discovery_tier")),
                "weight=" + str(channel.get("weight")),
                "authority=" + str(channel.get("authority_score")),
            )

    print()
    print("NEXT STEP")
    print("=========")
    print("Review reports/telegram_channel_selection_export.txt.")
    print("Then manually copy selected channel blocks into scanner_real_channels.py.")


def main() -> None:
    payload = build_selection_payload()
    json_path = save_json_payload(payload)
    txt_path = save_text_report(payload)
    print_summary(payload, json_path, txt_path)


if __name__ == "__main__":
    main()
