# Architecture — Common Mistakes & Anti-Patterns

Common mistakes when running the architecture specialist. Each pattern
describes a failure mode that leads to poor architectural decisions.

**Referenced by:** `specialist_architecture.md`

> These patterns are **illustrative, not exhaustive**. They are a starting
> point — identify additional project-specific anti-patterns as you work.
> When a listed pattern doesn't apply to the current project, skip it.

---

## A. Technology Selection

### ARCH-AP-01: Resume-Driven Development
**Mistake:** Picks trendy tech (Kubernetes, microservices, GraphQL, event sourcing) because it appears frequently in training data, not because the project needs it.
**Why:** LLM training data is saturated with blog posts and conference talks celebrating complex infrastructure. These technologies generate more written content than simpler alternatives, creating a frequency bias that the model interprets as a recommendation signal.
**Example:**
```
ARCH-03: Container Orchestration
Use Kubernetes with Helm charts for deployment. Set up a 3-node cluster
with auto-scaling, Istio service mesh for inter-service communication,
and ArgoCD for GitOps-based continuous deployment.
```
**Instead:** State the deployment requirements first (expected load, team ops capacity, budget). For an MVP with 1-2 services, a single VM with Docker Compose or a PaaS like Railway/Render is appropriate. Kubernetes is justified only when you have multiple independently-scaling services AND an ops team to manage the cluster.

### ARCH-AP-02: Framework Popularity Bias
**Mistake:** Recommends the most popular framework without evaluating project fit. Defaults to React + Node.js for everything regardless of whether the project is a content site, an admin dashboard, or a real-time system.
**Why:** Popular frameworks dominate training data. The model has seen thousands of "how to build X with React" tutorials and very few "why you shouldn't use React for X" analyses. Popularity is mistaken for universal suitability.
**Example:**
```
ARCH-02: Frontend Framework
Use React 19 with Next.js App Router for the frontend. React's component
model and ecosystem make it the best choice for building modern web apps.
```
**Instead:** Evaluate against project requirements: Does the app need rich client-side interactivity (SPA justified)? Is it content-heavy with SEO needs (SSG/SSR framework or even plain HTML)? Is it a simple admin panel (server-rendered with HTMX or Livewire)? State why the chosen framework fits THIS project, not why it is popular.

### ARCH-AP-03: Ignoring Team Capability
**Mistake:** Proposes a tech stack the team has no experience with, without acknowledging the ramp-up cost or risk of learning-on-the-job during a deadline.
**Why:** The model has no awareness of the team's skill profile unless explicitly told. It optimizes for theoretical "best tool for the job" without factoring in the human cost of learning a new language, framework, or paradigm.
**Example:**
```
ARCH-04: Backend Language
Use Rust with Actix-web for the API server. Rust's memory safety guarantees
and performance characteristics make it ideal for building reliable services.
```
(proposed to a team of Python developers building a standard CRUD API)
**Instead:** Ask what the team already knows. Propose the stack that maximizes delivery speed given current skills. If a different technology is genuinely better, quantify the ramp-up cost (weeks, not "some learning") and present it as a tradeoff for the user to decide.

### ARCH-AP-04: Vendor Lock-In Blindness
**Mistake:** Recommends deep integration with a single cloud vendor's proprietary services (AWS Lambda + DynamoDB + SQS + Cognito) without discussing portability tradeoffs or cost implications.
**Why:** Cloud vendor documentation and tutorials are heavily represented in training data. AWS/GCP services are presented as solutions to specific problems without mentioning the switching cost. The model treats managed services as free abstractions.
**Example:**
```
ARCH-05: Message Queue
Use AWS SQS for async job processing with SNS for fan-out notifications.
Pair with DynamoDB for job state tracking and Lambda for worker functions.
```
**Instead:** Identify which services are commodity (any cloud can provide equivalent) vs proprietary (switching cost is high). For each proprietary service, state the lock-in tradeoff explicitly: "Using DynamoDB means your data access patterns are coupled to its key-value model. Migrating to PostgreSQL later would require rewriting the data layer." Let the user decide if the operational convenience is worth the coupling.

---

## B. Scaling & Complexity

