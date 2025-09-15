from fastapi import APIRouter, Depends
from typing import List, Optional, Dict, Any

# Adjust the import path to use the new crypto service
from ..crypto_service import get_crypto_service

router = APIRouter(
    prefix="/api/active-trades",
    tags=["active-trades"],
)

@router.get("/", response_model=List[Dict[str, Any]])
async def get_live_active_trades():
    """
    Endpoint to fetch and return a list of currently active trades
    directly from the crypto exchange.

    Returns positions from the crypto exchange.
    """
    crypto_service = get_crypto_service()
    positions_result = await crypto_service.get_positions()

    if positions_result.get("success", False):
        positions = positions_result.get("positions", [])
        # Transform positions to match expected format
        active_trades = []
        for position in positions:
            trade = {
                "symbol": position.get("symbol"),
                "side": position.get("side"),
                "size": position.get("size"),
                "entry_price": position.get("entry_price"),
                "current_price": position.get("mark_price"),
                "pnl": position.get("pnl", 0),
                "timestamp": position.get("timestamp")
            }
            active_trades.append(trade)
        return active_trades
    else:
        return [] 