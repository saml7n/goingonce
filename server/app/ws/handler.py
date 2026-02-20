"""WebSocket endpoint for real-time auction updates."""

from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models import Auction, Bid
from app.ws.manager import manager

router = APIRouter()


async def _build_state_message(session: AsyncSession, auction_id: str) -> dict | None:
    """Build the initial state snapshot for a newly connected client."""
    result = await session.execute(select(Auction).where(Auction.id == auction_id))
    auction = result.scalar_one_or_none()
    if auction is None:
        return None

    bids_result = await session.execute(
        select(Bid).where(Bid.auction_id == auction_id).order_by(Bid.created_at.desc())
    )
    bids = bids_result.scalars().all()

    return {
        "type": "state",
        "auction": {
            "id": auction.id,
            "item_name": auction.item_name,
            "starting_price": auction.starting_price,
            "current_price": auction.current_price,
            "current_bidder_id": auction.current_bidder_id,
            "current_bidder_name": auction.current_bidder_name,
            "end_time": auction.end_time.isoformat(),
            "status": auction.status,
            "created_at": auction.created_at.isoformat(),
        },
        "bids": [
            {
                "id": b.id,
                "bidder_id": b.bidder_id,
                "bidder_name": b.bidder_name,
                "amount": b.amount,
                "created_at": b.created_at.isoformat(),
            }
            for b in bids
        ],
    }


@router.websocket("/auctions/{auction_id}/ws")
async def auction_websocket(
    websocket: WebSocket,
    auction_id: str,
    user_id: str = Query(...),
):
    await websocket.accept()

    # Send initial state
    async with async_session_factory() as session:
        state = await _build_state_message(session, auction_id)

    if state is None:
        await websocket.send_json({"type": "error", "message": "Auction not found"})
        await websocket.close(code=4004)
        return

    # Add server_time and send
    state["server_time"] = datetime.now(timezone.utc).isoformat()
    await websocket.send_json(state)

    # Register in room
    manager.connect(auction_id, user_id, websocket)

    try:
        # Keep connection alive — listen for pings / client messages
        while True:
            # We don't expect meaningful client messages, but we need to
            # keep the receive loop running to detect disconnects.
            data = await websocket.receive_text()
            # Client can send {"type": "ping"} — we respond with pong
            if "ping" in data:
                await websocket.send_json(
                    {
                        "type": "pong",
                        "server_time": datetime.now(timezone.utc).isoformat(),
                    }
                )
    except WebSocketDisconnect:
        manager.disconnect(auction_id, websocket)
    except Exception:
        manager.disconnect(auction_id, websocket)
