# Domain — Common Mistakes & Anti-Patterns

Common mistakes when running the domain specialist. Each pattern
describes a failure mode that leads to poor domain modeling decisions.

**Referenced by:** `specialist_domain.md`
> These patterns are **illustrative, not exhaustive**. They are a starting
> point — identify additional project-specific anti-patterns as you work.
> When a listed pattern doesn't apply to the current project, skip it.

---

## A. Research Quality

### DOM-AP-01: Breadth Without Depth
**Mistake:** Researches 20 domain topics superficially instead of going deep on the 5 that actually matter for this project. Produces a glossary without real understanding.
**Why:** LLMs default to comprehensive coverage because training data rewards exhaustiveness. A 20-topic overview looks thorough but leaves each topic at Wikipedia depth. The model conflates "covering more ground" with "being more helpful" when the opposite is true for domain modeling.
**Example:**
```
## Domain Knowledge: Healthcare Scheduling

### Glossary
- Appointment: A scheduled meeting between patient and provider
- Provider: A healthcare professional
- Patient: A person receiving care
- Insurance: Coverage for medical costs
- Copay: Patient's share of cost
- Referral: Recommendation to see a specialist
- Prior Authorization: Insurance approval before treatment
- ... (15 more definitions)
```
**Instead:** Identify the 3-5 domain concepts that directly affect the data model and business logic. For a healthcare scheduling app, go deep on appointment lifecycle (requested → confirmed → checked-in → in-progress → completed → billed), provider availability rules (block scheduling vs. wave scheduling vs. open access), and insurance verification workflow. Each of these needs worked examples, edge cases, and state diagrams — not a one-line definition.

### DOM-AP-02: Wikipedia-Level Research
**Mistake:** Defines domain terms from general knowledge without researching how THIS industry actually uses them. "Invoice" means different things in different contexts.
**Why:** The model draws on broad training data where domain terms have generic definitions. It doesn't distinguish between how "invoice" works in freelance billing (single-party, immediate), construction (progress billing, retention), and healthcare (claim → EOB → patient responsibility). Without targeted research, it defaults to the most common usage.
**Example:**
```
DOM-03: Invoice Entity
An invoice is a document sent to a customer requesting payment for goods
or services. It contains line items, a total amount, and a due date.
Status: draft → sent → paid.
```
**Instead:** Research how invoices work in the specific industry. In construction: invoices follow a schedule of values, support partial billing against budget lines, require lien waivers before payment, and may include retention (5-10% held until project completion). The lifecycle is: draft → submitted → reviewed → approved → certified → paid (partial) → retention released. These differences fundamentally change the data model.

### DOM-AP-03: Single-Source Research
**Mistake:** Bases domain knowledge on one authoritative source without cross-validating. Industry standards, regulations, and practices vary by jurisdiction and company size.
**Why:** The model finds one definitive-sounding source and treats it as ground truth. It doesn't naturally cross-reference because each research round is independent. A single ISO standard, textbook, or regulatory document can be accurate but incomplete — real practice deviates from written standards.
**Example:**
```
DOM-05: Payment Processing Rules
Per PCI DSS v4.0, all card data must be encrypted in transit and at rest.
We will implement tokenization via Stripe and never store raw card numbers.
```
**Instead:** Cross-reference at least 3 sources: the formal standard (PCI DSS), a practitioner guide (how companies actually implement it), and a failure case study (what goes wrong). For payment processing: PCI DSS defines the floor, but you also need to understand 3D Secure requirements (which vary by card network and region), strong customer authentication (SCA) for EU transactions, and the practical difference between merchant-of-record vs. payment facilitator models. One source gives you compliance; three sources give you a working system.

### DOM-AP-04: Skipping Practitioner Knowledge
**Mistake:** Researches from textbooks and official documentation but ignores how practitioners actually work. The gap between theory and practice IS the domain knowledge that matters most.
**Why:** Training data is dominated by formal documentation, standards, and textbook descriptions. Practitioner knowledge lives in forum posts, case studies, and experience reports that are less represented and harder to extract. The model defaults to the "official" version of how things work.
**Example:**
```
DOM-07: Inventory Management
Inventory is tracked using the perpetual inventory method. Each item has
a SKU, quantity on hand, reorder point, and reorder quantity. When stock
falls below the reorder point, a purchase order is automatically generated.
```
**Instead:** Practitioners know that perpetual inventory counts drift from reality (shrinkage, miscounts, receiving errors). Real systems need cycle counting schedules, adjustment workflows with approval chains, discrepancy thresholds that trigger investigation vs. auto-correction, and the concept of "available to promise" (on-hand minus reserved minus in-QC). The reorder point is rarely a simple threshold — it factors in lead time variability, demand forecasting, and safety stock calculations that change seasonally.