### ARCH-AP-05: Premature Scaling
**Mistake:** Designs infrastructure for 1M concurrent users when the project has 100 beta users. Over-provisions databases, caching layers, CDNs, and load balancers from day one.
**Why:** Architecture blog posts and case studies almost exclusively cover scaling challenges. The model has absorbed thousands of "how we scaled to millions" posts and very few "how we shipped with a single Postgres instance." Designing for scale feels responsible; designing small feels risky.
**Example:**
```
ARCH-06: Caching Strategy
Deploy Redis Cluster with 3 sentinel nodes for session caching and query
result caching. Implement cache-aside pattern with TTL-based invalidation.
Add a CDN layer (CloudFront) for static assets and API response caching.
```
(for an internal tool with 50 users)
**Instead:** Start with the simplest thing that works. A single PostgreSQL instance handles thousands of requests per second. Application-level in-memory caching (LRU dict) handles most read-heavy patterns. Document the scaling triggers: "Add Redis when DB query latency exceeds 200ms at p95" or "Add CDN when static asset bandwidth exceeds $X/month." Scale in response to measured bottlenecks, not imagined ones.

### ARCH-AP-06: Microservices by Default
**Mistake:** Splits the application into 5+ microservices before understanding where the domain boundaries are. Creates inter-service communication overhead, distributed transaction problems, and operational complexity that a monolith avoids entirely.
**Why:** Microservices are the dominant architectural narrative in training data. Nearly every "modern architecture" article advocates for them. The model has learned that microservices = modern = good, without internalizing the prerequisites (team size, deployment independence, clear bounded contexts).
**Example:**
```
ARCH-01: Service Architecture
Split into 5 services: UserService, ProductService, OrderService,
NotificationService, AnalyticsService. Each owns its database.
Communication via REST + async events through RabbitMQ.
```
(for a 2-person team building an MVP)
**Instead:** Start with a well-structured monolith. Use internal module boundaries (separate packages/directories for users, products, orders) that COULD become services later. Split only when you have evidence: different scaling needs, different deployment cadences, or different team ownership. The monolith-first approach is endorsed by Martin Fowler, Sam Newman, and most practitioners who have actually operated microservices.

### ARCH-AP-07: Event-Driven Everything
**Mistake:** Proposes event sourcing, CQRS, or saga patterns for a straightforward CRUD application. Introduces eventual consistency problems where strong consistency would be simpler and correct.
**Why:** Event-driven architecture generates extensive technical content (conference talks, blog posts, books). The patterns are intellectually interesting, which amplifies their presence in training data. The model conflates "sophisticated" with "appropriate."
**Example:**
```
ARCH-08: Data Architecture
Use event sourcing with CQRS. Write events to an append-only event store,
project read models into materialized views. This gives us a complete
audit trail and the ability to replay state from any point in time.
```
(for a task management app)
**Instead:** Ask: Does the application need a full audit trail of every state change? Are read and write patterns so different that they need separate models? Is eventual consistency acceptable for the domain? If the answer to all three is "no" or "not yet," use a standard relational database with regular CRUD operations. Add an audit log table if you need history. Event sourcing is justified for financial systems, collaborative editing, and domains where the event history IS the business value.

### ARCH-AP-08: Abstraction Astronautics
**Mistake:** Creates layers of abstraction (ports, adapters, facades, abstract factories, strategy patterns) before understanding the actual integration points. The codebase has more interfaces than implementations.
**Why:** Clean Architecture, Hexagonal Architecture, and Domain-Driven Design patterns are heavily represented in training data. The model generates architecturally "pure" designs because that is what gets written about. Nobody writes blog posts about "I used a simple function call instead of the strategy pattern."
**Example:**
```
ARCH-09: Integration Layer
Implement Hexagonal Architecture with explicit ports and adapters.
Define port interfaces: PaymentPort, NotificationPort, StoragePort,
AnalyticsPort. Each has an adapter for the concrete implementation.
Add an anti-corruption layer between bounded contexts.
```
(for an app with one payment provider and one email service)
**Instead:** Write the simplest integration first. If you have one payment provider, write a `payment.py` module that calls Stripe directly. If you later need to swap providers, extract an interface THEN. The cost of premature abstraction is real: more files to navigate, harder onboarding, and refactoring the abstraction itself when the actual requirements diverge from the assumed ones.

---

## C. Decision Quality

### ARCH-AP-09: Cargo-Culting FAANG
**Mistake:** Copies architectural patterns from Netflix, Google, or Amazon that solve problems the project does not have. Cites FAANG case studies as justification without evaluating whether the same constraints apply.
**Why:** FAANG engineering blogs are high-prestige training data. The model treats patterns from these companies as best practices rather than context-specific solutions to extreme-scale problems.
**Example:**
```
ARCH-10: Resilience Patterns
Implement circuit breakers (Hystrix pattern) on all external calls,
bulkhead isolation for thread pools, and retry with exponential backoff
plus jitter. Add a chaos engineering framework for resilience testing.
```
(for an app calling 2 external APIs)
**Instead:** Identify which resilience patterns are proportional to the risk. A simple retry with timeout on HTTP calls covers 95% of failure modes for small applications. Circuit breakers matter when you have dozens of downstream dependencies and cascading failures are a real risk. Chaos engineering matters when your system is complex enough that you cannot reason about failure modes manually. State what problem each pattern solves and whether the project actually has that problem.

