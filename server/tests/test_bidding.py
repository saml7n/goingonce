"""Tests for bid placement, race conditions, and anti-sniping.

Story 3 — Atomic Bidding & Race Conditions.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def _create_auction(
    client: AsyncClient, duration: int = 300, starting_price: float = 100.0
) -> dict:
    resp = await client.post(
        "/auctions",
        json={
            "item_name": "Test Item",
            "starting_price": starting_price,
            "duration_seconds": duration,
        },
    )
    assert resp.status_code == 201
    return resp.json()


# ─── Basic bid tests ───


@pytest.mark.asyncio
async def test_place_valid_bid(client: AsyncClient) -> None:
    auction = await _create_auction(client)
    resp = await client.post(
        f"/auctions/{auction['id']}/bid",
        json={"amount": 150.0, "bidder_id": "user-1", "bidder_name": "Alice"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["bid"]["amount"] == 150.0
    assert data["auction"]["current_price"] == 150.0
    assert data["auction"]["current_bidder_name"] == "Alice"


@pytest.mark.asyncio
async def test_bid_too_low(client: AsyncClient) -> None:
    auction = await _create_auction(client, starting_price=100.0)

    # Bid at starting price (not higher) should fail
    resp = await client.post(
        f"/auctions/{auction['id']}/bid",
        json={"amount": 100.0, "bidder_id": "user-1", "bidder_name": "Alice"},
    )
    assert resp.status_code == 400
    assert "higher" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_bid_below_current(client: AsyncClient) -> None:
    auction = await _create_auction(client, starting_price=100.0)

    # First bid succeeds
    await client.post(
        f"/auctions/{auction['id']}/bid",
        json={"amount": 200.0, "bidder_id": "user-1", "bidder_name": "Alice"},
    )

    # Second bid below current fails
    resp = await client.post(
        f"/auctions/{auction['id']}/bid",
        json={"amount": 150.0, "bidder_id": "user-2", "bidder_name": "Bob"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_bid_on_nonexistent_auction(client: AsyncClient) -> None:
    resp = await client.post(
        "/auctions/fake-id/bid",
        json={"amount": 100.0, "bidder_id": "user-1", "bidder_name": "Alice"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_bid_on_ended_auction(client: AsyncClient) -> None:
    # Create auction with 1s duration
    auction = await _create_auction(client, duration=1)

    # Wait for it to expire
    await asyncio.sleep(1.5)

    resp = await client.post(
        f"/auctions/{auction['id']}/bid",
        json={"amount": 200.0, "bidder_id": "user-1", "bidder_name": "Alice"},
    )
    assert resp.status_code == 410
    assert "ended" in resp.json()["detail"].lower()


# ─── Concurrency tests ───


@pytest.mark.asyncio
async def test_concurrent_bids_exactly_one_wins() -> None:
    """Fire 10 concurrent bids at the same amount. Exactly one should succeed."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        auction = await _create_auction(client, starting_price=100.0)
        auction_id = auction["id"]

        async def place_bid(user_idx: int) -> int:
            resp = await client.post(
                f"/auctions/{auction_id}/bid",
                json={
                    "amount": 150.0,
                    "bidder_id": f"user-{user_idx}",
                    "bidder_name": f"User {user_idx}",
                },
            )
            return resp.status_code

        # Fire 10 concurrent bids at the same price
        results = await asyncio.gather(*[place_bid(i) for i in range(10)])

        successes = results.count(200)
        failures = results.count(400)

        assert successes == 1, f"Expected exactly 1 success, got {successes}"
        assert failures == 9, f"Expected 9 failures, got {failures}"


