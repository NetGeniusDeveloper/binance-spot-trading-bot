import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


CONFIRM_ENV_NAME = "APPLY_CHANNEL_CONFIG_CONFIRM"

CURRENT_CONFIG_PATH = Path("scanner_real_channels.py")
RECOMMENDED_CONFIG_PATH = Path("reports") / "scanner_real_channels.recommended.py"

OUTPUT_JSON_PATH = Path("reports") / "telegram_channel_config_apply_manual.json"
OUTPUT_TXT_PATH = Path("reports") / "telegram_channel_config_apply_manual.txt"
BACKUP_PATH = Path("reports") / "scanner_real_channels.backup.py"


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


def build_base_payload() -> Dict[str, Any]:
    return {
        "source": "telegram_channel_config_apply_manual",
        "created_at": now_text(),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "telegram_messages_read": False,
        "binance_api_used": False,
        "current_config_path": str(CURRENT_CONFIG_PATH),
        "recommended_config_path": str(RECOMMENDED_CONFIG_PATH),
        "backup_path": str(BACKUP_PATH),
        "output_json": str(OUTPUT_JSON_PATH),
        "output_txt": str(OUTPUT_TXT_PATH),
        "confirm_env_name": CONFIRM_ENV_NAME,
        "confirm_env_value": os.getenv(CONFIRM_ENV_NAME, ""),
        "scanner_real_channels_modified": False,
        "backup_created": False,
        "applied": False,
        "safe_to_continue": False,
        "blockers": [],
        "warnings": [],
        "error": None,
        "disclaimer": (
            "This script modifies scanner_real_channels.py only when "
            "APPLY_CHANNEL_CONFIG_CONFIRM=YES is explicitly provided."
        ),
    }


def run_compile_check(path: Path) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            ["python", "-m", "py_compile", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )

        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    except Exception as ex:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(ex),
        }


def apply_config() -> Dict[str, Any]:
    payload = build_base_payload()

    confirm_value = str(payload["confirm_env_value"]).strip()

    if confirm_value != "YES":
        payload["blockers"].append("manual_confirmation_missing")
        payload["error"] = (
            "Manual confirmation is required. "
            "Run with APPLY_CHANNEL_CONFIG_CONFIRM=YES."
        )
        return payload

    if not RECOMMENDED_CONFIG_PATH.exists():
        payload["blockers"].append("recommended_config_missing")
        payload["error"] = f"Missing recommended config: {RECOMMENDED_CONFIG_PATH}"
        return payload

    if not CURRENT_CONFIG_PATH.exists():
        payload["blockers"].append("current_config_missing")
        payload["error"] = f"Missing current config: {CURRENT_CONFIG_PATH}"
        return payload

    recommended_compile = run_compile_check(RECOMMENDED_CONFIG_PATH)
    payload["recommended_compile"] = recommended_compile

    if not recommended_compile["ok"]:
        payload["blockers"].append("recommended_config_compile_failed")
        payload["error"] = "Recommended config failed Python compile check."
        return payload

    OUTPUT_JSON_PATH.parent.mkdir(exist_ok=True)

    shutil.copy2(CURRENT_CONFIG_PATH, BACKUP_PATH)
    payload["backup_created"] = True

    shutil.copy2(RECOMMENDED_CONFIG_PATH, CURRENT_CONFIG_PATH)
    payload["scanner_real_channels_modified"] = True
    payload["applied"] = True

    current_compile = run_compile_check(CURRENT_CONFIG_PATH)
    payload["current_compile_after_apply"] = current_compile

    if not current_compile["ok"]:
        payload["blockers"].append("current_config_compile_failed_after_apply")
        payload["error"] = "Applied config failed compile check. Backup should be restored manually."
        payload["safe_to_continue"] = False
        return payload

    payload["safe_to_continue"] = True

    return payload


def save_json_report(payload: Dict[str, Any]) -> Path:
    OUTPUT_JSON_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_JSON_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return OUTPUT_JSON_PATH


def build_text_report(payload: Dict[str, Any]) -> str:
    lines = []

    lines.append("TELEGRAM CHANNEL CONFIG APPLY MANUAL")
    lines.append("====================================")
    lines.append(f"Created at: {payload.get('created_at')}")
    lines.append("Mode: manual apply")
    lines.append(f"Safe to continue: {payload.get('safe_to_continue')}")
    lines.append(f"Applied: {payload.get('applied')}")
    lines.append(f"scanner_real_channels.py modified: {payload.get('scanner_real_channels_modified')}")
    lines.append(f"Backup created: {payload.get('backup_created')}")
    lines.append("")
    lines.append("FILES")
    lines.append("=====")
    lines.append(f"Current config: {payload.get('current_config_path')}")
    lines.append(f"Recommended config: {payload.get('recommended_config_path')}")
    lines.append(f"Backup: {payload.get('backup_path')}")
    lines.append("")
    lines.append("CONFIRMATION")
    lines.append("============")
    lines.append(f"{payload.get('confirm_env_name')}={payload.get('confirm_env_value')}")
    lines.append("")
    lines.append("BLOCKERS")
    lines.append("========")
    blockers = payload.get("blockers", [])
    lines.append(", ".join(str(item) for item in blockers) if blockers else "none")
    lines.append("")
    lines.append("WARNINGS")
    lines.append("========")
    warnings = payload.get("warnings", [])
    lines.append(", ".join(str(item) for item in warnings) if warnings else "none")

    if payload.get("error"):
        lines.append("")
        lines.append("ERROR")
        lines.append("=====")
        lines.append(str(payload.get("error")))

    lines.append("")
    lines.append("SAFETY")
    lines.append("======")
    lines.append("[OK] This script requires explicit manual confirmation.")
    lines.append("[OK] This script does not read Telegram.")
    lines.append("[OK] This script does not call Binance API.")
    lines.append("[OK] This script does not create orders.")
    lines.append("[OK] Backup is saved before replacing scanner_real_channels.py.")
    lines.append("")

    return "\n".join(lines)


def save_text_report(payload: Dict[str, Any]) -> Path:
    OUTPUT_TXT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_TXT_PATH.write_text(build_text_report(payload), encoding="utf-8")
    return OUTPUT_TXT_PATH


def print_summary(payload: Dict[str, Any], json_path: Path, txt_path: Path) -> None:
    print("TELEGRAM CHANNEL CONFIG APPLY MANUAL")
    print("====================================")
    print("Manual confirmation:", payload.get("confirm_env_value"))
    print("Applied:", payload.get("applied"))
    print("scanner_real_channels.py modified:", payload.get("scanner_real_channels_modified"))
    print("Backup created:", payload.get("backup_created"))
    print("Safe to continue:", payload.get("safe_to_continue"))
    print("JSON output:", json_path)
    print("TXT output:", txt_path)

    if payload.get("blockers"):
        print("Blockers:", ", ".join(str(item) for item in payload["blockers"]))
    else:
        print("Blockers: none")

    if payload.get("error"):
        print("Error:", payload.get("error"))


def main() -> None:
    payload = apply_config()
    json_path = save_json_report(payload)
    txt_path = save_text_report(payload)
    print_summary(payload, json_path, txt_path)


if __name__ == "__main__":
    main()
