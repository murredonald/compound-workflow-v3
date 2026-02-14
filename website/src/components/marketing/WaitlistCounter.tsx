import { useState, useEffect } from "react";

interface WaitlistCounterProps {
  text?: string; // e.g. "{count} tax professionals on the waitlist"
}

export default function WaitlistCounter({
  text = "{count} tax professionals on the waitlist",
}: WaitlistCounterProps) {
  const [count, setCount] = useState<number | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchCount() {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 10000);
        const res = await fetch("/api/counter", { signal: controller.signal });
        clearTimeout(timeout);
        const data = await res.json();
        if (!cancelled && typeof data.count === "number") {
          setCount(data.count);
        }
      } catch {
        // Graceful fallback — hide counter on failure
      }
    }

    fetchCount();

    // Listen for custom event from WaitlistForm success
    function handleRefresh() {
      fetchCount();
    }
    window.addEventListener("waitlist-refresh", handleRefresh);

    return () => {
      cancelled = true;
      window.removeEventListener("waitlist-refresh", handleRefresh);
    };
  }, []);

  // Animate count-up on load (FRONT-13)
  useEffect(() => {
    if (count !== null) {
      setVisible(true);
    }
  }, [count]);

  // Hide entirely if no count (API failed or loading)
  if (count === null || !visible) return null;

  const displayText = text.replace("{count}", count.toLocaleString());

  return (
    <p className="text-body-sm text-muted-foreground transition-opacity duration-500">
      {displayText}
    </p>
  );
}
