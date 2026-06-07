import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from config import WATCHLIST
from social_signal_engine import analyze_social_signals
from telegram_message_classifier import (
    classify_message_text,
    summarize_message_classifications,
)
from ticker_extractor import extract_tickers


PREVIEW_PATH = Path("reports") / "telegram_real_messages_preview.json"
OUTPUT_PATH = Path("reports") / "telegram_real_social_signals.json"


def load_preview_payload(path: Path = PREVIEW_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {
            "error": f"Preview file not found: {path}",
            "messages": [],
            "blockers": ["preview_file_not_found"],
            "warnings": [],
            "safe_to_continue": False,
        }

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as ex:
        return {
            "error": f"Invalid preview JSON: {ex}",
            "messages": [],
            "blockers": ["invalid_preview_json"],
            "warnings": [],
            "safe_to_continue": False,
        }


def parse_datetime_safe(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value

    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    return None


def select_analysis_now(messages: List[Dict[str, Any]]) -> datetime:
    """
    Use the newest Telegram message time as analysis time.

    This makes analysis reproducible for saved preview JSON files.
    """
    parsed_dates = []

    for message in messages:
        created_at = parse_datetime_safe(message.get("created_at"))

        if created_at is not None:
            parsed_dates.append(created_at)

    if parsed_dates:
        return max(parsed_dates)

    return datetime.now()


def normalize_preview_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized_messages = []

    for message in messages:
        text = str(message.get("text", "")).strip()

        if not text:
            continue

        classification = classify_message_text(text)

        normalized_messages.append({
            "channel": message.get("channel", "unknown"),
            "message_id": message.get("message_id"),
            "created_at": message.get("created_at"),
            "text": text,
            "views": message.get("views"),
            "forwards": message.get("forwards"),
            "channel_weight": message.get("channel_weight", 1.0),
            "authority_score": message.get("authority_score", 50),
            "demo": False,
            "message_classification": classification,
        })

    return normalized_messages


def build_ticker_classification_map(
    messages: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    result: Dict[str, List[Dict[str, Any]]] = {}

    for message in messages:
        text = str(message.get("text", ""))
        tickers = extract_tickers(text, WATCHLIST)

        for ticker in tickers:
            classification = message.get("message_classification")

            if not isinstance(classification, dict):
                continue

            result.setdefault(ticker, []).append(classification)

    return result


def enrich_signals_with_message_classification(
    signals: List[Dict[str, Any]],
    messages: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    ticker_classifications = build_ticker_classification_map(messages)

    enriched_signals = []

    for signal in signals:
        ticker = str(signal.get("ticker", "")).upper()
        classifications = ticker_classifications.get(ticker, [])
        classification_summary = summarize_message_classifications(classifications)

        enriched_signal = {
            **signal,
            "message_classification_summary": classification_summary,
            "message_intent": classification_summary.get("primary_intent"),
            "message_quality_score": classification_summary.get("avg_quality_score"),
            "message_score_adjustment": classification_summary.get("score_adjustment"),
            "message_risk_flags": classification_summary.get("flags", []),
        }

        enriched_signals.append(enriched_signal)

    return enriched_signals


def build_not_ready_payload(preview_payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": "telegram_real_messages_analyze",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "binance_scanner_started": False,
        "telegram_messages_read": False,
        "social_analysis_completed": False,
        "message_classification_completed": False,
        "safe_to_continue": False,
        "input_preview_file": str(PREVIEW_PATH),
        "output_file": str(OUTPUT_PATH),
        "messages_loaded": 0,
        "signals_found": 0,
        "social_signal_count": 0,
        "tickers_detected": [],
        "signals": [],
        "blockers": preview_payload.get("blockers", []) or ["preview_not_safe_to_continue"],
        "warnings": preview_payload.get("warnings", []),
        "error": preview_payload.get("error"),
        "disclaimer": (
            "Telegram/social data is analytical only. "
            "This analysis does not create orders and does not start trading."
        ),
    }


def build_analysis_payload(preview_payload: Dict[str, Any]) -> Dict[str, Any]:
    if not preview_payload.get("safe_to_continue"):
        return build_not_ready_payload(preview_payload)

    messages = normalize_preview_messages(preview_payload.get("messages", []))
    analysis_now = select_analysis_now(messages)

    signals = analyze_social_signals(
        raw_messages=messages,
        now=analysis_now,
    )

    enriched_signals = enrich_signals_with_message_classification(
        signals=signals,
        messages=messages,
    )

    tickers_detected = sorted({
        str(signal.get("ticker"))
        for signal in enriched_signals
        if signal.get("ticker")
    })

    social_signal_count = sum(
        1
        for signal in enriched_signals
        if bool(signal.get("social_signal"))
    )

    message_intents = sorted({
        str(signal.get("message_intent"))
        for signal in enriched_signals
        if signal.get("message_intent")
    })

    return {
        "source": "telegram_real_messages_analyze",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analysis_now": analysis_now.isoformat(timespec="seconds"),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "binance_scanner_started": False,
        "telegram_messages_read": False,
        "social_analysis_completed": True,
        "message_classification_completed": True,
        "safe_to_continue": True,
        "input_preview_file": str(PREVIEW_PATH),
        "output_file": str(OUTPUT_PATH),
        "preview_source": preview_payload.get("source"),
        "preview_created_at": preview_payload.get("created_at"),
        "preview_messages_collected": preview_payload.get("messages_collected"),
        "messages_loaded": len(messages),
        "signals_found": len(enriched_signals),
        "social_signal_count": social_signal_count,
        "tickers_detected": tickers_detected,
        "message_intents_detected": message_intents,
        "signals": enriched_signals,
        "blockers": [],
        "warnings": preview_payload.get("warnings", []),
        "disclaimer": (
            "Telegram/social data is analytical only. "
            "A social signal is not a trading entry. "
            "This analysis does not create orders and does not start trading."
        ),
    }


def save_analysis_payload(payload: Dict[str, Any], path: Path = OUTPUT_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )

    return path


def print_signal(signal: Dict[str, Any]) -> None:
    classification_summary = signal.get("message_classification_summary", {})

    print()
    print("Ticker:", signal.get("ticker"))
    print("Status:", signal.get("status"))
    print("Mentions 5m:", signal.get("mentions_5m"))
    print("Mentions 15m:", signal.get("mentions_15m"))
    print("Mentions 1h:", signal.get("mentions_1h"))
    print("Mentions 4h:", signal.get("mentions_4h"))
    print("Mentions 24h:", signal.get("mentions_24h"))
    print("Unique channels:", signal.get("unique_channels"))
    print("Weighted mentions:", signal.get("weighted_mentions"))
    print("Mention growth factor:", signal.get("mention_growth_factor"))
    print("Social signal:", signal.get("social_signal"))
    print("Message intent:", signal.get("message_intent"))
    print("Message quality score:", signal.get("message_quality_score"))
    print("Message score adjustment:", signal.get("message_score_adjustment"))
    print("Message risk flags:", ", ".join(signal.get("message_risk_flags", [])) or "none")
    print("Message intent counts:", classification_summary.get("counts_by_intent", {}))
    print("Sample texts:", signal.get("sample_texts", []))


def print_analysis_summary(payload: Dict[str, Any], output_path: Path) -> None:
    print("TELEGRAM REAL MESSAGES ANALYSIS")
    print("===============================")
    print("Mode: analytical only")
    print("Orders enabled:", payload.get("orders_enabled"))
    print("Trading enabled:", payload.get("trading_enabled"))
    print("Binance scanner started:", payload.get("binance_scanner_started"))
    print("Social analysis completed:", payload.get("social_analysis_completed"))
    print("Message classification completed:", payload.get("message_classification_completed"))
    print("Input preview file:", payload.get("input_preview_file"))
    print("Output file:", output_path)
    print()

    print("SUMMARY")
    print("=======")
    print("Safe to continue:", payload.get("safe_to_continue"))
    print("Messages loaded:", payload.get("messages_loaded"))
    print("Signals found:", payload.get("signals_found"))
    print("Social signal count:", payload.get("social_signal_count"))
    print("Tickers detected:", ", ".join(payload.get("tickers_detected", [])) or "none")
    print("Message intents:", ", ".join(payload.get("message_intents_detected", [])) or "none")

    if payload.get("blockers"):
        print("Blockers:", ", ".join(str(item) for item in payload["blockers"]))
    else:
        print("Blockers: none")

    if payload.get("warnings"):
        print("Warnings:", ", ".join(str(item) for item in payload["warnings"]))
    else:
        print("Warnings: none")

    if payload.get("error"):
        print("Error:", payload.get("error"))

    print()
    print("SOCIAL SIGNALS")
    print("==============")

    signals = payload.get("signals", [])

    if not signals:
        print("No tickers detected in real Telegram preview messages.")
    else:
        for signal in signals:
            print_signal(signal)

    print()
    print("SAFETY")
    print("======")
    print("[OK] This analysis did not create orders.")
    print("[OK] This analysis did not start trading bot.")
    print("[OK] This analysis did not start Binance market scanner.")
    print("[OK] This analysis only processed saved Telegram preview JSON.")
    print("[OK] Message classification is local rule-based analysis only.")

    print()
    print("NEXT STEP")
    print("=========")

    if payload.get("signals_found", 0) <= 0:
        print("Post a test message with a ticker, for example: SOL/USDT volume is growing, wait for retest.")
        print("Then rerun preview and analysis.")
        return

    print("Real Telegram messages were converted into enriched social signals.")
    print("Next safe step: rate these enriched signals with real Binance market data.")


def main() -> None:
    preview_payload = load_preview_payload()
    analysis_payload = build_analysis_payload(preview_payload)
    output_path = save_analysis_payload(analysis_payload)
    print_analysis_summary(analysis_payload, output_path)


if __name__ == "__main__":
    main()
