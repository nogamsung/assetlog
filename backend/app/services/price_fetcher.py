from dataclasses import dataclass

from app.models.holding import AssetType


@dataclass
class PriceResult:
    price: float
    currency: str


def fetch_kr_stock(symbol: str) -> PriceResult:
    from pykrx import stock
    from datetime import datetime

    today = datetime.now().strftime("%Y%m%d")
    df = stock.get_market_ohlcv(today, today, symbol)
    price = float(df["종가"].iloc[-1])
    return PriceResult(price=price, currency="KRW")


def fetch_us_stock(symbol: str) -> PriceResult:
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    price = float(ticker.fast_info["last_price"])
    return PriceResult(price=price, currency="USD")


def fetch_crypto(symbol: str) -> PriceResult:
    import ccxt

    exchange = ccxt.binance()
    market = f"{symbol}/USDT"
    ticker = exchange.fetch_ticker(market)
    return PriceResult(price=float(ticker["last"]), currency="USDT")


def fetch_price(asset_type: AssetType, symbol: str) -> PriceResult:
    if asset_type == AssetType.KR_STOCK:
        return fetch_kr_stock(symbol)
    if asset_type == AssetType.US_STOCK:
        return fetch_us_stock(symbol)
    if asset_type == AssetType.CRYPTO:
        return fetch_crypto(symbol)
    raise ValueError(f"Unsupported asset type: {asset_type}")
