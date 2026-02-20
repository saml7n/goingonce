# User Stories: GoingOnce — Real-time Auction PoC

Stories are ordered by dependency. Each one produces a concrete, testable output.

**Rules:**
- No work begins on a story until "Blocked until answered" is cleared.
- One commit per story: `story-<N>: <title>`.
- Mandatory two-tier testing: Unit tests (mocked) + QA verification (real interaction).

---

## Story 1 — Project scaffolding

As a **developer**, I want **a working project skeleton**, so that **I can start building features immediately**.

### Acceptance criteria
- [x] `server/` exists with `uv` init, FastAPI, SQLModel, and a passing `/health` check.
- [x] `web/` exists with Vite + React + Tailwind + shadcn/ui.
- [x] `.env.example` lists all required vars.
- [x] `README.md` has setup instructions.

### Unit tests
- `pytest server/tests/` — 1/1 passed (health endpoint returns 200 OK).

### QA verification
- `curl localhost:8000/health` → `{"status":"ok"}` ✅
- `npx vite build` → builds cleanly (1742 modules, 0 errors) ✅

---

## Story 2 — Auction CRUD

As a **user**, I want **to create and view auctions**, so that **I can start a bidding process**.

### Acceptance criteria
- [ ] `POST /auctions` creates an auction and returns ID.
- [ ] `GET /auctions/:id` returns the auction state.
- [ ] `GET /auctions` lists all auctions.
- [ ] SQLite database is correctly initialized and persisted.

### Unit tests
- Test model validation (prices must be positive).
- Test database insertion and retrieval.

### QA verification
- Create an auction via `curl`, then fetch it by id.

---

## Story 3 — Atomic Bidding & Race Conditions

As a **bidder**, I want **my bids to be processed reliably**, so that **I don't lose an auction due to server errors or race conditions**.

### Acceptance criteria
- [ ] `POST /auctions/:id/bid` validates bid amount > current.
- [ ] Uses `asyncio.Lock` per auction to gate bidding.
- [ ] If bid is in last 30s, `end_time` is extended by 30s (anti-snipe).
- [ ] Returns 400 for low bids, 410 for ended auctions.

### Unit tests
- **Concurrency Test:** Fire 10 concurrent bids to a single auction. Assert exactly one wins each increment.
- **Anti-snipe Test:** Bid at T-5s, assert `end_time` moved +30s.

---

## Story 4 — Real-time WebSockets

As a **user**, I want **the auction view to update in real-time**, so that **I can see new bids and outbid notices without refreshing**.

### Acceptance criteria
- [ ] WebSocket endpoint `ws /auctions/:id/ws` exists.
- [ ] Broadcasts `new_bid`, `time_extended`, and `auction_ended`.
- [ ] Sends targeted `outbid` message to the specific user who was just outbid.
- [ ] Includes `server_time` in every message for client sync.

### Unit tests
- Mock WS connection and verify message receipt after a bid is placed.

### QA verification
- Open two tabs. Bid in one, see update in the other instantly.

---

## Story 5 — Auction Lifecycle & Endings

As a **user**, I want **auctions to end automatically when time runs out**, so that **a winner can be declared**.

### Acceptance criteria
- [ ] Background `asyncio` task starts on server lifespan startup.
- [ ] Polls every 1s for auctions where `status = active AND end_time <= now`.
- [ ] Acquires the per-auction lock before transitioning to `ended` (prevents race with last-second bid).
- [ ] Broadcasts `auction_ended` with final state and winner details.

### Unit tests
- Mock DB with an expired auction; assert monitor calls `ended` transition exactly once.
- Assert no double-end: running the monitor twice on an already-ended auction is a no-op.

### QA verification
- Create a 10s auction. Let it expire. Confirm the browser shows the winner announcement within 2s of expiry.

---

## Story 6 — Frontend: Creator & Listing

As a **user**, I want **a clean UI to create and browse auctions**, so that **the system is easy to use**.

### Acceptance criteria
- [ ] Home page (`/`) lists active auctions (top) and ended auctions (bottom), polling `GET /auctions` every 5s.
- [ ] "Create Auction" form at `/create` with item name, starting price, and duration presets (1m, 5m, 10m + custom).
- [ ] On first visit, UUID is generated and stored in `localStorage`. Display name prompt shown via dialog.
- [ ] On successful create, redirects to `/auctions/:id`.

### Unit tests
- Vitest: `useIdentity` hook returns existing UUID from localStorage on second call.
- Vitest: Create form rejects a starting price of 0 or negative before submit.

### QA verification
- Clear localStorage. Load home page. Confirm name prompt appears. Create an auction. Confirm redirect to live view with correct item name and price.

---

## Story 7 — Frontend: Live Auction Showpiece

As a **bidder**, I want **a high-stakes visual experience**, so that **bidding is exciting and clear**.

### Acceptance criteria
- [ ] `useAuctionSocket` hook manages WebSocket connection with exponential-backoff reconnect.
- [ ] Countdown timer uses `end_time - (Date.now() + serverTimeOffset)`, updated every 100ms via `requestAnimationFrame`.
- [ ] Timer styling: normal → yellow (≤60s) → red pulse (≤30s) → "ENDED".
- [ ] Large animated current bid display (CSS transition on value change).
- [ ] Bid form disabled when auction ended or user is current high bidder.
- [ ] Toast: "You've been outbid! Current: $X" on `outbid` message.
- [ ] Toast: "Time extended! +30s" on `time_extended` message.
- [ ] `canvas-confetti` burst when `auction_ended` and winner ID matches local user UUID.
- [ ] Bid history: scrollable list, most recent first, new entries animate in.

### Unit tests
- Vitest: server time offset calculation is correct given a mocked `server_time` and `Date.now()`.
- Vitest: bid form validation rejects amounts ≤ current price.

### QA verification
- Open two browser tabs with different display names. Bid from one tab, confirm the other shows the new bid and the first tab shows the outbid toast. Let the auction expire and confirm confetti fires for the winner tab.

---

## Story 8 — Polish & README

As a **reviewer**, I want **clear instructions and a polished project**, so that **I can evaluate the technical test easily**.

### Acceptance criteria
- [ ] `README.md` covers: Setup (server + web), Architecture summary, Key decisions & tradeoffs, and "What I'd improve with more time".
- [ ] Responsive layout (works on mobile viewport).
- [ ] WebSocket disconnect shows a "Reconnecting..." indicator; connection restored silently.
- [ ] All API error responses surface meaningful messages in the UI (not just console errors).
- [ ] Loading skeleton shown while initial auction state is fetching.

### Unit tests
- None (polish/docs story).

### QA verification
- Follow README from a clean environment. Confirm server and web start with documented commands alone.
- Kill the server while a live auction is open. Confirm "Reconnecting..." UI appears. Restart server. Confirm UI recovers without a page refresh.
