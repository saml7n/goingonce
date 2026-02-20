import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel


class AuctionStatus(str, Enum):
    active = "active"
    ended = "ended"


class Auction(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    item_name: str = Field(index=True)
    starting_price: float = Field(ge=0.01)
    current_price: float = Field(ge=0.01)
    current_bidder_id: str | None = Field(default=None)
    current_bidder_name: str | None = Field(default=None)
    end_time: datetime = Field(index=True)
    status: AuctionStatus = Field(default=AuctionStatus.active, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Bid(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    auction_id: str = Field(foreign_key="auction.id", index=True)
    bidder_id: str
    bidder_name: str
    amount: float = Field(ge=0.01)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
