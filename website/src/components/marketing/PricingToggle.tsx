import { useState, type ReactNode } from "react";

// --- Tier data (PRICE-01, PRICE-02) ---
export interface Tier {
  id: string;
  monthly: number | null;       // null = custom/enterprise
  annualMonthly: number | null;  // monthly-equivalent when billed annually
  features: string[];
  queries: string;               // PRICE-05: approx query count range
  highlighted?: boolean;
}

export const tiers: Tier[] = [
  {
    id: "solo",
    monthly: 99,
    annualMonthly: 89,
    queries: "~150–300/mo",
    features: ["1 seat", "1 jurisdiction", "Source citations", "Confidence scoring", "Query history", "Email support"],
  },
  {
    id: "team",
    monthly: 299,
    annualMonthly: 269,
    queries: "~750–3,000/mo",
    highlighted: true,
    features: ["4 seats", "1 jurisdiction", "Source citations", "Confidence scoring", "Shared workspace", "Client folders", "Templates", "Priority support"],
  },
  {
    id: "firm",
    monthly: 549,
    annualMonthly: 494,
    queries: "~2,000–8,000/mo",
    features: ["15 seats", "2 jurisdictions", "Source citations", "Confidence scoring", "Admin dashboard", "Knowledge base", "Bulk analysis", "Audit trail", "SSO", "Dedicated support"],
  },
  {
    id: "enterprise",
    monthly: null,
    annualMonthly: null,
    queries: "Unlimited",
    features: ["Unlimited seats", "All jurisdictions", "All features", "Custom integrations", "SLA", "Dedicated account manager"],
  },
];

// --- Jurisdiction add-ons (PRICE-03) ---
export const addons = {
  extra: { solo: 29, team: 79, firm: 149 },
  benelux: { solo: 49, team: 129, firm: 249 },
};

// --- Toggle component ---
interface PricingToggleProps {
  monthlyLabel?: string;
  annualLabel?: string;
  annualSave?: string;
  children?: ReactNode;
  onChange?: (isAnnual: boolean) => void;
}

export default function PricingToggle({
  monthlyLabel = "Monthly",
  annualLabel = "Annual",
  annualSave = "Save 10%",
  onChange,
}: PricingToggleProps) {
  const [isAnnual, setIsAnnual] = useState(false);

  function toggle() {
    const next = !isAnnual;
    setIsAnnual(next);
    onChange?.(next);
    window.dispatchEvent(new CustomEvent("billing-toggle", { detail: { isAnnual: next } }));
  }

  return (
    <div className="flex items-center justify-center gap-3">
      <span className={`text-body-sm font-medium ${!isAnnual ? "text-foreground" : "text-muted-foreground"}`}>
        {monthlyLabel}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={isAnnual}
        aria-label={`Switch to ${isAnnual ? "monthly" : "annual"} billing`}
        onClick={toggle}
        className="relative inline-flex h-7 w-12 min-h-[44px] min-w-[44px] items-center rounded-full bg-muted transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      >
        <span
          className={`inline-block h-5 w-5 rounded-full bg-primary transition-transform ${isAnnual ? "translate-x-6" : "translate-x-1"}`}
        />
      </button>
      <span className={`text-body-sm font-medium ${isAnnual ? "text-foreground" : "text-muted-foreground"}`}>
        {annualLabel}
      </span>
      {isAnnual && (
        <span className="rounded-full bg-primary/10 px-2 py-0.5 text-body-xs font-medium text-primary-text">
          {annualSave}
        </span>
      )}
    </div>
  );
}
