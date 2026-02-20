import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_auction(client: AsyncClient) -> None:
    response = await client.post(
        "/auctions",
        json={
            "item_name": "Vintage Watch",
            "starting_price": 100.0,
            "duration_seconds": 300,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["item_name"] == "Vintage Watch"
    assert data["starting_price"] == 100.0
    assert "id" in data
    assert "end_time" in data


@pytest.mark.asyncio
async def test_create_auction_invalid_price(client: AsyncClient) -> None:
    response = await client.post(
        "/auctions",
        json={
            "item_name": "Bad Item",
            "starting_price": -5.0,
            "duration_seconds": 60,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_auction_zero_price(client: AsyncClient) -> None:
    response = await client.post(
        "/auctions",
        json={
            "item_name": "Free Item",
            "starting_price": 0,
            "duration_seconds": 60,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_auction_empty_name(client: AsyncClient) -> None:
    response = await client.post(
        "/auctions",
        json={
            "item_name": "",
            "starting_price": 50.0,
            "duration_seconds": 60,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_auction(client: AsyncClient) -> None:
    # Create first
    create_resp = await client.post(
        "/auctions",
        json={
            "item_name": "Test Item",
            "starting_price": 50.0,
            "duration_seconds": 120,
        },
    )
    auction_id = create_resp.json()["id"]

    # Then fetch
    response = await client.get(f"/auctions/{auction_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == auction_id
    assert data["item_name"] == "Test Item"
    assert data["current_price"] == 50.0
    assert data["status"] == "active"
    assert data["bids"] == []


@pytest.mark.asyncio
async def test_get_auction_not_found(client: AsyncClient) -> None:
    response = await client.get("/auctions/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_auctions(client: AsyncClient) -> None:
    # Create two auctions
    await client.post(
        "/auctions",
        json={"item_name": "Item A", "starting_price": 10.0, "duration_seconds": 60},
    )
    await client.post(
        "/auctions",
        json={"item_name": "Item B", "starting_price": 20.0, "duration_seconds": 60},
    )

    response = await client.get("/auctions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    # Most recent first
    names = [a["item_name"] for a in data]
    assert "Item A" in names
    assert "Item B" in names
