"""Tests for WebSocket real-time auction updates."""

import asyncio
import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.ws.manager import manager


# ---------- helpers ----------

async def create_auction(client: AsyncClient, duration: int = 300) -> dict:
    resp = await client.post(
        "/auctions",
        json={
            "item_name": "WS Test Item",
            "starting_price": 100.0,
            "duration_seconds": duration,
        },
    )
    assert resp.status_code == 201
    return resp.json()


async def place_bid(client: AsyncClient, auction_id: str, amount: float, bidder_id: str = "bidder-1", bidder_name: str = "Alice") -> dict:
    resp = await client.post(
        f"/auctions/{auction_id}/bid",
        json={
            "amount": amount,
            "bidder_id": bidder_id,
            "bidder_name": bidder_name,
        },
    )
    return resp.json()


# ---------- ConnectionManager unit tests ----------

class TestConnectionManager:
    def test_connect_and_room_size(self):
        mgr = manager
        # start clean
        mgr._rooms.clear()

        class FakeWS:
            pass

        ws1 = FakeWS()
        ws2 = FakeWS()
        mgr.connect("auction-1", "user-a", ws1)
        mgr.connect("auction-1", "user-b", ws2)
        assert mgr.room_size("auction-1") == 2

    def test_disconnect_removes_connection(self):
        mgr = manager
        mgr._rooms.clear()

        class FakeWS:
            pass

        ws1 = FakeWS()
        ws2 = FakeWS()
        mgr.connect("auction-2", "user-a", ws1)
        mgr.connect("auction-2", "user-b", ws2)
        mgr.disconnect("auction-2", ws1)
        assert mgr.room_size("auction-2") == 1

    def test_disconnect_cleans_up_empty_room(self):
        mgr = manager
        mgr._rooms.clear()

        class FakeWS:
            pass

        ws = FakeWS()
        mgr.connect("auction-3", "user-a", ws)
        mgr.disconnect("auction-3", ws)
        assert "auction-3" not in mgr._rooms

    def test_disconnect_nonexistent_room_is_noop(self):
        mgr = manager
        mgr._rooms.clear()

        class FakeWS:
            pass

        mgr.disconnect("nonexistent", FakeWS())  # should not raise


# ---------- WebSocket integration tests ----------

@pytest.mark.asyncio
async def test_ws_connect_receives_initial_state(client: AsyncClient):
    """Connecting via WS should receive a 'state' message with auction data."""
    auction = await create_auction(client)
    auction_id = auction["id"]

    from starlette.testclient import TestClient
    # Use Starlette's sync TestClient for WebSocket testing
    with TestClient(app) as sync_client:
        with sync_client.websocket_connect(
            f"/auctions/{auction_id}/ws?user_id=test-user"
        ) as ws:
            data = ws.receive_json()
            assert data["type"] == "state"
            assert data["auction"]["id"] == auction_id
            assert data["auction"]["current_price"] == 100.0
            assert "server_time" in data
            assert "bids" in data


@pytest.mark.asyncio
async def test_ws_invalid_auction_returns_error(client: AsyncClient):
    """Connecting to a non-existent auction should return an error and close."""
    from starlette.testclient import TestClient
    with TestClient(app) as sync_client:
        with sync_client.websocket_connect(
            "/auctions/nonexistent-id/ws?user_id=test-user"
        ) as ws:
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "not found" in data["message"].lower()


@pytest.mark.asyncio
async def test_ws_broadcast_on_bid(client: AsyncClient):
    """A bid should broadcast new_bid to all connected WebSocket clients."""
    auction = await create_auction(client)
    auction_id = auction["id"]

    from starlette.testclient import TestClient
    with TestClient(app) as sync_client:
        with sync_client.websocket_connect(
            f"/auctions/{auction_id}/ws?user_id=watcher"
        ) as ws:
            # Consume initial state
            ws.receive_json()

            # Place a bid via HTTP (use sync_client for simplicity)
            bid_resp = sync_client.post(
                f"/auctions/{auction_id}/bid",
                json={
                    "amount": 150.0,
                    "bidder_id": "bidder-1",
                    "bidder_name": "Alice",
                },
            )
            assert bid_resp.status_code == 200

            # Should receive new_bid message
            msg = ws.receive_json()
            assert msg["type"] == "new_bid"
            assert msg["bid"]["amount"] == 150.0
            assert msg["bid"]["bidder_name"] == "Alice"
            assert msg["auction"]["current_price"] == 150.0
            assert "server_time" in msg


@pytest.mark.asyncio
async def test_ws_outbid_notification(client: AsyncClient):
    """The previously leading bidder should receive an 'outbid' message."""
    auction = await create_auction(client)
    auction_id = auction["id"]

    from starlette.testclient import TestClient
    with TestClient(app) as sync_client:
        # Bidder 1 connects
        with sync_client.websocket_connect(
            f"/auctions/{auction_id}/ws?user_id=bidder-1"
        ) as ws1:
            ws1.receive_json()  # initial state

            # Bidder 1 places first bid
            sync_client.post(
                f"/auctions/{auction_id}/bid",
                json={"amount": 150.0, "bidder_id": "bidder-1", "bidder_name": "Alice"},
            )
            # Bidder 1 receives new_bid broadcast
            msg = ws1.receive_json()
            assert msg["type"] == "new_bid"

            # Bidder 2 outbids
            sync_client.post(
                f"/auctions/{auction_id}/bid",
                json={"amount": 200.0, "bidder_id": "bidder-2", "bidder_name": "Bob"},
            )

            # Bidder 1 should receive new_bid AND outbid
            messages = []
            messages.append(ws1.receive_json())
            messages.append(ws1.receive_json())

            types = {m["type"] for m in messages}
            assert "new_bid" in types
            assert "outbid" in types

            outbid_msg = next(m for m in messages if m["type"] == "outbid")
            assert outbid_msg["by"] == "Bob"
            assert outbid_msg["new_price"] == 200.0


@pytest.mark.asyncio
async def test_ws_ping_pong(client: AsyncClient):
    """Client ping should receive pong with server_time."""
    auction = await create_auction(client)
    auction_id = auction["id"]

    from starlette.testclient import TestClient
    with TestClient(app) as sync_client:
        with sync_client.websocket_connect(
            f"/auctions/{auction_id}/ws?user_id=test-user"
        ) as ws:
            ws.receive_json()  # initial state
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"
            assert "server_time" in data


@pytest.mark.asyncio
async def test_ws_time_extended_broadcast(client: AsyncClient):
    """Anti-snipe extension should broadcast time_extended to all clients."""
    # Create auction with very short duration so anti-snipe triggers
    auction = await create_auction(client, duration=5)
    auction_id = auction["id"]

    from starlette.testclient import TestClient
    with TestClient(app) as sync_client:
        with sync_client.websocket_connect(
            f"/auctions/{auction_id}/ws?user_id=watcher"
        ) as ws:
            ws.receive_json()  # initial state

            # Place a bid (within anti-snipe window since duration=5s)
            sync_client.post(
                f"/auctions/{auction_id}/bid",
                json={"amount": 150.0, "bidder_id": "bidder-1", "bidder_name": "Alice"},
            )

            # Should receive new_bid and time_extended
            messages = []
            messages.append(ws.receive_json())
            messages.append(ws.receive_json())

            types = {m["type"] for m in messages}
            assert "new_bid" in types
            assert "time_extended" in types

            ext_msg = next(m for m in messages if m["type"] == "time_extended")
            assert "new_end_time" in ext_msg
