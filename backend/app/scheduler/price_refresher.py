import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.holding import Holding
from app.models.price import PriceSnapshot
from app.services.price_fetcher import fetch_price

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def refresh_all_prices() -> None:
    db = SessionLocal()
    try:
        symbols = {(h.asset_type, h.symbol) for h in db.query(Holding).all()}
        for asset_type, symbol in symbols:
            try:
                result = fetch_price(asset_type, symbol)
                db.add(
                    PriceSnapshot(
                        symbol=symbol,
                        asset_type=asset_type.value,
                        price=result.price,
                        currency=result.currency,
                    )
                )
            except Exception as exc:
                logger.warning("Failed to fetch %s/%s: %s", asset_type, symbol, exc)
        db.commit()
    finally:
        db.close()


def start_scheduler() -> None:
    scheduler.add_job(
        refresh_all_prices,
        "interval",
        minutes=settings.refresh_interval_minutes,
        id="refresh_prices",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
