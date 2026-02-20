# Agent Operating Instructions (GoingOnce)

These instructions apply to any coding agent working in this repository.

## Project context

GoingOnce is a real-time auction system PoC. The architecture is documented in `docs/architecture.md`. Read it for system design context, tech stack decisions, and race condition strategies.

**Tech stack (server):** Python 3.12+, FastAPI, asyncio, SQLModel (SQLite), aiosqlite.
**Tech stack (web):** React, TypeScript, Vite, Tailwind v4, shadcn/ui.
**Key Features:** `asyncio.Lock` for atomic bidding, server-authoritative time sync via WebSockets, anti-sniping protection, confetti celebrations.

## Non-negotiables

1. **Story-gated work only**
   - Before making any code change, read the relevant story in `docs/stories.md`.
   - You must identify the active story (e.g., "Story 1 — Project scaffolding").
   - You must confirm that all "Blocked until answered" items are cleared.
   - Do not skip ahead. Respect the dependency chain.

2. **One story at a time**
   - Do not begin a new story until the current one meets acceptance criteria, passes tests, and is committed.

3. **Two-tier testing is mandatory**
   - **Unit tests** (`pytest` for server, `vitest` for web): isolated, fast.
   - **QA verification**: real runs of the system (manual or Playwright).
   - **Concurrency tests** are required for Story 3 (Atomic Bidding).

4. **One commit per story**
   - Commit message format: `story-<N>: <short title>`.
   - The commit must include code, tests, and updated story docs.

5. **Update story progress**
   - Mark stories as done (`- [x]`) and record test results in `docs/stories.md` after completion.

## Coding style

### Python (server)
- **Package manager: `uv`**.
- **Atomic Bidding:** Always use the per-auction `asyncio.Lock` pattern for the read-validate-write-broadcast cycle.
- **Async everywhere:** `async def` for I/O.
- **Typing:** Strict Pydantic/SQLModel typing.

### Web (client)
- **Time Sync:** Use the server-provided offset for all countdown calculations.
- **State Management:** Keep it lightweight (React `useState`, custom hooks for WS).
- **UX:** Use shadcn/ui for components and `lucide-react` for icons. Add "flare" with animations and `canvas-confetti`.
