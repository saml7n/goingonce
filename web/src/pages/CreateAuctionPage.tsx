import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Gavel, ArrowLeft } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { useIdentity } from "@/hooks/useIdentity";

const DURATION_PRESETS = [
  { label: "1 min", seconds: 60 },
  { label: "5 min", seconds: 300 },
  { label: "10 min", seconds: 600 },
];

export default function CreateAuctionPage() {
  const navigate = useNavigate();
  const { userName } = useIdentity();
  const [itemName, setItemName] = useState("");
  const [startingPrice, setStartingPrice] = useState("");
  const [duration, setDuration] = useState(60);
  const [customDuration, setCustomDuration] = useState("");
  const [isCustom, setIsCustom] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const effectiveDuration = isCustom ? parseInt(customDuration) || 0 : duration;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const price = parseFloat(startingPrice);
    if (!itemName.trim()) {
      toast.error("Item name is required");
      return;
    }
    if (isNaN(price) || price <= 0) {
      toast.error("Starting price must be greater than $0");
      return;
    }
    if (effectiveDuration <= 0) {
      toast.error("Duration must be positive");
      return;
    }

    setSubmitting(true);
    try {
      const result = await apiFetch<{ id: string }>("/auctions", {
        method: "POST",
        body: JSON.stringify({
          item_name: itemName.trim(),
          starting_price: price,
          duration_seconds: effectiveDuration,
        }),
      });
      toast.success("Auction created!");
      navigate(`/auctions/${result.id}`);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to create auction");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b sticky top-0 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-50">
        <div className="container mx-auto flex items-center gap-2 px-4 py-3">
          <Link to="/" className="flex items-center gap-2">
            <Gavel className="h-6 w-6 text-primary" />
            <h1 className="text-xl font-bold tracking-tight">GoingOnce</h1>
          </Link>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 max-w-lg">
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to auctions
        </Link>

        <Card>
          <CardHeader>
            <CardTitle>Create Auction</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="item-name">Item Name</Label>
                <Input
                  id="item-name"
                  placeholder="e.g. Vintage Watch"
                  value={itemName}
                  onChange={(e) => setItemName(e.target.value)}
                  maxLength={200}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="starting-price">Starting Price ($)</Label>
                <Input
                  id="starting-price"
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder="10.00"
                  value={startingPrice}
                  onChange={(e) => setStartingPrice(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label>Duration</Label>
                <div className="flex flex-wrap gap-2">
                  {DURATION_PRESETS.map(({ label, seconds }) => (
                    <Button
                      key={seconds}
                      type="button"
                      size="sm"
                      variant={!isCustom && duration === seconds ? "default" : "outline"}
                      onClick={() => {
                        setDuration(seconds);
                        setIsCustom(false);
                      }}
                    >
                      {label}
                    </Button>
                  ))}
                  <Button
                    type="button"
                    size="sm"
                    variant={isCustom ? "default" : "outline"}
                    onClick={() => setIsCustom(true)}
                  >
                    Custom
                  </Button>
                </div>
                {isCustom && (
                  <div className="flex items-center gap-2 mt-2">
                    <Input
                      type="number"
                      min="1"
                      placeholder="Seconds"
                      value={customDuration}
                      onChange={(e) => setCustomDuration(e.target.value)}
                      className="w-32"
                    />
                    <span className="text-sm text-muted-foreground">seconds</span>
                  </div>
                )}
              </div>

              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Creating..." : "Create Auction"}
              </Button>

              {userName && (
                <p className="text-xs text-center text-muted-foreground">
                  Creating as <span className="font-medium">{userName}</span>
                </p>
              )}
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
