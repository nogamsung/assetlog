"""Base crypto-ticker → human-readable name map.

Used to populate AssetSymbol.name for crypto rows imported via Upbit (where
the trade payload only carries the base ticker, e.g. ``"BTC"``). Without
this, every crypto AssetSymbol fell back to ``name = symbol`` and the UI
showed ``BTC`` twice — once as ticker and once as name.

Curated by hand for the most common spot-tradable cryptos. Unknown tickers
gracefully fall back to ``None`` so the existing ``name = symbol`` default
still applies.
"""

from __future__ import annotations

CRYPTO_NAMES: dict[str, str] = {
    # Top market-cap layer-1 / payment tokens
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "BNB": "BNB",
    "SOL": "Solana",
    "XRP": "XRP",
    "ADA": "Cardano",
    "AVAX": "Avalanche",
    "TRX": "TRON",
    "DOT": "Polkadot",
    "MATIC": "Polygon",
    "LTC": "Litecoin",
    "BCH": "Bitcoin Cash",
    "ATOM": "Cosmos",
    "NEAR": "NEAR Protocol",
    "ALGO": "Algorand",
    "ICP": "Internet Computer",
    "ETC": "Ethereum Classic",
    "XLM": "Stellar",
    "FIL": "Filecoin",
    "APT": "Aptos",
    "SUI": "Sui",
    "HBAR": "Hedera",
    "VET": "VeChain",
    "EOS": "EOS",
    "XTZ": "Tezos",
    # Stablecoins
    "USDT": "Tether",
    "USDC": "USD Coin",
    "DAI": "Dai",
    "TUSD": "TrueUSD",
    "FDUSD": "First Digital USD",
    # Memes & community
    "DOGE": "Dogecoin",
    "SHIB": "Shiba Inu",
    "PEPE": "Pepe",
    "BONK": "Bonk",
    "WIF": "dogwifhat",
    # DeFi / governance
    "UNI": "Uniswap",
    "LINK": "Chainlink",
    "AAVE": "Aave",
    "MKR": "Maker",
    "COMP": "Compound",
    "SNX": "Synthetix",
    "CRV": "Curve DAO",
    "LDO": "Lido DAO",
    "1INCH": "1inch",
    # Korean exchange staples
    "KLAY": "Klaytn",
    "WEMIX": "WEMIX",
    "STRIKE": "Strike",
    "CTC": "Creditcoin",
    # Gaming / NFT
    "AXS": "Axie Infinity",
    "SAND": "The Sandbox",
    "MANA": "Decentraland",
    "GALA": "Gala",
    "ENJ": "Enjin Coin",
    "APE": "ApeCoin",
}


def lookup_crypto_name(base: str) -> str | None:
    """Return the canonical display name for a crypto base ticker, or None.

    *base* is the part before the slash in a ccxt pair (``BTC`` in ``BTC/KRW``)
    or the standalone ticker when no slash is present. Lookup is case-sensitive
    against uppercase keys.
    """
    return CRYPTO_NAMES.get(base.upper())
