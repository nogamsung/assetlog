from fastapi import APIRouter

from app.api.routes import holdings, prices

api_router = APIRouter()
api_router.include_router(holdings.router, prefix="/holdings", tags=["holdings"])
api_router.include_router(prices.router, prefix="/prices", tags=["prices"])
