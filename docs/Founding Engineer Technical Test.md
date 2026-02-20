### Real-time Auction System

**Time:** 60 minutes
**Stack:** Your choice (any language/framework)
**AI:** You may use AI assistants (ChatGPT, Copilot, Claude, etc.)

#### Background

Build a real-time auction system where users can create auctions and place bids. The system must handle the complexities of real-time bidding including race conditions, time synchronization, and anti-sniping protection.

#### Requirements

**API Endpoints:**

1. `POST /auctions` - Create a new auction

    - Accepts: item name, starting price, duration (in seconds)
    - Returns: auction ID, end time

2. `POST /auctions/:id/bid` - Place a bid

    - Accepts: bid amount, bidder identifier
    - Validates: bid must be higher than current highest, auction must be active
    - Returns: success/failure with current state

3. `GET /auctions/:id` - Get auction state
    - Returns: item, current bid, high bidder, end time, bid history, status (active/ended)

**Real-time Requirements:**

-   Broadcast bid updates to all connected clients
-   Notify users when they've been outbid
-   Broadcast when auction ends with winner information

**Anti-sniping Rule:**

-   If a bid is placed within the last 30 seconds, extend the auction by 30 seconds
-   This prevents last-second sniping and ensures fair bidding

**Frontend:**

1. **Create Auction Form**

    - Item name, starting price, duration inputs
    - Display created auction link/ID

2. **Live Auction View**
    - Item name and description
    - Current highest bid (updates in real-time)
    - Countdown timer synchronized with server time
    - Bid input with validation feedback
    - "You've been outbid!" notification
    - Bid history (most recent first)
    - Winner announcement when auction ends

#### Deliverables

1. Working backend API
2. Working frontend UI
3. README with:
    - Setup instructions
    - Any assumptions or tradeoffs you made
    - What you'd improve with more time

#### Evaluation Criteria

-   Correctness of bid validation and auction lifecycle
-   Handling of race conditions and edge cases
-   Real-time synchronization approach
-   Code organization and quality
-   UX decisions under time pressure
