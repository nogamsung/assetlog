"""ORM models — imported here so Alembic autogenerate can detect all tables."""

from app.models.asset_symbol import AssetSymbol
from app.models.cash_account import CashAccount
from app.models.cash_account_transaction import CashAccountTransaction
from app.models.dividend import Dividend
from app.models.fx_rate import FxRate
from app.models.fx_rate_snapshot import FxRateSnapshot
from app.models.isin_ticker_cache import IsinTickerCache
from app.models.kr_name_cache import KrNameCache
from app.models.login_attempt import LoginAttempt
from app.models.target_allocation import TargetAllocation
from app.models.transaction import Transaction
from app.models.user_asset import UserAsset

__all__ = [
    "AssetSymbol",
    "CashAccount",
    "CashAccountTransaction",
    "Dividend",
    "FxRate",
    "FxRateSnapshot",
    "IsinTickerCache",
    "KrNameCache",
    "LoginAttempt",
    "TargetAllocation",
    "Transaction",
    "UserAsset",
]
