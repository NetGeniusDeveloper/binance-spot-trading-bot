import re
from typing import Iterable, List


ALIASES = {
    "BITCOIN": "BTC",
    "ETHEREUM": "ETH",
    "ETHER": "ETH",
    "SOLANA": "SOL",
    "TONCOIN": "TON",
    "CHAINLINK": "LINK",
    "AVALANCHE": "AVAX",
    "POLKADOT": "DOT",
    "COSMOS": "ATOM",
    "CARDANO": "ADA",
    "RIPPLE": "XRP",
    "ARBITRUM": "ARB",
    "OPTIMISM": "OP",
    "APTOS": "APT",
    "RENDER": "RNDR",
    "FETCH": "FET",
}

QUOTE_ASSETS = {
    "USDT",
    "USDC",
    "BUSD",
    "FDUSD",
    "USD",
    "BTC",
    "ETH",
}


def normalize_watchlist(watchlist: Iterable[str]) -> set[str]:
    return {
        str(item).strip().upper()
        for item in watchlist
        if str(item).strip()
    }


def add_ticker(result: List[str], ticker: str, allowed: set[str]) -> None:
    normalized = ticker.strip().upper()

    if normalized in ALIASES:
        normalized = ALIASES[normalized]

    if normalized not in allowed:
        return

    if normalized not in result:
        result.append(normalized)


def extract_pair_tickers(text: str, allowed: set[str]) -> List[str]:
    result: List[str] = []

    # Examples: TON/USDT, ETH-USDT, SOL_USDT, BTCUSDT
    pair_patterns = [
        r"\b([A-Za-z]{2,12})\s*/\s*(USDT|USDC|BUSD|FDUSD|USD)\b",
        r"\b([A-Za-z]{2,12})\s*-\s*(USDT|USDC|BUSD|FDUSD|USD)\b",
        r"\b([A-Za-z]{2,12})\s*_\s*(USDT|USDC|BUSD|FDUSD|USD)\b",
        r"\b([A-Za-z]{2,12})(USDT|USDC|BUSD|FDUSD|USD)\b",
    ]

    for pattern in pair_patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            base = match.group(1)
            add_ticker(result, base, allowed)

    return result


def extract_tagged_tickers(text: str, allowed: set[str]) -> List[str]:
    result: List[str] = []

    # Examples: $TON, #TON
    for match in re.finditer(r"(?<![A-Za-z0-9])[$#]([A-Za-z]{2,12})\b", text):
        add_ticker(result, match.group(1), allowed)

    return result


def extract_alias_tickers(text: str, allowed: set[str]) -> List[str]:
    result: List[str] = []
    upper_text = text.upper()

    for alias, ticker in ALIASES.items():
        if ticker not in allowed:
            continue

        pattern = r"\b" + re.escape(alias) + r"\b"

        if re.search(pattern, upper_text):
            add_ticker(result, ticker, allowed)

    return result


def extract_plain_tickers(text: str, allowed: set[str]) -> List[str]:
    result: List[str] = []

    # Plain words are accepted only if they are in WATCHLIST.
    # This prevents common words from becoming fake tickers.
    for match in re.finditer(r"\b[A-Za-z]{2,12}\b", text):
        word = match.group(0).upper()

        if word in QUOTE_ASSETS and word not in allowed:
            continue

        add_ticker(result, word, allowed)

    return result


def extract_tickers(text: str, watchlist: Iterable[str]) -> List[str]:
    """
    Extract crypto tickers from a message using a safe watchlist.

    Supported examples:
    - $TON
    - #TON
    - TON/USDT
    - TON-USDT
    - TON_USDT
    - TONUSDT
    - Bitcoin
    - Ethereum
    - Solana
    - Toncoin

    Telegram/social mention is NOT a trading signal.
    This function only extracts candidates for further analysis.
    """
    if not text:
        return []

    allowed = normalize_watchlist(watchlist)

    if not allowed:
        return []

    result: List[str] = []

    for extractor in (
        extract_pair_tickers,
        extract_tagged_tickers,
        extract_alias_tickers,
        extract_plain_tickers,
    ):
        for ticker in extractor(text, allowed):
            add_ticker(result, ticker, allowed)

    return result


if __name__ == "__main__":
    from config import WATCHLIST

    samples = [
        "$TON is moving fast",
        "TON/USDT looks interesting after retest",
        "#SOL breakout soon",
        "Bitcoin and Ethereum are under pressure",
        "Toncoin integration news",
        "This is just normal text without crypto ticker",
        "urgent 100x moon pump guaranteed",
        "LINKUSDT volume is rising",
    ]

    for sample in samples:
        print(sample)
        print("tickers:", extract_tickers(sample, WATCHLIST))
        print()
