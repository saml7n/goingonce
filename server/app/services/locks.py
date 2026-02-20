import asyncio


class AuctionLockManager:
    """Per-auction asyncio.Lock manager.

    Provides a unique lock per auction ID so that bid validation and writes
    are serialized per-auction without blocking other auctions.
    """

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}

    def get(self, auction_id: str) -> asyncio.Lock:
        if auction_id not in self._locks:
            self._locks[auction_id] = asyncio.Lock()
        return self._locks[auction_id]

    def remove(self, auction_id: str) -> None:
        """Clean up lock for ended auctions."""
        self._locks.pop(auction_id, None)


# Singleton — shared across the entire server process
auction_locks = AuctionLockManager()
