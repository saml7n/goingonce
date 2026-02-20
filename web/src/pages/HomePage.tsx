import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Gavel, Plus, Clock, Trophy } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import type { Auction } from "@/lib/types";
import { apiFetch } from "@/lib/api";

function formatPrice(price: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(price);
}

function timeLeft(endTime: string): string {
  const diff = new Date(endTime).getTime() - Date.now();
  if (diff <= 0) return "Ended";
  const secs = Math.floor(diff / 1000);
  const mins = Math.floor(secs / 60);
  const hrs = Math.floor(mins / 60);
  if (hrs > 0) return `${hrs}h ${mins % 60}m`;
  if (mins > 0) return `${mins}m ${secs % 60}s`;
  return `${secs}s`;
}

function AuctionCard({ auction }: { auction: Auction }) {
  const isActive = auction.status === "active";
  return (
    <Link to={`/auctions/${auction.id}`} className="block">
      <Card className="transition-all hover:shadow-md hover:border-primary/30 cursor-pointer">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">{auction.item_name}</CardTitle>
            <Badge variant={isActive ? "default" : "secondary"}>
              {isActive ? "Live" : "Ended"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-2xl font-bold tabular-nums">
                {formatPrice(auction.current_price)}
              </p>
              {auction.current_bidder_name && (
                <p className="text-sm text-muted-foreground">
                  {isActive ? "Leading: " : "Winner: "}
                  {auction.current_bidder_name}
                </p>
              )}
              {!auction.current_bidder_name && (
                <p className="text-sm text-muted-foreground">No bids yet</p>
              )}
            </div>
            <div className="text-right">
              {isActive ? (
                <div className="flex items-center gap-1 text-sm text-muted-foreground">
                  <Clock className="h-3.5 w-3.5" />
                  <span className="tabular-nums">{timeLeft(auction.end_time)}</span>
                </div>
              ) : (
                <div className="flex items-center gap-1 text-sm text-muted-foreground">
                  <Trophy className="h-3.5 w-3.5" />
                  <span>Completed</span>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

export default function HomePage() {
  const [auctions, setAuctions] = useState<Auction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await apiFetch<Auction[]>("/auctions");
        if (!cancelled) {
          setAuctions(data);
          setLoading(false);
        }
      } catch {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 5000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const active = auctions.filter((a) => a.status === "active");
  const ended = auctions.filter((a) => a.status === "ended");

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b sticky top-0 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-50">
        <div className="container mx-auto flex items-center justify-between px-4 py-3">
          <Link to="/" className="flex items-center gap-2">
            <Gavel className="h-6 w-6 text-primary" />
            <h1 className="text-xl font-bold tracking-tight">GoingOnce</h1>
          </Link>
          <Link to="/create">
            <Button size="sm">
              <Plus className="h-4 w-4 mr-1" />
              New Auction
            </Button>
          </Link>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 max-w-3xl">
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="animate-pulse">
                <CardHeader className="pb-2">
                  <div className="h-5 w-40 bg-muted rounded" />
                </CardHeader>
                <CardContent>
                  <div className="h-8 w-24 bg-muted rounded" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : auctions.length === 0 ? (
          <div className="text-center py-16">
            <Gavel className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold mb-2">No auctions yet</h2>
            <p className="text-muted-foreground mb-4">
              Create the first auction to get started.
            </p>
            <Link to="/create">
              <Button>
                <Plus className="h-4 w-4 mr-1" />
                Create Auction
              </Button>
            </Link>
          </div>
        ) : (
          <>
            {active.length > 0 && (
              <section>
                <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500" />
                  </span>
                  Live Auctions
                </h2>
                <div className="space-y-3">
                  {active.map((a) => (
                    <AuctionCard key={a.id} auction={a} />
                  ))}
                </div>
              </section>
            )}

            {active.length > 0 && ended.length > 0 && (
              <Separator className="my-6" />
            )}

            {ended.length > 0 && (
              <section>
                <h2 className="text-lg font-semibold mb-3 text-muted-foreground">
                  Past Auctions
                </h2>
                <div className="space-y-3">
                  {ended.map((a) => (
                    <AuctionCard key={a.id} auction={a} />
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}
