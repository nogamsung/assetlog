from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.price import PriceSnapshot
from app.schemas.price import PriceRead
from app.scheduler.price_refresher import refresh_all_prices

router = APIRouter()


@router.get("/latest", response_model=list[PriceRead])
def latest_prices(db: Session = Depends(get_db)):
    subq = (
        db.query(PriceSnapshot.symbol, func.max(PriceSnapshot.fetched_at).label("latest"))
        .group_by(PriceSnapshot.symbol)
        .subquery()
    )
    return (
        db.query(PriceSnapshot)
        .join(subq, (PriceSnapshot.symbol == subq.c.symbol) & (PriceSnapshot.fetched_at == subq.c.latest))
        .all()
    )


@router.post("/refresh", status_code=202)
def trigger_refresh():
    refresh_all_prices()
    return {"status": "refreshed"}