---

## B. Modeling

### DOM-AP-05: Over-Formalized Domain
**Mistake:** Creates a UML-level domain model with bounded contexts, aggregates, and domain events for a simple CRUD application. Not every project needs DDD tactical patterns.
**Why:** Domain-Driven Design content is heavily overrepresented in LLM training data relative to its actual applicability. Blog posts about bounded contexts and aggregate roots outnumber posts about "just use a relational schema" by orders of magnitude. The model pattern-matches "domain modeling" to "DDD" regardless of complexity.
**Example:**
```
DOM-08: Domain Model Architecture
The scheduling domain will use bounded contexts:
- Appointment Context (aggregate root: Appointment)
- Provider Context (aggregate root: Provider)
- Patient Context (aggregate root: Patient)

Domain events:
- AppointmentRequested, AppointmentConfirmed, AppointmentCancelled
- ProviderAvailabilityChanged, PatientRegistered

Anti-corruption layer between Appointment and Billing contexts.
```
**Instead:** Ask: How many entities? How complex are the business rules? Is there genuine domain complexity (conflicting rules, complex state machines, multi-step workflows) or just data complexity (many fields, many records)? A scheduling app with 5-8 entities and straightforward CRUD operations needs a clean relational schema with well-named tables, not bounded contexts. Reserve DDD tactical patterns for domains where business rules genuinely conflict across subdomains.

### DOM-AP-06: Inconsistent Terminology
**Mistake:** Uses "client", "customer", and "user" interchangeably in the same domain model. Every concept needs exactly one canonical name used everywhere — code, docs, UI, and API.
**Why:** The model generates natural-sounding prose, and English favors synonym variation for readability. In a 2000-word domain document, using the same word 50 times feels repetitive, so the model substitutes synonyms. But in domain modeling, synonyms are bugs — they create ambiguity about whether "client" and "customer" are the same entity.
**Example:**
```
DOM-02: Core Entities
- User: person who logs into the system
- Customer: person who purchases a subscription
- Client: person whose data is managed in the system

The user creates projects. When a client upgrades their plan,
the customer's billing information is updated.
```
**Instead:** Choose ONE term and enforce it universally. If the domain calls them "clients," then the database table is `clients`, the API endpoint is `/clients`, the UI says "Clients," and the code uses `Client` class. Document rejected synonyms explicitly: "We say 'client', never 'customer' or 'user' (unless referring to authentication identity)." Build a ubiquitous language glossary where each concept has exactly one name.

### DOM-AP-07: Missing Entity Relationships
**Mistake:** Lists entities and their fields but doesn't define cardinality, ownership, or lifecycle dependencies. The relationships between entities are more important than the entities themselves.
**Why:** The model generates entity definitions as independent blocks because each entity is conceptually self-contained in description. Relationships require cross-referencing and reasoning about constraints that span multiple entities — a harder cognitive task that the model often skips in favor of completing each entity's field list.
**Example:**
```
DOM-04: Entity Definitions
Project: id, name, description, status, created_at
Task: id, title, description, priority, status, due_date
User: id, name, email, role
Comment: id, body, created_at
```
**Instead:** Define relationships with cardinality and constraints: A Project has many Tasks (1:N, cascade delete). A Task belongs to one Project (required) and is assigned to zero or one User (optional). A Comment belongs to one Task (required) and one User (required). When a User is deactivated, their Tasks are unassigned (not deleted) and their Comments are preserved (attributed to "Deleted User"). When a Project is archived, its Tasks cannot transition to "in-progress." These dependency rules drive the actual database schema and API behavior.

### DOM-AP-08: Static Model Only
**Mistake:** Captures entities and their fields but not workflows, state transitions, or business processes. Domain knowledge is about HOW things happen, not just WHAT exists.
**Why:** Entity definitions are easy to generate — they look like database schemas, which are abundant in training data. Process descriptions require temporal reasoning (what happens in what order, under what conditions, with what exceptions) which is harder to generate correctly. The model gravitates toward the easier structural output.
**Example:**
```
DOM-06: Order Entity
Fields: id, customer_id, items[], total, status, created_at, updated_at
Status values: pending, confirmed, shipped, delivered, cancelled
```
**Instead:** Map the full lifecycle: Order is created (status: pending, payment hold placed). Merchant confirms within 24h or auto-cancels (pending → confirmed OR pending → cancelled + payment released). Warehouse picks and packs (confirmed → processing). Carrier scans pickup (processing → shipped, tracking number assigned). Customer receives (shipped → delivered, delivery confirmation triggers payment capture). Customer disputes (delivered → disputed, within 30-day window only, triggers hold on merchant payout). Each transition has preconditions, side effects, and exception handling.

