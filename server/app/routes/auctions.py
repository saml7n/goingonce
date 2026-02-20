from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models import Auction, AuctionStatus, Bid
from app.schemas import (
    AuctionCreatedResponse,
    AuctionDetailResponse,
    AuctionResponse,
    BidResponse,
    BidResultResponse,
    CreateAuctionRequest,
    PlaceBidRequest,
)
from app.services.locks import auction_locks

ANTI_SNIPE_WINDOW_SECONDS = 30
ANTI_SNIPE_EXTENSION_SECONDS = 30

router = APIRouter(prefix="/auctions", tags=["auctions"])


@router.post("", response_model=AuctionCreatedResponse, status_code=201)
async def create_auction(
    body: CreateAuctionRequest,
    session: AsyncSession = Depends(get_session),
) -> AuctionCreatedResponse:
    now = datetime.now(timezone.utc)
    end_time = now + timedelta(seconds=body.duration_seconds)

    auction = Auction(
        item_name=body.item_name,
        starting_price=body.starting_price,
        current_price=body.starting_price,
        end_time=end_time,
    )

    session.add(auction)
    await session.commit()
    await session.refresh(auction)

    return AuctionCreatedResponse(
        id=auction.id,
        item_name=auction.item_name,
        starting_price=auction.starting_price,
        end_time=auction.end_time,
    )


@router.get("", response_model=list[AuctionResponse])
async def list_auctions(
    session: AsyncSession = Depends(get_session),
) -> list[AuctionResponse]:
    result = await session.execute(
        select(Auction).order_by(Auction.created_at.desc())  # type: ignore[attr-defined]
    )
    auctions = result.scalars().all()
    return [AuctionResponse.model_validate(a, from_attributes=True) for a in auctions]


@router.get("/{auction_id}", response_model=AuctionDetailResponse)
async def get_auction(
    auction_id: str,
    session: AsyncSession = Depends(get_session),
) -> AuctionDetailResponse:
    auction = await session.get(Auction, auction_id)
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")

    result = await session.execute(
        select(Bid)
        .where(Bid.auction_id == auction_id)
        .order_by(Bid.created_at.desc())  # type: ignore[attr-defined]
    )
    bids = result.scalars().all()

    return AuctionDetailResponse(
        **AuctionResponse.model_validate(auction, from_attributes=True).model_dump(),
        bids=[BidResponse.model_validate(b, from_attributes=True) for b in bids],
    )


@router.post("/{auction_id}/bid", response_model=BidResultResponse)
async def place_bid(
    auction_id: str,
    body: PlaceBidRequest,
    session: AsyncSession = Depends(get_session),
) -> BidResultResponse:
    lock = auction_locks.get(auction_id)

    async with lock:
        # Re-read auction state under lock
        auction = await session.get(Auction, auction_id)
        if not auction:
            raise HTTPException(status_code=404, detail="Auction not found")

        # Check auction has ended (status flag)
        if auction.status == AuctionStatus.ended:
            raise HTTPException(status_code=410, detail="Auction has ended")

        now = datetime.now(timezone.utc)

        # Check auction has expired by time (defense in depth)
        if auction.end_time.tzinfo is None:
            end_time = auction.end_time.replace(tzinfo=timezone.utc)
        else:
            end_time = auction.end_time

        if now >= end_time:
            raise HTTPException(status_code=410, detail="Auction has ended")

        # Validate bid amount
        if body.amount <= auction.current_price:
            raise HTTPException(
                status_code=400,
                detail=f"Bid must be higher than current price: {auction.current_price}",
            )

        # Track previous bidder for outbid notifications (Story 4)
        previous_bidder_id = auction.current_bidder_id

        # Create the bid
        bid = Bid(
            auction_id=auction_id,
            bidder_id=body.bidder_id,
            bidder_name=body.bidder_name,
            amount=body.amount,
        )
        session.add(bid)

        # Update auction state
        auction.current_price = body.amount
        auction.current_bidder_id = body.bidder_id
        auction.current_bidder_name = body.bidder_name

        # Anti-sniping: extend if bid is in the last 30s
        time_remaining = (end_time - now).total_seconds()
        time_extended = False
        if time_remaining < ANTI_SNIPE_WINDOW_SECONDS:
            auction.end_time = auction.end_time + timedelta(
                seconds=ANTI_SNIPE_EXTENSION_SECONDS
            )
            time_extended = True

        session.add(auction)
        await session.commit()
        await session.refresh(auction)
        await session.refresh(bid)

    # Build response (outside lock — no DB writes here)
    auction_resp = AuctionResponse.model_validate(auction, from_attributes=True)
    bid_resp = BidResponse.model_validate(bid, from_attributes=True)

    message = "Bid placed successfully"
    if time_extended:
        message += f" (time extended by {ANTI_SNIPE_EXTENSION_SECONDS}s)"

    return BidResultResponse(
        success=True,
        message=message,
        auction=auction_resp,
        bid=bid_resp,
    )