### ARCH-AP-10: Missing Cost Analysis
**Mistake:** Proposes an architecture without estimating the monthly infrastructure cost. Recommends serverless functions, managed databases, and premium services without a cost model.
**Why:** Architecture discussions in training data rarely include cost estimates. The model treats infrastructure as an abstract concern ("use the right tool") without connecting choices to dollars. Serverless appears cheap because you "only pay for what you use," but at moderate scale it can be 10x more expensive than a VM.
**Example:**
```
ARCH-11: Database
Use Aurora Serverless v2 for the primary database with DynamoDB for
session storage and ElastiCache Redis for caching. Enable multi-AZ
failover and automated backups with 30-day retention.
```
(no cost estimate provided, total would be ~$500+/month for an early-stage product)
**Instead:** Include a rough monthly cost estimate for every infrastructure decision. Compare: "Aurora Serverless v2 starts at ~$90/month minimum vs a single RDS t3.micro at ~$15/month." State the tradeoff: "Aurora auto-scales but has a higher floor. RDS requires manual scaling but costs 6x less at low traffic." Let the user make the cost-performance tradeoff explicitly.

### ARCH-AP-11: Ignoring Operational Complexity
**Mistake:** Recommends distributed systems, multiple databases, or complex deployment topologies without considering who will operate, debug, and monitor them day-to-day.
**Why:** Architecture content focuses on design-time decisions, not runtime operations. The model generates architectures optimized for theoretical elegance rather than operational simplicity. "Who gets paged at 3 AM when this breaks" is not a question that appears in training data.
**Example:**
```
ARCH-12: Observability
Deploy Prometheus + Grafana for metrics, Jaeger for distributed tracing,
ELK stack for log aggregation, and PagerDuty for alerting. Instrument
all services with OpenTelemetry.
```
(for a solo developer running 2 services)
**Instead:** Match operational tooling to team capacity. A solo developer needs application-level logging (structured JSON to stdout), a hosted error tracker (Sentry free tier), and basic uptime monitoring (UptimeRobot). Add distributed tracing when you actually have distributed services and cannot follow a request through logs alone. Each operational tool is itself a system that needs maintenance.

### ARCH-AP-12: Architecture Without Constraints
**Mistake:** Makes architectural decisions without referencing the project's constraints (budget, timeline, team size, existing infrastructure). Produces an architecture that is theoretically optimal but practically impossible to deliver.
**Why:** The model generates decisions based on technical merit alone unless constraints are explicitly injected into the prompt context. It does not spontaneously check constraints.md or ask about budget.
**Example:**
```
ARCH-07: Search
Implement Elasticsearch cluster for full-text search with custom analyzers,
synonym expansion, and faceted search. Deploy a 3-node cluster with
dedicated master nodes for resilience.
```
(project has a 4-week timeline, 1 developer, and $50/month budget)
**Instead:** Read constraints.md before making any decision. Cross-reference each ARCH-NN decision against budget, timeline, and team size. If a constraint conflicts with the ideal technical choice, state the conflict explicitly and propose a pragmatic alternative: "Full Elasticsearch would be ideal but exceeds the $50/month budget. PostgreSQL full-text search (ts_vector) covers 80% of the use case at zero additional cost."

### ARCH-AP-13: Conflating Logical and Physical Architecture
**Mistake:** Treats module boundaries (logical groupings of code) as deployment boundaries (separate services/containers) before there is evidence that independent deployment is needed.
**Why:** Architecture diagrams in training data frequently show boxes connected by arrows, and the model interprets each box as a separately deployed unit. The distinction between "these are separate concerns in the code" and "these need to be separate running processes" is rarely explicit in the source material.
**Example:**
```
Logical modules: Auth, Billing, Notifications, Analytics
→ Therefore: 4 microservices, each with its own database, deployed
  independently, communicating via REST + message queue.
```
**Instead:** Define the logical architecture first (modules, dependencies, interfaces). Then separately decide the physical architecture (what runs where). Multiple modules can live in one deployment unit (monolith, modular monolith). The trigger for physical separation is: different scaling needs, different deployment cadences, different team ownership, or regulatory isolation. State which trigger applies before splitting.
