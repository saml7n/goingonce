# GoingOnce — Real-time Auction System

A high-performance real-time auction system with anti-sniping protection, server-authoritative time sync, and race-condition-safe bidding.

## Quick Start

### Prerequisites
- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- npm

### Server

```bash
cd server
cp ../.env.example .env   # adjust if needed
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### Web

```bash
cd web
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## Architecture

See [docs/architecture.md](docs/architecture.md) for full details.

- **Backend:** FastAPI + SQLite (via SQLModel/aiosqlite) + WebSockets
- **Frontend:** React + Vite + Tailwind v4 + shadcn/ui
- **Concurrency:** Per-auction `asyncio.Lock` for atomic bid validation
- **Time sync:** Server-authoritative timestamps on every WebSocket message
- **Anti-sniping:** Bids in the last 30s extend `end_time` by 30s

## Key Decisions & Tradeoffs

| Decision | Rationale |
|---|---|
| SQLite over Postgres | Zero-config; single-writer model pairs perfectly with asyncio.Lock |
| asyncio.Lock over DB-level locking | Simpler, provably correct for single-process PoC |
| Server time on every WS message | Resilient to clock drift and sleep/wake cycles |
| UUID + display name (no auth) | Minimal friction for a PoC |
| canvas-confetti for wins | Low-effort, high-impact visual flair |

## What I'd Improve With More Time

- PostgreSQL + `SELECT FOR UPDATE` for multi-process deployments
- JWT authentication with proper user accounts
- Minimum bid increment rules (e.g., $1 or 5% of current)
- Image upload for auction items
- Pagination on auction listing and bid history
- Rate limiting on bid endpoint
- E2E tests with Playwright
- Deploy to a cloud provider with CI/CD
