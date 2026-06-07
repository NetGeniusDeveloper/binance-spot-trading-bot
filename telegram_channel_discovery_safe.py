import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from credentials import (
    TELEGRAM_API_HASH,
    TELEGRAM_API_ID,
    TELEGRAM_SESSION_NAME,
)
from telegram_connection_test import run_connection_test_async


CANDIDATES_PATH = Path("data") / "telegram_channel_candidates.txt"
REPORTS_DIR = Path("reports")
OUTPUT_JSON_PATH = REPORTS_DIR / "telegram_channel_discovery.json"
OUTPUT_TXT_PATH = REPORTS_DIR / "telegram_channel_discovery.txt"

DEFAULT_LIMIT_PER_CHANNEL = 10
MAX_TEXT_PREVIEW_LENGTH = 300

CRYPTO_KEYWORDS = {
    "btc",
    "bitcoin",
    "eth",
    "ethereum",
    "bnb",
    "binance",
    "sol",
    "ton",
    "usdt",
    "crypto",
    "altcoin",
    "market",
    "trading",
    "futures",
    "spot",
    "token",
    "blockchain",
    "airdrop",
}

TICKER_PATTERN = re.compile(
    r"(?<![A-Z0-9])(?:\$|#)?([A-Z]{2,12})(?:/USDT|USDT|/USD|USD)?(?![A-Z0-9])"
)

NOISE_TICKERS = {
    "THE",
    "AND",
    "FOR",
    "ARE",
    "YOU",
    "NOT",
    "THIS",
    "WITH",
    "FROM",
    "NEWS",
    "POST",
    "TEST",
    "START",
}


def normalize_username(value: str) -> str:
    text = str(value or "").strip()
    text = text.replace("https://t.me/", "")
    text = text.replace("http://t.me/", "")
    text = text.replace("t.me/", "")
    text = text.strip().lstrip("@").strip("/")

    if "/" in text:
        text = text.split("/", 1)[0]

    return text


def truncate_text(text: str, max_length: int = MAX_TEXT_PREVIEW_LENGTH) -> str:
    clean = " ".join(str(text or "").split())

    if len(clean) <= max_length:
        return clean

    return clean[:max_length].rstrip() + "..."


def load_candidate_usernames(path: Path = CANDIDATES_PATH) -> List[str]:
    if not path.exists():
        return []

    usernames: List[str] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        username = normalize_username(line)

        if username and username not in usernames:
            usernames.append(username)

    return usernames


def extract_tickers(text: str) -> List[str]:
    found: List[str] = []

    for match in TICKER_PATTERN.findall(str(text or "").upper()):
        ticker = match.strip().upper()

        if not ticker:
            continue

        if ticker in NOISE_TICKERS:
            continue

        if len(ticker) < 2:
            continue

        if ticker not in found:
            found.append(ticker)

    return found


def count_crypto_keywords(text: str) -> int:
    lowered = str(text or "").lower()
    count = 0

    for keyword in CRYPTO_KEYWORDS:
        if keyword in lowered:
            count += 1

    return count


def score_channel(
    messages: List[Dict[str, Any]],
    participants_count: Any,
    verified: bool,
    scam: bool,
    fake: bool,
) -> Dict[str, Any]:
    ticker_hits: Dict[str, int] = {}
    keyword_hits = 0
    total_text_messages = len(messages)

    for message in messages:
        text = str(message.get("text", ""))
        keyword_hits += count_crypto_keywords(text)

        for ticker in extract_tickers(text):
            ticker_hits[ticker] = ticker_hits.get(ticker, 0) + 1

    unique_tickers = sorted(ticker_hits)

    score = 0
    reasons: List[str] = []
    warnings: List[str] = []

    if total_text_messages > 0:
        score += 20
        reasons.append("has_recent_text_messages")
    else:
        warnings.append("no_recent_text_messages")

    if keyword_hits > 0:
        score += min(30, keyword_hits * 5)
        reasons.append("crypto_keywords_found")

    if unique_tickers:
        score += min(30, len(unique_tickers) * 10)
        reasons.append("tickers_found")

    if verified:
        score += 10
        reasons.append("telegram_verified")

    try:
        participants = int(participants_count or 0)
    except Exception:
        participants = 0

    if participants >= 10000:
        score += 10
        reasons.append("large_channel")
    elif participants >= 1000:
        score += 5
        reasons.append("medium_channel")

    if scam:
        score -= 60
        warnings.append("telegram_scam_flag")

    if fake:
        score -= 60
        warnings.append("telegram_fake_flag")

    if keyword_hits == 0 and not unique_tickers:
        warnings.append("no_crypto_relevance_detected")

    score = max(0, min(100, score))

    if scam or fake:
        recommendation = "reject"
    elif score >= 60:
        recommendation = "active_candidate"
    elif score >= 35:
        recommendation = "watch_candidate"
    else:
        recommendation = "reject"

    return {
        "score": score,
        "recommendation": recommendation,
        "keyword_hits": keyword_hits,
        "ticker_hits": ticker_hits,
        "unique_tickers": unique_tickers,
        "reasons": reasons,
        "warnings": warnings,
    }


