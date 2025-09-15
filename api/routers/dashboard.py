from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from .. import crud, schemas
from ..database import get_db
from ..crypto_service import get_crypto_service

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
)

@router.get("/")
def read_dashboard_data(
    db: Session = Depends(get_db),
    timeframe: str = Query("1W", description="Timeframe for performance chart")
):
    """
    Endpoint to get all data required for the main dashboard page.
    """
    kpis = crud.get_dashboard_kpis(db)
    overview_chart = crud.get_overview_chart_data(db)
    # Pass the timeframe to the chart data function
    filters = {"timeframe": timeframe, "asset": "All Assets"}
    performance_chart_data = crud.get_performance_chart_data(db, filters=filters)
    
    return {
        "kpis": kpis,
        "overviewChart": overview_chart,
        "performanceChart": performance_chart_data["series"]
    }

@router.get("/account-info")
async def get_live_account_info():
    """
    Endpoint to get live account information (balance, equity) from crypto exchange.
    """
    crypto_service = get_crypto_service()
    account_info = await crypto_service.get_account_info()
    if account_info.get("success", False):
        balance_data = account_info.get("balance", {})
        # Calculate total balance in USDT or equivalent
        total_balance = 0.0
        for currency, data in balance_data.items():
            if currency.upper() in ['USDT', 'USDC', 'BUSD']:
                total_balance += data.get("total", 0)

        return {
            "balance": total_balance,
            "equity": total_balance,  # For crypto, balance = equity
            "profit": 0.0,  # Would need to calculate unrealized P&L
            "exchange": account_info.get("exchange"),
            "connected": account_info.get("connected", False)
        }
    return {"error": "Could not retrieve account information"} 