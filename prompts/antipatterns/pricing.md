# Pricing — Common Mistakes & Anti-Patterns

Common mistakes when running the pricing specialist. Each pattern
describes a failure mode that leads to poor pricing decisions.

**Referenced by:** `specialist_pricing.md`
> These patterns are **illustrative, not exhaustive**. They are a starting
> point — identify additional project-specific anti-patterns as you work.
> When a listed pattern doesn't apply to the current project, skip it.

---

## A. Model Design

### PRICE-AP-01: Copying Competitor Pricing
**Mistake:** Matches competitor price points without understanding their cost structure, market position, or unit economics. Their $29/mo might be subsidized by $200M in VC funding burning through runway to acquire market share.
**Why:** Competitor pricing is the most visible data point in competitive analysis, and the model anchors on it. Training data is full of "competitive pricing analysis" frameworks that recommend positioning relative to competitors. But competitor prices reflect THEIR costs, THEIR strategy, and THEIR investor patience — none of which transfer to your product.
**Example:**
```
PRICE-01: Pricing Strategy
Competitor analysis shows:
- Acme: $49/mo starter, $99/mo pro
- BookEasy: $39/mo starter, $79/mo pro
Recommendation: Price at $35/mo starter, $69/mo pro to undercut
both competitors and win on price.
```
**Instead:** Calculate pricing from your own fundamentals: (1) Cost floor — what does it cost to serve one user? (infrastructure, support, payment processing). (2) Value ceiling — what is the user's willingness to pay based on the value delivered? (time saved, revenue generated, cost avoided). (3) Competitive context — where do competitors sit between floor and ceiling? Price based on YOUR floor-to-ceiling range, not theirs. "Our cost to serve: $8/user/month. Value delivered (estimated 5 hours saved/month at $50/hr): $250/month. Price capture at 15% of value: $37/month. This happens to be near BookEasy — coincidental, not derived from their pricing."