def build_message_item(username: str, message: Any) -> Dict[str, Any]:
    message_date = getattr(message, "date", None)

    if message_date is None:
        created_at = datetime.now()
    else:
        created_at = message_date.replace(tzinfo=None)

    text = getattr(message, "message", "") or ""

    return {
        "channel": username,
        "message_id": int(getattr(message, "id", 0) or 0),
        "created_at": created_at.isoformat(timespec="seconds"),
        "text": str(text),
        "text_preview": truncate_text(str(text)),
        "views": int(getattr(message, "views", 0) or 0),
        "forwards": int(getattr(message, "forwards", 0) or 0),
    }


def build_not_ready_payload(connection_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": "telegram_channel_discovery_safe",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "binance_api_used": False,
        "telegram_connect_attempted": connection_result.get("telegram_connect_attempted", False),
        "telegram_messages_read": False,
        "telegram_channel_metadata_read": False,
        "safe_to_continue": False,
        "input_file": str(CANDIDATES_PATH),
        "output_json": str(OUTPUT_JSON_PATH),
        "output_txt": str(OUTPUT_TXT_PATH),
        "candidates_loaded": 0,
        "channels_checked": 0,
        "channels_ok": 0,
        "channels_failed": 0,
        "active_candidates": 0,
        "watch_candidates": 0,
        "rejected": 0,
        "channels": [],
        "blockers": connection_result.get("blockers", []),
        "warnings": connection_result.get("warnings", []),
        "disclaimer": (
            "This discovery is analytical only. It reads only public Telegram channels "
            "listed by the user. It does not create orders and does not start trading."
        ),
    }


