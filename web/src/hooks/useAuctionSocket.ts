import { useEffect, useRef, useState, useCallback } from "react";
import type { Auction, Bid, WSMessage } from "@/lib/types";
import { WS_BASE } from "@/lib/api";

interface AuctionSocketState {
  auction: Auction | null;
  bids: Bid[];
  connected: boolean;
  serverTimeOffset: number; // ms to add to Date.now() to approximate server time
  lastMessage: WSMessage | null;
}

export function useAuctionSocket(auctionId: string, userId: string) {
  const [state, setState] = useState<AuctionSocketState>({
    auction: null,
    bids: [],
    connected: false,
    serverTimeOffset: 0,
    lastMessage: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const updateServerTimeOffset = useCallback((serverTimeStr: string) => {
    const serverTime = new Date(serverTimeStr).getTime();
    const offset = serverTime - Date.now();
    setState((s) => ({ ...s, serverTimeOffset: offset }));
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    const ws = new WebSocket(
      `${WS_BASE}/auctions/${auctionId}/ws?user_id=${userId}`
    );
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      retriesRef.current = 0;
      setState((s) => ({ ...s, connected: true }));
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      const msg: WSMessage = JSON.parse(event.data);

      // Update server time offset from every message
      if ("server_time" in msg && msg.server_time) {
        updateServerTimeOffset(msg.server_time);
      }

      switch (msg.type) {
        case "state":
          setState((s) => ({
            ...s,
            auction: msg.auction,
            bids: msg.bids,
            lastMessage: msg,
          }));
          break;

        case "new_bid":
          setState((s) => {
            if (!s.auction) return s;
            return {
              ...s,
              auction: {
                ...s.auction,
                current_price: msg.auction.current_price,
                current_bidder_id: msg.auction.current_bidder_id,
                current_bidder_name: msg.auction.current_bidder_name,
                end_time: msg.auction.end_time,
              },
              bids: [msg.bid, ...s.bids],
              lastMessage: msg,
            };
          });
          break;

        case "time_extended":
          setState((s) => {
            if (!s.auction) return s;
            return {
              ...s,
              auction: { ...s.auction, end_time: msg.new_end_time },
              lastMessage: msg,
            };
          });
          break;

        case "auction_ended":
          setState((s) => ({
            ...s,
            auction: msg.auction,
            lastMessage: msg,
          }));
          break;

        case "outbid":
        case "pong":
          setState((s) => ({ ...s, lastMessage: msg }));
          break;
      }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setState((s) => ({ ...s, connected: false }));
      // Exponential backoff reconnect
      const delay = Math.min(1000 * Math.pow(2, retriesRef.current), 10000);
      retriesRef.current++;
      timerRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [auctionId, userId, updateServerTimeOffset]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    // Ping every 30s to keep connection alive
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "ping" }));
      }
    }, 30000);

    return () => {
      mountedRef.current = false;
      clearInterval(pingInterval);
      if (timerRef.current) clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return state;
}