### PRICE-AP-02: Cost-Plus Pricing
**Mistake:** Calculates infrastructure cost and adds a margin. This ignores that users pay for VALUE delivered, not for your server bills. A tool that saves someone $10,000/month can charge $500/month even if it costs $2/month to run.
**Why:** Cost-plus is the simplest pricing model and the one most commonly taught in training data. It feels "fair" and is easy to justify. The model defaults to it because it requires only cost data (which it can estimate) rather than value data (which requires user research it doesn't have). But cost-plus leaves enormous value on the table for high-value products and makes low-value products unprofitable.
**Example:**
```
PRICE-02: Cost Analysis
Infrastructure cost per user: $3.50/month
Support cost per user: $1.50/month
Total cost: $5.00/month
Target margin: 70%
Recommended price: $16.67/month → round to $17/month
```
**Instead:** Price from value, not cost. Interview target users: "How much time does manual scheduling cost you per week?" If a solo therapist spends 5 hours/week on scheduling at an effective rate of $150/hour, that's $750/week or $3,000/month in lost billable time. Even recovering 50% of that time, the tool delivers $1,500/month in value. Pricing at $49/month captures 3.3% of value created — easily justifiable. The $5/month cost becomes your margin floor, not your pricing input. "Price: $49/month. Cost: $5/month. Gross margin: 90%. Value capture: 3.3%."

### PRICE-AP-03: Too Many Tiers
**Mistake:** Creates 5+ pricing tiers with overlapping features and confusing boundaries. Users experience choice paralysis and default to the cheapest option or leave entirely.
**Why:** The model generates tiers by feature-gating, and with many features, it creates many tiers. Each feature feels like it deserves its own tier boundary. Training data includes enterprise pricing pages with 4-5 tiers, which the model replicates even for products that don't need that granularity. More tiers feel more "comprehensive" to the model, but they increase cognitive load for buyers.
**Example:**
```
PRICE-03: Pricing Tiers
1. Free — 5 appointments/month
2. Starter — $19/mo, 50 appointments
3. Basic — $29/mo, 150 appointments
4. Pro — $49/mo, 500 appointments
5. Business — $99/mo, unlimited appointments
6. Enterprise — custom pricing
```
**Instead:** Use 3 tiers maximum, each targeting a distinct user persona with distinct needs: "(1) Solo — $29/mo: unlimited appointments, 1 calendar, email reminders. Target: individual practitioners. (2) Team — $79/mo: everything in Solo + 5 calendars, team scheduling, SMS reminders. Target: small practices (2-10 people). (3) Enterprise — custom: everything in Team + SSO, audit logs, API access, dedicated support. Target: organizations (50+ people)." Each tier serves a different buyer with different purchasing authority and different needs — not the same buyer at different volumes.

### PRICE-AP-04: Feature-Gating Wrong Things
**Mistake:** Gates features by novelty or development cost instead of by customer value and growth signal. The feature that makes users successful should be accessible; the feature that signals a user is scaling should be gated.
**Why:** The model treats expensive-to-build features as premium and simple features as free, which is backwards. It gates "AI scheduling" (novel, expensive to build) behind the top tier, even if AI scheduling is the reason users sign up. Meanwhile, it gives away "team management" for free even though needing team features signals the user has grown beyond solo use — the natural upgrade trigger.
**Example:**
```
PRICE-04: Feature Gating
Free: basic scheduling, 1 calendar
Starter: email reminders, calendar sync
Pro: AI scheduling, SMS reminders, reporting
Enterprise: team management, API, SSO
```
**Instead:** Gate features by growth signal, not by build cost: "Solo ($29): full scheduling + AI optimization + email reminders + reporting. These are WHY users choose us — don't gate the core value. Team ($79): everything in Solo + multiple calendars + team view + SMS reminders. Gate trigger: the user added a second staff member — clear signal they've outgrown Solo. Enterprise (custom): everything in Team + SSO + API + audit logs. Gate trigger: IT department requires SSO before procurement approves." The AI feature is the product's differentiator — putting it in the top tier means 80% of users never experience it.

### PRICE-AP-05: Free Tier Without Conversion Strategy
**Mistake:** Offers a permanent free tier because competitors do, without modeling the conversion funnel. If only 2% convert to paid, you need to serve 50 free users to support 1 paying user — can you afford that?
**Why:** Free tiers are prominently featured in SaaS pricing literature and competitor pricing pages. The model pattern-matches "SaaS" to "freemium" without analyzing whether freemium works for this specific business model. PLG (Product-Led Growth) requires specific conditions: low marginal cost per user, viral/network effects that free users drive, and a natural in-product trigger for upgrading. Without these, a free tier is just a cost center.
**Example:**
```
PRICE-05: Free Tier
Offer a permanent free tier with 10 appointments/month to drive adoption.
Users who need more will naturally upgrade to the paid plan.
```
**Instead:** Model the funnel before committing: "Free tier cost: $2/user/month (email, compute, support overhead). Industry conversion rate for scheduling tools: 3-5%. At $49/month paid tier, each paying user subsidizes 24-49 free users at a cost of $48-98/month — nearly wiping out the paying user's revenue. Alternative approaches: (1) 14-day free trial (no permanent free tier) — user experiences full product, converts or leaves. Cost: ~$1 per trial user, no ongoing burden. (2) Freemium with viral hook — free users get a branded booking page that promotes us to THEIR clients, driving organic acquisition. Only viable if booking page generates measurable referrals. (3) Time-limited free tier — free for 6 months, then converts to paid. Reduces long-tail free user costs." Choose based on which model's economics actually work.

---

## B. Economics

### PRICE-AP-06: LTV:CAC Without Context
**Mistake:** Cites "3:1 LTV:CAC ratio" as a universal benchmark for pricing viability. This ratio varies dramatically by business model, sales cycle, and market — B2B enterprise, B2B SMB, B2C consumer, and marketplace businesses all have different healthy ratios.
**Why:** The "3:1 LTV:CAC" rule is one of the most frequently repeated SaaS metrics in training data. Blog posts, VC frameworks, and startup playbooks cite it as a universal standard. The model has absorbed this as a hard rule rather than a context-dependent guideline. In reality, B2C apps may need 5:1+ (high churn), while enterprise deals can tolerate 2:1 (long contracts, low churn).
**Example:**
```
PRICE-06: Unit Economics Validation
Projected LTV: $588 (12 months × $49/month)
Projected CAC: $150 (ad spend + onboarding cost)
LTV:CAC ratio: 3.9:1 ✅ Exceeds the 3:1 benchmark

Pricing is validated.
```
**Instead:** Contextualize the ratio for your specific model: "LTV: $588 assumes 12-month retention, but our category average is 8 months (source: OpenView SaaS benchmarks for SMB scheduling). Adjusted LTV: $392. CAC: $150 assumes 100% self-serve onboarding. If 30% of signups need a support call ($25 each), effective CAC: $157.50. Adjusted LTV:CAC: 2.5:1. For SMB SaaS with monthly contracts and no switching costs, the benchmark is 4:1+ (Bessemer Cloud Index). We're below target. Options: (1) increase retention (reduce churn from 12% to 8% monthly → LTV jumps to $612). (2) reduce CAC (improve onboarding to reduce support calls). (3) increase ARPU (upsell SMS add-on at $10/month)."

### PRICE-AP-07: Ignoring Churn in Projections
**Mistake:** Revenue projections assume all users stay. Monthly churn of 5% means losing half your user base in a year. Without modeling churn, revenue projections are fiction.
**Why:** Revenue projections in training data often use simple multiplication (users x price x months) without churn modeling. Churn is a compounding negative that's hard to intuit — 5% monthly churn sounds small but compounds to 46% annual attrition. The model generates optimistic projections because they're mathematically simpler and more common in pitch deck examples.
**Example:**
```
PRICE-07: Revenue Projections (Year 1)
Month 1: 100 users × $49 = $4,900
Month 6: 500 users × $49 = $24,500
Month 12: 1,000 users × $49 = $49,000
Annual revenue: $324,000
```
**Instead:** Model with explicit churn: "Assuming 50 new users/month and 7% monthly churn (industry average for SMB SaaS): Month 1: 50 users, $2,450 MRR. Month 6: 50 new + ~197 retained = 247 active users, $12,103 MRR. Month 12: 50 new + ~309 retained = 359 active users, $17,591 MRR. Annual revenue: $142,800 (not $324,000). The 1,000-user projection assumed zero churn — actual active users at month 12 are 359. To reach 1,000 active users at 7% churn, you need either 142 new users/month OR to reduce churn to 3%." Always present optimistic (3% churn), expected (7%), and pessimistic (12%) scenarios.

### PRICE-AP-08: Annual Pricing Without Incentive
**Mistake:** Offers annual billing at the same monthly rate, or with such a small discount that it doesn't motivate users to commit. Annual plans need a meaningful discount to incentivize prepayment and reduce churn.
**Why:** The model mentions annual billing as a feature ("we'll offer monthly and annual plans") without designing the incentive structure. In training data, pricing pages show annual plans but the strategic reasoning (cash flow, churn reduction, commitment effect) is rarely discussed. The model treats annual billing as a billing option rather than a retention and revenue strategy.
**Example:**
```
PRICE-08: Billing Options
Monthly: $49/month
Annual: $49/month (billed annually at $588)
```
**Instead:** Design annual pricing as a strategic instrument: "Monthly: $49/month ($588/year). Annual: $39/month billed at $468/year (20% discount). Annual pricing justification: (1) Cash flow: $468 upfront vs. $49 x average 8 months retention = $392 — annual users actually pay MORE even with the discount. (2) Churn reduction: annual users churn at 30% the rate of monthly users (they've committed). (3) Revenue predictability: annual contracts make revenue forecasting reliable. Display as: '$39/mo billed annually — save $120/year' to anchor on the savings. Show monthly as '$49/mo billed monthly' — the higher number makes annual feel like a deal."

### PRICE-AP-09: No Unit Economics Per Tier
**Mistake:** Defines pricing tiers without calculating the cost to serve each tier. Cannot answer "how much does it cost to serve a Free user vs. a Pro user?" Without this, pricing is guesswork — you might be losing money on your most popular tier.
**Why:** The model designs tiers from the customer-facing side (features and prices) without calculating the cost-of-service side. Tier economics require infrastructure cost modeling (compute, storage, email sends, API calls) that the model doesn't naturally perform. In training data, pricing discussions focus on revenue, not margin per tier.
**Example:**
```
PRICE-09: Tier Economics
Solo: $29/mo — healthy margin ✅
Team: $79/mo — healthy margin ✅
Enterprise: Custom — healthy margin ✅
```
**Instead:** Calculate cost-to-serve per tier with specific line items: "Solo ($29/mo): compute $0.50, storage $0.20, email (est. 50 reminders/mo) $0.25, payment processing (2.9% + $0.30) $1.14, support (0.1 tickets/mo × $15/ticket) $1.50. Total cost: $3.59. Gross margin: 87.6%. Team ($79/mo): compute $2.00 (5x users), storage $1.00, email $1.25, SMS (est. 100 messages/mo) $4.00, payment processing $2.59, support (0.5 tickets/mo) $7.50. Total cost: $18.34. Gross margin: 76.8%. Flag: SMS costs scale linearly with appointment volume. A heavy Team user (500 SMS/month) costs $20 in SMS alone — monitor and cap if needed."

---

## C. Implementation

### PRICE-AP-10: Billing Integration as Afterthought
**Mistake:** Plans pricing tiers and feature gates without considering payment provider capabilities, webhook handling, subscription lifecycle management, and edge cases like failed payments, plan changes, and refunds.
**Why:** The model treats pricing as a business decision and billing as an implementation detail. In training data, pricing strategy and billing implementation are discussed in separate contexts — strategy articles don't mention Stripe webhook event types, and Stripe docs don't discuss pricing strategy. The model maintains this separation, but the implementation constraints should inform the pricing design.
**Example:**
```
PRICE-10: Billing
We'll integrate Stripe for payment processing.
Monthly and annual billing will be available.
Users can upgrade or downgrade at any time.
```
**Instead:** Design pricing with billing mechanics in mind: "Stripe integration requirements: (1) Products: 2 products (Solo, Team), each with 2 prices (monthly, annual). (2) Subscription lifecycle: `customer.subscription.created` → provision features. `customer.subscription.updated` → handle plan changes (upgrade: immediate with prorated charge; downgrade: at period end to avoid refund complexity). `invoice.payment_failed` → 3 retry attempts over 7 days, then `customer.subscription.deleted` → revoke access, retain data 30 days. (3) Proration: Stripe calculates automatically for upgrades. For downgrades, we wait until period end (simpler billing, no refunds). (4) Tax: Stripe Tax for automatic VAT/sales tax calculation — required for EU sales from day 1. (5) Trial: 14-day trial via Stripe `trial_period_days` — no card required (reduces signup friction, lower conversion but higher volume)."

### PRICE-AP-11: No Upgrade/Downgrade Path
**Mistake:** Defines tiers but not what happens when users switch between them. Proration, feature access during transitions, data handling on downgrade, and timing of changes are all business rules that must be decided during pricing design, not discovered during implementation.
**Why:** Tier definitions in training data are static snapshots — "Free gets X, Pro gets Y." The dynamic transitions between tiers (upgrade, downgrade, cancellation) are implementation details that pricing articles skip. The model follows this pattern, producing a pricing table without lifecycle rules. But these rules affect user experience, revenue recognition, and engineering complexity.
**Example:**
```
PRICE-11: Plan Changes
Users can upgrade or downgrade their plan at any time through
the billing settings page.
```
**Instead:** Define explicit transition rules for every path: "Solo → Team upgrade: immediate. User charged prorated amount for remainder of billing period. Team features (extra calendars, SMS) available immediately. Existing data preserved. Team → Solo downgrade: effective at end of current billing period. User retains Team features until period ends. At transition: if >1 calendar exists, prompt user to select primary calendar. Other calendars become read-only (data preserved, not deleted). SMS reminders stop, email reminders continue. Team → Solo → data: appointments from non-primary calendars remain visible in a read-only archive for 90 days, then are deleted with 30-day warning email. Any plan → cancellation: access continues until period end. Data retained 30 days post-cancellation. Downloadable export available during retention period. After 30 days: anonymize PII, retain aggregate analytics."

### PRICE-AP-12: Missing Tax and Compliance
**Mistake:** Prices displayed and discussed without considering sales tax, VAT, and regional pricing differences. EU VAT alone changes the effective price by 15-25%, and many jurisdictions require tax-inclusive pricing in consumer-facing displays.
**Why:** Tax is invisible in most pricing discussions in training data. US-centric blog posts rarely mention VAT, and SaaS pricing articles discuss prices as clean round numbers ($29, $49, $99) without tax considerations. The model reproduces this tax-free simplicity, but real products selling internationally must handle tax from day one or face legal and financial consequences.
**Example:**
```
PRICE-12: International Pricing
Our pricing is the same worldwide:
Solo: $29/month
Team: $79/month
Simple and transparent.
```
**Instead:** Account for tax and regional factors: "US: prices shown ex-tax (standard SaaS practice). Tax calculated at checkout based on state (Stripe Tax handles this). EU: VAT must be included in displayed price for B2C (EU consumer protection law). $29 + 20% VAT = $34.80 displayed as 'EUR 34.80/month (incl. VAT).' B2B with valid VAT ID: reverse charge, display ex-VAT. UK: similar to EU post-Brexit, 20% VAT. India: 18% GST. Decision needed: (1) Single global price (absorb tax variance — simpler but lower margin in high-VAT countries). (2) Regional pricing (adjust base price by market — $29 US, EUR 25 EU, GBP 22 UK — to maintain margin parity). Recommendation: start with single global price + Stripe Tax. Implement regional pricing at 500+ customers when the revenue impact justifies the complexity."

### PRICE-AP-13: Price Anchoring Mistakes
**Mistake:** Presents pricing tiers left-to-right from cheapest to most expensive without a recommended tier highlight or visual anchoring. Users default to the cheapest option without context about which tier fits their needs, or they bounce because the enterprise tier is the first thing they see (if right-to-left).
**Why:** The model generates tiers in logical order (low to high) because that's the natural sort. It doesn't apply pricing psychology — anchoring, decoy effect, recommended tier highlighting — because these are behavioral economics concepts that appear in specialized marketing literature, not in typical pricing page descriptions. The model produces a neutral comparison table when it should produce a persuasion-optimized layout.
**Example:**
```
PRICE-13: Pricing Display
| Solo | Team | Enterprise |
|------|------|------------|
| $29/mo | $79/mo | Custom |
| 1 calendar | 5 calendars | Unlimited |
| Email | Email + SMS | Everything |
```
**Instead:** Design the pricing page as a conversion tool: "(1) Display order: Solo — Team (RECOMMENDED) — Enterprise. The recommended badge on Team creates an anchor. (2) Visual weight: Team column is larger, highlighted with primary brand color border, and has a 'Most Popular' badge. Solo and Enterprise are visually receded. (3) Decoy principle: if most users should pick Team, ensure the Solo-to-Team value gap is obvious (1 calendar vs. 5, email-only vs. SMS) while the price gap feels reasonable ($29 vs. $79 = $50 for 5x the capability). (4) CTA copy: Solo says 'Get started' (low commitment). Team says 'Start free trial' (action-oriented, references trial). Enterprise says 'Contact us' (appropriate for custom pricing). (5) Annual toggle: default to annual view (lower displayed number) with monthly available."