---

## C. Communication

### DOM-AP-09: Domain Expert Jargon
**Mistake:** Produces domain documentation filled with jargon that only a domain expert would understand. The purpose of domain modeling is to translate domain knowledge into terms developers can implement.
**Why:** When researching a domain, the model absorbs specialist terminology and reproduces it without simplification. Medical, legal, and financial domains have dense jargon that appears in training data as-is. The model doesn't distinguish between "source material I'm reading" and "documentation I'm writing for developers."
**Example:**
```
DOM-09: Claims Adjudication
The TPA performs adjudication against the SPD, applying COB rules for
dual-eligible members. EOBs are generated post-adjudication with CARC/RARC
codes. Subrogation claims follow the plan's MOB provisions.
```
**Instead:** Every jargon term needs a plain-language definition on first use AND a developer-oriented explanation of what it means for the system: "Claims adjudication: the process of deciding whether an insurance claim should be paid and how much. For our system, this means: (1) receive claim data via 837 EDI file, (2) match against member eligibility rules, (3) apply benefit calculations from the plan configuration, (4) generate a payment or denial record. The TPA (Third-Party Administrator) runs this process — we integrate with their API, not replace them."

### DOM-AP-10: Missing Edge Cases
**Mistake:** Documents the happy path business rules but ignores exceptions, partial states, and conflict resolution. Real systems spend 80% of their complexity on edge cases.
**Why:** Happy paths are well-documented in training data — tutorials, getting-started guides, and product descriptions all describe how things work when everything goes right. Edge cases are documented in support forums, incident reports, and internal wikis that are underrepresented in training data. The model generates the version of reality it has seen most often.
**Example:**
```
DOM-10: Payment Processing
Customer selects a plan, enters payment info, and is charged monthly.
If payment fails, the system retries. After successful payment, access
is granted immediately.
```
**Instead:** Document the edge cases explicitly: What happens when payment fails on the 1st retry? (grace period: 3 days, access continues) 2nd retry? (warning email, access continues) 3rd retry? (access suspended, "update payment" screen on login) What about partial refunds — does the user keep pro-rated access? What if a user disputes a charge via their bank (chargeback) — immediate suspension or investigation period? What happens to data created during an unpaid period if the subscription is eventually cancelled? Each edge case is a business rule that needs a decision.

### DOM-AP-11: Regulatory Landscape as Checkbox
**Mistake:** Lists applicable regulations ("GDPR applies", "SOC 2 required") without mapping specific obligations to specific data fields, processing activities, and system behaviors.
**Why:** Regulatory compliance in training data is often discussed at the summary level — "you need to comply with GDPR" — rather than at the implementation level. The model reproduces this surface-level treatment because detailed regulation-to-code mappings are rare in public training data.
**Example:**
```
DOM-11: Compliance Requirements
- GDPR: Must comply for EU users
- CCPA: Must comply for California users
- HIPAA: Must comply if handling health data
- SOC 2: Required for enterprise customers
```
**Instead:** Map each regulation to concrete system requirements: GDPR Article 17 (right to erasure) means: user can request deletion → system must delete all PII from `users`, `profiles`, `payment_methods` within 30 days → BUT must retain invoice records for tax compliance (Article 6(1)(c) legal obligation) → SO anonymize invoices (replace name/email with hash) rather than delete. This creates specific implementation tasks: a deletion workflow, an anonymization function, a retention policy table, and an audit log of deletion requests.

### DOM-AP-12: No Worked Examples
**Mistake:** Defines business rules abstractly without concrete examples showing inputs, calculations, and outputs. Developers can't implement a rule they can't trace through manually.
**Why:** Abstract rule statements are compact and feel complete. Worked examples require the model to simulate a specific scenario with real numbers, which takes more tokens and requires arithmetic reasoning that models sometimes avoid. "Late fees apply after the due date" sounds like a complete rule but is actually unimplementable.
**Example:**
```
DOM-12: Late Fee Calculation
Late fees are applied to overdue invoices. The fee is calculated based
on the outstanding balance and the number of days overdue, subject to
any applicable maximum fee caps.
```
**Instead:** Provide a worked example: Invoice #1042, amount $5,000, due date Jan 15. Payment received Feb 3 (19 days late). Late fee calculation: base rate 1.5% per month = 0.05% per day. 19 days x 0.05% x $5,000 = $47.50. State maximum cap: $500 or 10% of invoice (whichever is lower) = $47.50 (under cap, applied as-is). Grace period: first 5 days are fee-free, so actual billable late days = 14. Revised: 14 x 0.05% x $5,000 = $35.00. Minimum fee: $25. Final late fee: $35.00. Now a developer can implement this.
