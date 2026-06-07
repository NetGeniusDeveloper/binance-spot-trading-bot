import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

from binance.client import Client

from credentials import BINANCE_API_KEY, BINANCE_SECRET_KEY

try:
    from config import BINANCE_API_TIMEOUT
except Exception:
    BINANCE_API_TIMEOUT = 20


REPORTS_DIR = Path("reports")
OUTPUT_PATH = REPORTS_DIR / "binance_symbol_universe.json"

COMMON_EXTRA_ASSETS = {
    "BTC",
    "ETH",
    "BNB",
    "SOL",
    "TON",
    "XRP",
    "LINK",
    "USDT",
    "USDC",
    "FDUSD",
    "TUSD",
}


def create_public_binance_client() -> Client:
    return Client(
        api_key=BINANCE_API_KEY,
        api_secret=BINANCE_SECRET_KEY,
        requests_params={"timeout": BINANCE_API_TIMEOUT},
    )


def build_fallback_universe(error: str | None = None) -> Dict[str, Any]:
    base_assets = sorted(COMMON_EXTRA_ASSETS)

    return {
        "source": "binance_symbol_universe",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "binance_public_api_used": False,
        "safe_to_continue": True,
        "fallback": True,
        "error": error,
        "symbols_count": 0,
        "base_assets_count": len(base_assets),
        "quote_assets_count": 0,
        "symbols": [],
        "base_assets": base_assets,
        "quote_assets": [],
        "warnings": ["using_fallback_symbol_universe"],
        "disclaimer": (
            "This file is used only for analytical ticker filtering. "
            "It does not create orders and does not start trading."
        ),
    }


def fetch_binance_symbol_universe() -> Dict[str, Any]:
    client = create_public_binance_client()
    exchange_info = client.get_exchange_info()

    symbols: Set[str] = set()
    base_assets: Set[str] = set(COMMON_EXTRA_ASSETS)
    quote_assets: Set[str] = set()

    for item in exchange_info.get("symbols", []):
        status = str(item.get("status", ""))
        permissions = item.get("permissions", []) or []

        if status != "TRADING":
            continue

        if permissions and "SPOT" not in permissions:
            continue

        symbol = str(item.get("symbol", "")).upper().strip()
        base_asset = str(item.get("baseAsset", "")).upper().strip()
        quote_asset = str(item.get("quoteAsset", "")).upper().strip()

        if symbol:
            symbols.add(symbol)

        if base_asset:
            base_assets.add(base_asset)

        if quote_asset:
            quote_assets.add(quote_asset)

    return {
        "source": "binance_symbol_universe",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "binance_public_api_used": True,
        "safe_to_continue": True,
        "fallback": False,
        "error": None,
        "symbols_count": len(symbols),
        "base_assets_count": len(base_assets),
        "quote_assets_count": len(quote_assets),
        "symbols": sorted(symbols),
        "base_assets": sorted(base_assets),
        "quote_assets": sorted(quote_assets),
        "warnings": [],
        "disclaimer": (
            "This file is used only for analytical ticker filtering. "
            "It does not create orders and does not start trading."
        ),
    }


def save_symbol_universe(payload: Dict[str, Any], path: Path = OUTPUT_PATH) -> Path:
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


def load_cached_universe(path: Path = OUTPUT_PATH) -> Dict[str, Any] | None:
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    if not payload.get("base_assets"):
        return None

    return payload


def load_symbol_universe(refresh: bool = False) -> Dict[str, Any]:
    if not refresh:
        cached = load_cached_universe()

        if cached is not None:
            return cached

    try:
        payload = fetch_binance_symbol_universe()
        save_symbol_universe(payload)
        return payload
    except Exception as ex:
        fallback = build_fallback_universe(error=str(ex))
        save_symbol_universe(fallback)
        return fallback


def print_symbol_universe_summary(payload: Dict[str, Any]) -> None:
    print("BINANCE SYMBOL UNIVERSE")
    print("=======================")
    print("Mode: analytical only")
    print("Binance public API used:", payload.get("binance_public_api_used"))
    print("Fallback:", payload.get("fallback"))
    print("Safe to continue:", payload.get("safe_to_continue"))
    print("Symbols:", payload.get("symbols_count"))
    print("Base assets:", payload.get("base_assets_count"))
    print("Quote assets:", payload.get("quote_assets_count"))

    if payload.get("error"):
        print("Error:", payload.get("error"))

    if payload.get("warnings"):
        print("Warnings:", ", ".join(str(item) for item in payload["warnings"]))
    else:
        print("Warnings: none")

    print()
    print("SAMPLE BASE ASSETS")
    print("==================")
    print(", ".join(payload.get("base_assets", [])[:50]))

    print()
    print("SAFETY")
    print("======")
    print("[OK] This script did not create orders.")
    print("[OK] This script did not start trading bot.")
    print("[OK] This script uses Binance only for public exchange metadata.")


def main() -> None:
    payload = load_symbol_universe(refresh=True)
    print_symbol_universe_summary(payload)


if __name__ == "__main__":
    main()