async def run_channel_discovery_async(
    limit_per_channel: int = DEFAULT_LIMIT_PER_CHANNEL,
) -> Dict[str, Any]:
    connection_result = await run_connection_test_async()

    if not connection_result.get("safe_to_continue"):
        return build_not_ready_payload(connection_result)

    usernames = load_candidate_usernames()

    payload: Dict[str, Any] = {
        "source": "telegram_channel_discovery_safe",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "binance_api_used": False,
        "telegram_connect_attempted": True,
        "telegram_messages_read": False,
        "telegram_channel_metadata_read": False,
        "safe_to_continue": True,
        "input_file": str(CANDIDATES_PATH),
        "output_json": str(OUTPUT_JSON_PATH),
        "output_txt": str(OUTPUT_TXT_PATH),
        "limit_per_channel": int(limit_per_channel),
        "candidates_loaded": len(usernames),
        "channels_checked": 0,
        "channels_ok": 0,
        "channels_failed": 0,
        "active_candidates": 0,
        "watch_candidates": 0,
        "rejected": 0,
        "channels": [],
        "blockers": [],
        "warnings": list(connection_result.get("warnings", [])),
        "disclaimer": (
            "This discovery is analytical only. It reads only public Telegram channels "
            "listed by the user. It does not create orders and does not start trading."
        ),
    }

    if not usernames:
        payload["warnings"].append("no_channel_candidates_configured")
        return payload

    from telethon import TelegramClient

    async with TelegramClient(
        TELEGRAM_SESSION_NAME,
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH,
    ) as client:
        for username in usernames:
            payload["channels_checked"] += 1

            try:
                entity = await client.get_entity(username)

                verified = bool(getattr(entity, "verified", False))
                scam = bool(getattr(entity, "scam", False))
                fake = bool(getattr(entity, "fake", False))
                participants_count = getattr(entity, "participants_count", None)
                title = getattr(entity, "title", username)

                messages: List[Dict[str, Any]] = []

                async for message in client.iter_messages(
                    username,
                    limit=int(limit_per_channel),
                ):
                    text = getattr(message, "message", "") or ""

                    if not str(text).strip():
                        continue

                    messages.append(build_message_item(username, message))

                if messages:
                    payload["telegram_messages_read"] = True

                payload["telegram_channel_metadata_read"] = True

                score = score_channel(
                    messages=messages,
                    participants_count=participants_count,
                    verified=verified,
                    scam=scam,
                    fake=fake,
                )

                item = {
                    "username": username,
                    "ok": True,
                    "title": title,
                    "id": getattr(entity, "id", None),
                    "verified": verified,
                    "scam": scam,
                    "fake": fake,
                    "participants_count": participants_count,
                    "messages_checked": len(messages),
                    "score": score["score"],
                    "recommendation": score["recommendation"],
                    "keyword_hits": score["keyword_hits"],
                    "ticker_hits": score["ticker_hits"],
                    "unique_tickers": score["unique_tickers"],
                    "reasons": score["reasons"],
                    "warnings": score["warnings"],
                    "sample_messages": messages[:5],
                }

                payload["channels"].append(item)
                payload["channels_ok"] += 1

                if item["recommendation"] == "active_candidate":
                    payload["active_candidates"] += 1
                elif item["recommendation"] == "watch_candidate":
                    payload["watch_candidates"] += 1
                else:
                    payload["rejected"] += 1

            except Exception as ex:
                payload["channels_failed"] += 1
                payload["rejected"] += 1
                payload["channels"].append({
                    "username": username,
                    "ok": False,
                    "recommendation": "reject",
                    "score": 0,
                    "error": str(ex),
                    "warnings": ["channel_check_failed"],
                })

    return payload


def run_channel_discovery() -> Dict[str, Any]:
    return asyncio.run(run_channel_discovery_async())


