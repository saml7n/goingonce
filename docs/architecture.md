# GoingOnce — Real-time Auction System: Architecture & Plan

> **Status:** Planning / Pre-implementation  
> **Last updated:** 20 February 2026  
> **Approach:** FastAPI + WebSockets + SQLite (Atomic Bidding)

---

## 1. Vision & End State

GoingOnce is a high-performance real-time auction system that:

- **Creates auctions** with names, starting prices, and durations.
- **Handles real-time bidding** via WebSockets with ultra-low latency.
- **Prevents race conditions** using a per-auction lock pattern for atomic bid validation.
- **Synchronizes time** using server-authoritative timestamps on every WebSocket message.
- **Protects against sniping** by automatically extending auctions by 30s for late bids.
- **Notifies users immediately** when they've been outbid or an auction ends.
- **Provides a polished UI** with real-time countdowns, animations, and winner celebrations (confetti).

### What "done" looks like (PoC)

1. A user creates an auction (e.g., "Vintage Watch", $100, 5 mins).
2. Multiple users join the live auction view.
3. Users place bids; the system validates them (must be > current) and broadcasts updates to all clients within ~50ms.
4. If a user is outbid, they receive a targeted "Outbid!" notification.
5. If a bid arrives in the last 30s, the timer extends by 30s from the current `end_time` (anti-sniping).
6. When the timer hits zero, the auction closes, no more bids are accepted, and the winner is announced with a celebration.

---

## 2. System Architecture

```
┌─────────────┐       ┌──────────────────────────────────────────────┐
│   Bidder     │       │            GoingOnce Server (Python)         │
│  (browser)   │       │                                              │
│              │  ←──→ │  ┌──────────┐   ┌─────────┐   ┌──────────┐   │
│              │       │  │ WebSocket│──→│ Auction │──→│ SQLite   │   │
│              │       │  │ Manager  │   │ Manager │   │ (DB)     │   │
│              │       │  │ (PubSub) │   │ (Locks) │   └──────────┘   │
│              │       │  └────┬─────┘   └────┬────┘                  │
│              │       │       │              │                        │
│              │       │  ┌────▼─────┐   ┌────▼────┐                  │
│              │       │  │ Bid      │   │ Timer   │                  │
│              │       │  │ Validator│   │ Service │                  │
│              │       │  └──────────┘   └─────────┘                  │
│              │       └──────────────────────────────────────────────┘
│              │
│              │       ┌──────────────────────────────────────────────┐
│              │       │           Web Dashboard (React)              │
│   User       │  ←──→ │  ┌──────────────┐  ┌───────────────┐         │
│  (browser)   │       │  │ Auction      │  │ Live Bid      │         │
│              │       │  │ Creator      │  │ Dashboard     │         │
│              │       │  └──────────────┘  └───────────────┘         │
│              │       └──────────────────────────────────────────────┘
```

### Bidding Pipeline (Atomic & Real-time)

```
User places bid (POST /bid)
    │
    ▼
Acquire per-auction async Lock
    │
    ▼
Read Auction state from DB
    │
    ▼
Validate: Active? Time left? Amount > Current?
    │
    ▼
Write Bid + Update Auction (Price, Bidder, EndTime if anti-snipe)
    │
    ▼
Release Lock
    │
    ▼
Broadcast NEW_BID to all WS clients
Send OUTBID to previous high bidder
```

**Anti-sniping Rule:**
- If `end_time - now < 30s`: `end_time += 30s`.
- This *extends* the auction by 30 seconds from where it was, not resets to 30s. A bid at T-5s yields 35s remaining.

---

## 3. Technology Stack

| Layer | Technology | Why |
|---|---|---|
| **Server** | Python 3.12+ | Excellent async ecosystem; fast prototyping. |
| **Package manager** | uv | Fast, modern Python package manager. |
| **Web framework** | FastAPI | Async-native; automatic OpenAPI docs; WebSocket support. |
| **Database** | SQLite + SQLModel | Zero-config for PoC; atomic single-writer model. |
| **Concurrency** | `asyncio.Lock` | Simple, provably correct gating for bid validation. |
| **Frontend** | React + Vite | Fast HMR; industry standard. |
| **Styling** | Tailwind + shadcn/ui | Polished, professional components out of the box. |
| **Real-time** | WebSockets | Lowest latency for bid broadcasts. |
| **Time Sync** | Server-authoritative | Continuous offset correction in client. |

---

## 4. Data Models

### 4.1 Auction
- `id`: UUID (PK)
- `item_name`: str
- `starting_price`: Decimal
- `current_price`: Decimal
- `current_bidder_id`: str (UUID)
- `current_bidder_name`: str
- `end_time`: datetime (UTC)
- `status`: enum (active, ended)

### 4.2 Bid
- `id`: UUID (PK)
- `auction_id`: FK(Auction.id)
- `bidder_id`: str
- `bidder_name`: str
- `amount`: Decimal
- `timestamp`: datetime (UTC)

---

## 5. WebSocket Protocol

Messages are JSON objects with a `type` field.

| Type | Direction | Payload |
|---|---|---|
| `state` | Server → Client | Full auction object + `server_time` (sent on connect) |
| `new_bid` | Server → Client | Bid object + updated Auction + `server_time` |
| `outbid` | Server → Client | Minimal payload + `server_time` (targeted message) |
| `time_extended`| Server → Client | New `end_time` + `server_time` |
| `auction_ended`| Server → Client | Final Auction state + Winner details + `server_time` |

---

## 6. Project Structure

```
goingonce/
├── docs/               # Architecture, Stories
├── server/
│   ├── pyproject.toml  # uv project config
│   ├── app/
│   │   ├── routes/     # HTTP endpoints (auctions, bids)
│   │   ├── ws/         # WebSocket manager
│   │   ├── services/   # Auction monitor (background task)
│   │   ├── models.py   # SQLModel definitions
│   │   ├── schemas.py  # Pydantic request/response models
│   │   ├── database.py # Engine & session setup
│   │   └── main.py     # FastAPI entry point + lifespan
│   └── tests/
│       ├── test_auctions.py   # CRUD + validation
│       └── test_concurrency.py # Race condition & anti-snipe
├── web/
│   ├── src/
│   │   ├── components/ # shadcn + custom components
│   │   ├── hooks/      # useAuctionSocket, useIdentity
│   │   └── pages/      # Home, Create, AuctionView
│   └── tests/          # Vitest
├── .env.example
└── README.md
```
