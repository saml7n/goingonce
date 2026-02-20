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
    CreateAuctionRequest,
)

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