def save_json_report(payload: Dict[str, Any], path: Path = OUTPUT_JSON_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def build_text_report(payload: Dict[str, Any]) -> str:
    lines: List[str] = []

    lines.append("TELEGRAM CHANNEL DISCOVERY SAFE REPORT")
    lines.append("======================================")
    lines.append(f"Created at: {payload.get('created_at')}")
    lines.append("Mode: analytical only")
    lines.append(f"Safe to continue: {payload.get('safe_to_continue')}")
    lines.append("")
    lines.append("SUMMARY")
    lines.append("=======")
    lines.append(f"Candidates loaded: {payload.get('candidates_loaded')}")
    lines.append(f"Channels checked: {payload.get('channels_checked')}")
    lines.append(f"Channels OK: {payload.get('channels_ok')}")
    lines.append(f"Channels failed: {payload.get('channels_failed')}")
    lines.append(f"Active candidates: {payload.get('active_candidates')}")
    lines.append(f"Watch candidates: {payload.get('watch_candidates')}")
    lines.append(f"Rejected: {payload.get('rejected')}")
    lines.append("")

    lines.append("CHANNELS")
    lines.append("========")

    channels = payload.get("channels", [])

    if not channels:
        lines.append("No channels checked.")
    else:
        for item in channels:
            lines.append("")
            lines.append(f"@{item.get('username')}")
            lines.append("-" * (len(str(item.get("username"))) + 1))
            lines.append(f"OK: {item.get('ok')}")
            lines.append(f"Title: {item.get('title')}")
            lines.append(f"Recommendation: {item.get('recommendation')}")
            lines.append(f"Score: {item.get('score')}")
            lines.append(f"Participants: {item.get('participants_count')}")
            lines.append(f"Verified: {item.get('verified')}")
            lines.append(f"Scam: {item.get('scam')}")
            lines.append(f"Fake: {item.get('fake')}")
            lines.append(f"Messages checked: {item.get('messages_checked')}")
            lines.append(f"Tickers: {item.get('unique_tickers', [])}")
            lines.append(f"Keyword hits: {item.get('keyword_hits')}")

            if item.get("error"):
                lines.append(f"Error: {item.get('error')}")

            if item.get("warnings"):
                lines.append("Warnings: " + ", ".join(str(x) for x in item.get("warnings", [])))

            samples = item.get("sample_messages", [])

            if samples:
                lines.append("Samples:")
                for sample in samples[:3]:
                    lines.append("- " + str(sample.get("text_preview")))

    lines.append("")
    lines.append("SAFETY")
    lines.append("======")
    lines.append("[OK] This discovery did not create orders.")
    lines.append("[OK] This discovery did not start trading bot.")
    lines.append("[OK] This discovery did not call Binance API.")
    lines.append("[OK] This discovery reads only limited public Telegram channel data.")
    lines.append("[OK] Result is only a candidate report for manual review.")
    lines.append("")

    return "\n".join(lines)


def save_text_report(payload: Dict[str, Any], path: Path = OUTPUT_TXT_PATH) -> Path:
    text = build_text_report(payload)
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def print_summary(payload: Dict[str, Any], json_path: Path, txt_path: Path) -> None:
    print("TELEGRAM CHANNEL DISCOVERY SAFE")
    print("===============================")
    print("Mode: analytical only")
    print("Orders enabled:", payload.get("orders_enabled"))
    print("Trading enabled:", payload.get("trading_enabled"))
    print("Binance API used:", payload.get("binance_api_used"))
    print("Telegram connect attempted:", payload.get("telegram_connect_attempted"))
    print("Telegram metadata read:", payload.get("telegram_channel_metadata_read"))
    print("Telegram messages read:", payload.get("telegram_messages_read"))
    print("JSON output:", json_path)
    print("TXT output:", txt_path)
    print()

    print("SUMMARY")
    print("=======")
    print("Safe to continue:", payload.get("safe_to_continue"))
    print("Candidates loaded:", payload.get("candidates_loaded"))
    print("Channels checked:", payload.get("channels_checked"))
    print("Channels OK:", payload.get("channels_ok"))
    print("Channels failed:", payload.get("channels_failed"))
    print("Active candidates:", payload.get("active_candidates"))
    print("Watch candidates:", payload.get("watch_candidates"))
    print("Rejected:", payload.get("rejected"))

    blockers = payload.get("blockers", [])
    warnings = payload.get("warnings", [])

    print("Blockers:", ", ".join(str(x) for x in blockers) if blockers else "none")
    print("Warnings:", ", ".join(str(x) for x in warnings) if warnings else "none")
    print()

    print("TOP CHANNELS")
    print("============")

    channels = sorted(
        payload.get("channels", []),
        key=lambda item: int(item.get("score", 0) or 0),
        reverse=True,
    )

    if not channels:
        print("No channels.")
    else:
        for item in channels[:20]:
            print(
                ("@" + str(item.get("username"))).ljust(30),
                "ok=" + str(item.get("ok")),
                "score=" + str(item.get("score")),
                "recommendation=" + str(item.get("recommendation")),
                "tickers=" + ",".join(item.get("unique_tickers", [])),
            )

    print()
    print("SAFETY")
    print("======")
    print("[OK] This discovery did not create orders.")
    print("[OK] This discovery did not start trading bot.")
    print("[OK] This discovery did not call Binance API.")
    print("[OK] This discovery reads only limited public Telegram channel data.")
    print()
    print("NEXT STEP")
    print("=========")
    print("Review reports/telegram_channel_discovery.txt.")
    print("Only after manual review, selected channels can be added to scanner_real_channels.py.")


def main() -> None:
    payload = run_channel_discovery()
    json_path = save_json_report(payload)
    txt_path = save_text_report(payload)
    print_summary(payload, json_path, txt_path)


if __name__ == "__main__":
    main()
