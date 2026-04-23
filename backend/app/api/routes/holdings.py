from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.holding import Holding
from app.schemas.holding import HoldingCreate, HoldingRead

router = APIRouter()


@router.get("", response_model=list[HoldingRead])
def list_holdings(db: Session = Depends(get_db)):
    return db.query(Holding).order_by(Holding.created_at.desc()).all()


@router.post("", response_model=HoldingRead, status_code=201)
def create_holding(payload: HoldingCreate, db: Session = Depends(get_db)):
    holding = Holding(**payload.model_dump())
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return holding


@router.delete("/{holding_id}", status_code=204)
def delete_holding(holding_id: int, db: Session = Depends(get_db)):
    holding = db.get(Holding, holding_id)
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    db.delete(holding)
    db.commit()
