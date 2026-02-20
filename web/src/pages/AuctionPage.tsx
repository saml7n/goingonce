import { useState, useEffect, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { Gavel, ArrowLeft, Send, Wifi, WifiOff } from "lucide-react";
import confetti from "canvas-confetti";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";

import { useAuctionSocket } from "@/hooks/useAuctionSocket";
import { useCountdown } from "@/hooks/useCountdown";
import { useIdentity } from "@/hooks/useIdentity";
import { apiFetch } from "@/lib/api";
import type { BidResult, WSMessage } from "@/lib/types";

function formatPrice(price: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(price);
}

function formatTime(seconds: number): string {
  if (seconds <= 0) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function timerColor(seconds: number): string {
  if (seconds <= 30) return "text-red-500";
  if (seconds <= 60) return "text-yellow-500";
  return "text-foreground";
}

export default function AuctionPage() {
  const { id } = useParams<{ id: string }>();
  const { userId, userName } = useIdentity();
  const { auction, bids, connected, serverTimeOffset, lastMessage } =
    useAuctionSocket(id!, userId);
  const remaining = useCountdown(auction?.end_time ?? null, serverTimeOffset);
  const [bidAmount, setBidAmount] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const prevMessageRef = useRef<WSMessage | null>(null);
  const confettiFiredRef = useRef(false);

  const isEnded = auction?.status === "ended" || (auction?.status === "active" && remaining <= 0);
  const isHighBidder = auction?.current_bidder_id === userId;
  const minBid = auction ? auction.current_price + 0.01 : 0;

  // Client-side auction ending detection (fires confetti/toast when countdown hits 0)
  const prevRemainingRef = useRef<number | null>(null);
  useEffect(() => {
    if (!auction || auction.status === "ended") return;
    const prev = prevRemainingRef.current;
    prevRemainingRef.current = remaining;

    // Detect transition from >0 to 0
    if (prev !== null && prev > 0 && remaining <= 0 && !confettiFiredRef.current) {
      if (isHighBidder) {
        confettiFiredRef.current = true;
        confetti({
          particleCount: 150,
          spread: 80,
          origin: { y: 0.6 },
        });
        toast.success("🎉 You won the auction!", { duration: 8000 });
      } else if (auction.current_bidder_name) {
        toast(`Auction ended — ${auction.current_bidder_name} wins!`, { duration: 5000 });
      } else {
        toast("Auction ended with no bids", { duration: 5000 });
      }
    }
  }, [remaining, auction, isHighBidder]);

  // React to incoming WS messages for toasts & confetti
  useEffect(() => {
    if (!lastMessage || lastMessage === prevMessageRef.current) return;
    prevMessageRef.current = lastMessage;

    if (lastMessage.type === "outbid") {
      toast.warning(
        `You've been outbid by ${lastMessage.by}! Current: ${formatPrice(lastMessage.new_price)}`,
        { duration: 5000 }
      );
    }

    if (lastMessage.type === "time_extended") {
      toast.info("Time extended! +30s", { duration: 3000 });
    }

    if (lastMessage.type === "auction_ended") {
      if (lastMessage.winner_id === userId && !confettiFiredRef.current) {
        confettiFiredRef.current = true;
        confetti({
          particleCount: 150,
          spread: 80,
          origin: { y: 0.6 },
        });
        toast.success("🎉 You won the auction!", { duration: 8000 });
      } else if (lastMessage.winner_id && lastMessage.winner_id !== userId) {
        toast(`Auction ended — ${lastMessage.winner_name} wins!`, { duration: 5000 });
      } else {
        toast("Auction ended with no bids", { duration: 5000 });
      }
    }
  }, [lastMessage, userId]);

  const handleBid = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(bidAmount);
    if (isNaN(amount) || amount < minBid) {
      toast.error(`Bid must be at least ${formatPrice(minBid)}`);
      return;
    }
    setSubmitting(true);
    try {
      const result = await apiFetch<BidResult>(`/auctions/${id}/bid`, {
        method: "POST",
        body: JSON.stringify({
          amount,
          bidder_id: userId,
          bidder_name: userName,
        }),
      });
      if (result.success) {
        toast.success(result.message);
        setBidAmount("");
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Bid failed");
    } finally {
      setSubmitting(false);
    }
  };

  // Loading state
  if (!auction) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="container mx-auto px-4 py-6 max-w-2xl">
          <div className="space-y-4">
            <Card className="animate-pulse">
              <CardHeader>
                <div className="h-7 w-48 bg-muted rounded" />
              </CardHeader>
              <CardContent>
                <div className="h-16 w-32 bg-muted rounded mb-4" />
                <div className="h-4 w-64 bg-muted rounded" />
              </CardContent>
            </Card>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Header connected={connected} />

      <main className="container mx-auto px-4 py-6 max-w-2xl">
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          All auctions
        </Link>

        {/* Auction Info */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xl">{auction.item_name}</CardTitle>
              <Badge variant={isEnded ? "secondary" : "default"}>
                {isEnded ? "Ended" : "Live"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            {/* Timer */}
            <div className="text-center mb-4">
              {isEnded ? (
                <p className="text-3xl font-bold text-muted-foreground">ENDED</p>
              ) : (
                <p
                  className={`text-5xl font-bold tabular-nums transition-colors ${timerColor(remaining)} ${
                    remaining <= 30 ? "animate-pulse" : ""
                  }`}
                >
                  {formatTime(remaining)}
                </p>
              )}
            </div>

            {/* Current Price */}
            <div className="text-center mb-4">
              <p className="text-sm text-muted-foreground uppercase tracking-wide">
                {isEnded ? "Final Price" : "Current Bid"}
              </p>
              <p className="text-4xl font-bold tabular-nums transition-all duration-300">
                {formatPrice(auction.current_price)}
              </p>
              {auction.current_bidder_name && (
                <p className="text-sm text-muted-foreground mt-1">
                  {isEnded ? "Winner: " : "Leading: "}
                  <span className="font-medium">
                    {auction.current_bidder_name}
                    {isHighBidder && " (you)"}
                  </span>
                </p>
              )}
              {!auction.current_bidder_name && (
                <p className="text-sm text-muted-foreground mt-1">No bids yet</p>
              )}
            </div>

            {/* Bid Form */}
            {!isEnded && (
              <form onSubmit={handleBid} className="flex gap-2">
                <div className="flex-1 relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">
                    $
                  </span>
                  <Input
                    type="number"
                    step="0.01"
                    min={minBid}
                    placeholder={minBid.toFixed(2)}
                    value={bidAmount}
                    onChange={(e) => setBidAmount(e.target.value)}
                    className="pl-7 tabular-nums"
                    disabled={submitting || isHighBidder}
                  />
                </div>
                <Button
                  type="submit"
                  disabled={submitting || isHighBidder}
                  title={isHighBidder ? "You're already the highest bidder" : undefined}
                >
                  <Send className="h-4 w-4 mr-1" />
                  {submitting ? "..." : "Bid"}
                </Button>
              </form>
            )}
            {!isEnded && isHighBidder && (
              <p className="text-sm text-center text-green-600 mt-2 font-medium">
                You're the highest bidder!
              </p>
            )}
          </CardContent>
        </Card>

        {/* Bid History */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">
              Bid History ({bids.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {bids.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                No bids yet. Be the first!
              </p>
            ) : (
              <ScrollArea className="h-64">
                <div className="space-y-1">
                  {bids.map((bid, i) => (
                    <div
                      key={bid.id}
                      className={`flex items-center justify-between py-2 px-2 rounded text-sm ${
                        i === 0 ? "bg-primary/5 animate-in fade-in slide-in-from-top-1 duration-300" : ""
                      }`}
                    >
                      <div>
                        <span className="font-medium">{bid.bidder_name}</span>
                        {bid.bidder_id === userId && (
                          <span className="text-xs text-muted-foreground ml-1">(you)</span>
                        )}
                      </div>
                      <span className="font-mono font-medium tabular-nums">
                        {formatPrice(bid.amount)}
                      </span>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

function Header({ connected }: { connected?: boolean }) {
  return (
    <header className="border-b sticky top-0 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-50">
      <div className="container mx-auto flex items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2">
          <Gavel className="h-6 w-6 text-primary" />
          <h1 className="text-xl font-bold tracking-tight">GoingOnce</h1>
        </Link>
        {connected !== undefined && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            {connected ? (
              <>
                <Wifi className="h-3.5 w-3.5 text-green-500" />
                <span>Live</span>
              </>
            ) : (
              <>
                <WifiOff className="h-3.5 w-3.5 text-red-500" />
                <span>Reconnecting...</span>
              </>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