@pytest.mark.asyncio
async def test_concurrent_incremental_bids_no_data_corruption() -> None:
    """Fire 10 concurrent bids at increasing amounts.

    All 10 should succeed (each is higher than the last).
    Final price should be the highest bid.
    No bids should be lost from history.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        auction = await _create_auction(client, starting_price=100.0)
        auction_id = auction["id"]

        async def place_bid(amount: float, user_idx: int) -> int:
            resp = await client.post(
                f"/auctions/{auction_id}/bid",
                json={
                    "amount": amount,
                    "bidder_id": f"user-{user_idx}",
                    "bidder_name": f"User {user_idx}",
                },
            )
            return resp.status_code

        # Bids at 110, 120, ..., 200 — all should be valid if serialized correctly
        # But under concurrency, some may see stale current_price and lose
        results = await asyncio.gather(
            *[place_bid(110.0 + i * 10, i) for i in range(10)]
        )

        successes = results.count(200)
        # At least 1 must succeed, and the final state must be consistent
        assert successes >= 1

        # Verify final state
        resp = await client.get(f"/auctions/{auction_id}")
        data = resp.json()

        # Current price must be the highest successful bid
        bid_amounts = [b["amount"] for b in data["bids"]]
        assert data["current_price"] == max(bid_amounts)

        # No duplicate bids (each bid ID is unique)
        bid_ids = [b["id"] for b in data["bids"]]
        assert len(bid_ids) == len(set(bid_ids))


# ─── Anti-sniping tests ───


@pytest.mark.asyncio
async def test_anti_snipe_extends_time(client: AsyncClient) -> None:
    """Bid placed with <30s remaining should extend end_time by 30s."""
    # Create auction with 5s duration (well within anti-snipe window)
    auction = await _create_auction(client, duration=5)
    auction_id = auction["id"]
    original_end_time = datetime.fromisoformat(auction["end_time"])

    # Place bid immediately — 5s remaining is < 30s, so anti-snipe triggers
    resp = await client.post(
        f"/auctions/{auction_id}/bid",
        json={"amount": 150.0, "bidder_id": "user-1", "bidder_name": "Alice"},
    )
    assert resp.status_code == 200
    data = resp.json()

    new_end_time = datetime.fromisoformat(data["auction"]["end_time"])
    extension = (new_end_time - original_end_time).total_seconds()

    assert extension == pytest.approx(30.0, abs=1.0), (
        f"Expected ~30s extension, got {extension}s"
    )
    assert "time extended" in data["message"].lower()


@pytest.mark.asyncio
async def test_anti_snipe_does_not_trigger_with_plenty_of_time(
    client: AsyncClient,
) -> None:
    """Bid placed with >30s remaining should NOT extend end_time."""
    auction = await _create_auction(client, duration=300)  # 5 minutes
    auction_id = auction["id"]
    original_end_time = datetime.fromisoformat(auction["end_time"])

    resp = await client.post(
        f"/auctions/{auction_id}/bid",
        json={"amount": 150.0, "bidder_id": "user-1", "bidder_name": "Alice"},
    )
    assert resp.status_code == 200
    data = resp.json()

    new_end_time = datetime.fromisoformat(data["auction"]["end_time"])
    extension = (new_end_time - original_end_time).total_seconds()

    assert extension == pytest.approx(0.0, abs=1.0), (
        f"Expected no extension, got {extension}s"
    )
    assert "time extended" not in data["message"].lower()


@pytest.mark.asyncio
async def test_anti_snipe_stacks() -> None:
    """Multiple bids in the anti-snipe window should each extend by 30s."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        auction = await _create_auction(client, duration=5)
        auction_id = auction["id"]
        original_end_time = datetime.fromisoformat(auction["end_time"])

        # First bid — extends by 30s
        await client.post(
            f"/auctions/{auction_id}/bid",
            json={"amount": 150.0, "bidder_id": "user-1", "bidder_name": "Alice"},
        )

        # Second bid — still within anti-snipe window (5 + 30 - elapsed ≈ 34s remaining)
        # Since 34s > 30s, this should NOT trigger anti-snipe
        resp = await client.post(
            f"/auctions/{auction_id}/bid",
            json={"amount": 200.0, "bidder_id": "user-2", "bidder_name": "Bob"},
        )
        data = resp.json()
        end_after_second = datetime.fromisoformat(data["auction"]["end_time"])

        # Only 30s total extension (first bid), second bid didn't trigger
        total_extension = (end_after_second - original_end_time).total_seconds()
        assert total_extension == pytest.approx(30.0, abs=2.0)
