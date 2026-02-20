import { useState, useEffect, useRef, useCallback } from "react";

/**
 * Countdown hook using server-authoritative end_time.
 * Returns remaining seconds, updated ~10x/s via requestAnimationFrame.
 */
export function useCountdown(endTimeISO: string | null, serverTimeOffset: number) {
  const [remaining, setRemaining] = useState<number>(0);
  const rafRef = useRef<number>(0);

  const tick = useCallback(() => {
    if (!endTimeISO) {
      setRemaining(0);
      return;
    }
    const endMs = new Date(endTimeISO).getTime();
    const serverNow = Date.now() + serverTimeOffset;
    const left = Math.max(0, (endMs - serverNow) / 1000);
    setRemaining(left);

    if (left > 0) {
      rafRef.current = requestAnimationFrame(tick);
    }
  }, [endTimeISO, serverTimeOffset]);

  useEffect(() => {
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [tick]);

  return remaining;
}
