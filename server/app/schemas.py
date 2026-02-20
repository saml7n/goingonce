from datetime import datetime

from pydantic import BaseModel, Field


# --- Requests ---


class CreateAuctionRequest(BaseModel):
    item_name: str = Field(min_length=1, max_length=200)
    starting_price: float = Field(gt=0)
    duration_seconds: int = Field(gt=0, le=86400)  # max 24h


class PlaceBidRequest(BaseModel):
    amount: float = Field(gt=0)
    bidder_id: str = Field(min_length=1)
    bidder_name: str = Field(min_length=1, max_length=100)


# --- Responses ---


class AuctionResponse(BaseModel):
    id: str
    item_name: str
    starting_price: float
    current_price: float
    current_bidder_id: str | None
    current_bidder_name: str | None
    end_time: datetime
    status: str
    created_at: datetime


class AuctionCreatedResponse(BaseModel):
    id: str
    item_name: str
    starting_price: float
    end_time: datetime


class BidResponse(BaseModel):
    id: str
    auction_id: str
    bidder_id: str
    bidder_name: str
    amount: float
    created_at: datetime


class AuctionDetailResponse(AuctionResponse):
    bids: list[BidResponse] = []


class BidResultResponse(BaseModel):
    success: bool
    message: str
    auction: AuctionResponse
    bid: BidResponse | None = None
