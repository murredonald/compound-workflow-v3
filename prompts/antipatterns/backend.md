# Backend — Common Mistakes & Anti-Patterns

Common mistakes when running the backend specialist. Each pattern
describes a failure mode that leads to poor API and data decisions.

**Referenced by:** `specialist_backend.md`
> These patterns are **illustrative, not exhaustive**. They are a starting
> point — identify additional project-specific anti-patterns as you work.
> When a listed pattern doesn't apply to the current project, skip it.

---

## A. API Design

### BACK-AP-01: CRUD-Only Thinking
**Mistake:** Maps every entity to 5 REST endpoints (list, get, create, update, delete) without considering business operations that span multiple entities or represent domain actions.
**Why:** REST resource tutorials dominate training data and almost always demonstrate single-entity CRUD. The model has internalized "1 entity = 1 resource = 5 endpoints" as the default pattern. Business operations that don't map cleanly to a single resource (e.g., "checkout," "transfer," "approve") get shoehorned into awkward PATCH calls.
**Example:**
```
POST   /api/orders          # Create order
GET    /api/orders/:id      # Get order
PATCH  /api/orders/:id      # Update order (used for status changes too)
DELETE /api/orders/:id      # Cancel order
POST   /api/payments        # Create payment
PATCH  /api/inventory/:id   # Decrement stock
```
(checkout requires the client to call 3 endpoints in sequence, handling partial failures)
**Instead:** Design APIs around business operations, not database tables. A checkout is a single action: `POST /api/orders/:id/checkout` that atomically creates the payment, decrements inventory, and transitions the order status. The API surface should match the user's mental model of what they are doing, not the developer's mental model of where data lives.

### BACK-AP-02: API Designed for the Database
**Mistake:** Endpoints mirror database tables 1:1 instead of serving frontend workflows. The frontend needs to make 4 API calls to render one page because each entity is a separate endpoint.
**Why:** The model designs the API by looking at the data model rather than the UI requirements. Each table becomes a resource, and the frontend assembles the page from multiple fetches. This is technically "correct" REST but creates chatty APIs that hurt performance and developer experience.
**Example:**
```
GET /api/users/:id           → { name, email, avatar_url }
GET /api/users/:id/settings  → { theme, notifications, language }
GET /api/users/:id/stats     → { posts_count, followers_count }
GET /api/users/:id/badges    → [{ name, earned_at }]
```
(profile page needs all 4 calls, creating a waterfall)
**Instead:** Design endpoints for the screens that consume them. A profile page endpoint returns everything the profile page needs: `GET /api/users/:id/profile` with embedded settings, stats, and badges. Internal boundaries (separate tables, separate services) are implementation details the client should not need to know about. Use GraphQL or BFF (Backend For Frontend) patterns if different clients need different shapes.

### BACK-AP-03: Inconsistent Error Responses
**Mistake:** Different endpoints return errors in different shapes. Some return `{ "error": "message" }`, others return `{ "detail": "message" }`, others return `{ "errors": [{ "field": "email", "message": "invalid" }] }`. Status codes are used inconsistently.
**Why:** The model generates each endpoint independently without a shared error contract. Each endpoint's error handling is influenced by whatever tutorial or framework convention was most prominent in the training data for that specific pattern.
**Example:**
```python
# Endpoint A
return JSONResponse({"error": "User not found"}, status_code=404)

# Endpoint B
raise HTTPException(status_code=400, detail="Invalid email format")

# Endpoint C
return JSONResponse({"message": "Validation failed", "errors": {"name": "required"}}, status_code=422)
```
**Instead:** Define a single error envelope in BACK-01 or BACK-02 and reference it for all endpoints. Example standard: `{ "error": { "code": "VALIDATION_ERROR", "message": "Human-readable summary", "details": [{ "field": "email", "issue": "invalid format" }] } }`. Map HTTP status codes to error categories: 400 = validation, 401 = auth, 403 = permission, 404 = not found, 409 = conflict, 422 = business rule, 500 = server error.

### BACK-AP-04: Verb-Based URLs
**Mistake:** Uses verbs in URLs (`/api/createUser`, `/api/getOrderById`, `/api/deleteProduct`) instead of resource-based naming with HTTP methods carrying the verb semantics.
**Why:** RPC-style naming appears in older APIs and internal codebases in the training data. The model sometimes generates a hybrid of REST and RPC conventions, especially when the prompt uses verb phrases like "create a user endpoint."
**Example:**
```
POST   /api/createUser
GET    /api/getUserById/:id
POST   /api/updateUserEmail
DELETE /api/removeUser/:id
GET    /api/searchProducts?q=...
POST   /api/processPayment
```
**Instead:** Use resource nouns with HTTP methods: `POST /api/users` (create), `GET /api/users/:id` (read), `PATCH /api/users/:id` (update), `DELETE /api/users/:id` (delete). For actions that don't map to CRUD, use sub-resource verbs: `POST /api/orders/:id/cancel`, `POST /api/payments/:id/refund`. Search is a GET with query params: `GET /api/products?q=...`.

### BACK-AP-05: Over-Documenting Obvious Endpoints
**Mistake:** Spends equal design effort on trivial CRUD endpoints (list users, get user by ID) and complex business logic endpoints (checkout flow, permission evaluation, multi-step wizards). The complex endpoints get the same shallow treatment as the simple ones.
**Why:** The model processes each endpoint with uniform attention. It does not distinguish between endpoints that are trivially implemented (standard ORM queries) and endpoints that encode critical business logic (state machines, multi-entity transactions, authorization rules).
**Example:**
```
BACK-03: GET /api/users/:id
Returns user by ID. Fields: id, name, email, created_at.
Status codes: 200 OK, 404 Not Found.

BACK-04: POST /api/orders/:id/checkout
Processes checkout. Status codes: 200 OK, 400 Bad Request.
```
(the checkout endpoint gets 2 lines; it actually needs to define: inventory reservation, payment authorization, failure rollback, confirmation email trigger, and order state transitions)
**Instead:** Spend decision depth proportional to complexity. Simple CRUD endpoints can be a single line: "Standard CRUD for users — see error envelope in BACK-01." Complex endpoints need: preconditions, step-by-step flow, transaction boundaries, failure modes and rollback behavior, side effects (emails, webhooks), and state transitions.

---

## B. Data & Validation

### BACK-AP-06: Float for Money
**Mistake:** Uses `float` or `double` for monetary values, introducing rounding errors that accumulate across calculations. Prices of $19.99 become $19.990000000000002.
**Why:** `float` is the default numeric type in most training examples. Financial precision requirements are domain knowledge that the model does not spontaneously apply unless the context mentions money explicitly. The error is invisible in simple examples and only manifests in aggregations.
**Example:**
```python
class Product(Base):
    price = Column(Float)  # $19.99 stored as 19.990000000000002

class Order(Base):
    subtotal = Column(Float)
    tax = Column(Float)
    total = Column(Float)  # accumulated rounding errors
```
**Instead:** Use `Decimal` (Python), `numeric(10,2)` (PostgreSQL), or integer cents (store $19.99 as 1999). Define the money representation in a single BACK-NN decision and apply it everywhere. If using Decimal, set the precision explicitly: `Column(Numeric(10, 2))`. If using integer cents, document the conversion convention and put the formatting logic in one place.

### BACK-AP-07: Sequential IDs Exposed
**Mistake:** Uses auto-increment integer IDs in public URLs and API responses, enabling enumeration attacks (`/api/users/1`, `/api/users/2`, ...) and leaking business metrics (order count, user count).
**Why:** Auto-increment IDs are the default in every ORM tutorial. The model uses them because they are simple and universally demonstrated. The security implication (enumeration) and business implication (competitors can count your orders) are not discussed in typical tutorial contexts.
**Example:**
```
GET /api/invoices/1042    → attacker tries /api/invoices/1043, 1044, ...
GET /api/users/5          → competitor knows you have ~5 users
```
**Instead:** Use UUIDs (v4 or v7) for public-facing identifiers. Keep auto-increment IDs as internal database primary keys for join performance, but expose only the UUID in API responses and URLs. Alternatively, use hashids/sqids for shorter URL-friendly IDs. Define this convention in a single decision and apply it to all public-facing entities.

### BACK-AP-08: Validation Only at One Layer
**Mistake:** Puts all validation in the request handler (Pydantic model, form validator) with no database constraints, or puts all validation in database constraints with no user-friendly error messages.
**Why:** The model follows whichever validation pattern is most prominent for the framework being used. FastAPI examples emphasize Pydantic validation; Django examples emphasize model validation. Neither consistently demonstrates both layers working together.
**Example:**
```python
# All validation in Pydantic, nothing in DB
class CreateUser(BaseModel):
    email: EmailStr
    age: int = Field(ge=18)

# Database has no constraints:
class User(Base):
    email = Column(String)       # no unique, no not-null
    age = Column(Integer)        # no check constraint
```
**Instead:** Validate at both layers with different purposes. Application layer (Pydantic/serializer): user-friendly error messages, format validation, business rule checks. Database layer: NOT NULL, UNIQUE, CHECK constraints, foreign keys — the safety net that prevents bad data even if application code has bugs or data is inserted via migration scripts. State this dual-validation strategy in a BACK-NN decision.

### BACK-AP-09: Missing State Machine Design
**Mistake:** Entities with status fields (`order.status`, `ticket.state`, `payment.status`) but no defined transition rules. Any status can change to any other status through a generic PATCH endpoint.
**Why:** State machines require explicit domain modeling that the model skips unless specifically prompted. The default pattern is a string/enum field with no transition validation, because that is what appears in tutorial code.
**Example:**
```python
class Order(Base):
    status = Column(String)  # "pending", "paid", "shipped", "cancelled"

# Any transition is possible:
PATCH /api/orders/123 {"status": "shipped"}  # from "cancelled"? Sure!
```
**Instead:** Define valid transitions explicitly: `pending -> paid -> shipped -> delivered` and `pending -> cancelled`, `paid -> refunded`. Implement a transition function that rejects invalid moves. Document the state machine as a BACK-NN decision with a diagram or transition table. Each transition should have: preconditions, side effects (emails, inventory updates), and who is authorized to trigger it.

### BACK-AP-10: Soft Delete Without Cleanup
**Mistake:** Adds `deleted_at` / `is_deleted` to every table without defining a purge strategy, query filtering convention, or cascade behavior. Deleted records accumulate forever, queries silently include deleted data, and unique constraints break.
**Why:** Soft delete appears in training data as a "best practice" without the operational concerns. The model adds the column but not the supporting infrastructure (default query scope, purge job, unique constraint handling).
**Example:**
```python
class User(Base):
    email = Column(String, unique=True)
    deleted_at = Column(DateTime, nullable=True)
    # Problem: deleted user's email blocks new registration
    # Problem: SELECT * FROM users returns deleted users
    # Problem: deleted records grow forever
```
**Instead:** Decide per-entity whether soft delete is needed (audit requirements, undo capability) or hard delete is sufficient. For soft-deleted entities: add a default query scope that filters deleted records, use partial unique indexes (`UNIQUE(email) WHERE deleted_at IS NULL`), define a purge policy (e.g., hard-delete after 90 days), and document cascade behavior (what happens to a deleted user's orders?).

---

## C. Service Logic & Integration

### BACK-AP-11: No Transaction Boundaries
**Mistake:** Multi-step operations (create order + reserve inventory + charge payment) without defining what is atomic. A failure midway leaves the system in an inconsistent state: payment charged but inventory not reserved, or order created but payment failed.
**Why:** Transaction management is rarely explicit in training examples. ORM tutorials show single-model operations where the default auto-commit behavior works fine. The model does not spontaneously identify operations that span multiple models as needing explicit transaction boundaries.
**Example:**
```python
async def checkout(order_id: int):
    order = await Order.get(order_id)
    order.status = "paid"
    await order.save()              # committed
    await inventory.decrement()     # fails → order is "paid" but stock not reserved
    await payment.charge()          # never reached
```
**Instead:** Define transaction boundaries for every multi-step operation in the BACK-NN decisions. Use database transactions for operations that touch multiple tables in one database. For operations spanning external services (payment gateway + local DB), define the compensation/rollback strategy: charge first then record, or record as pending then charge then confirm. Document what happens on partial failure.

### BACK-AP-12: Synchronous Everything
**Mistake:** Makes external API calls (email sends, webhook deliveries, PDF generation, payment processing) in the HTTP request path, blocking the response while waiting for external services that may be slow or down.
**Why:** Synchronous code is simpler to write and reason about. Training data shows request handlers that do everything inline because the examples are small. The model does not spontaneously identify which operations should be asynchronous unless the latency impact is obvious.
**Example:**
```python
@app.post("/api/orders")
async def create_order(data: OrderCreate):
    order = Order.create(**data.dict())
    send_confirmation_email(order)      # blocks 2-5 seconds
    notify_warehouse_webhook(order)     # blocks 1-3 seconds
    generate_invoice_pdf(order)         # blocks 3-10 seconds
    return order                        # total: 6-18 seconds response time
```
**Instead:** Identify which operations are on the critical path (must complete before the response) and which are side effects (can happen after the response). Critical path: validate input, create the database record, charge payment. Side effects: email, webhooks, PDF generation, analytics. Process side effects via a background task queue (Celery, RQ, or even a simple database-backed job table). Define this split in the BACK-NN decisions for each major endpoint.

### BACK-AP-13: Repository Pattern as Cargo Cult
**Mistake:** Wraps every ORM call in a repository class with methods like `get_by_id()`, `get_all()`, `create()`, `update()`, `delete()` — even though the ORM already provides these exact operations. The repository adds a layer of indirection with no additional logic.
**Why:** Repository pattern is heavily promoted in Clean Architecture and DDD literature that dominates training data. The model applies it as a universal best practice without evaluating whether the abstraction provides value for the specific project.
**Example:**
```python
class UserRepository:
    def get_by_id(self, id: int) -> User:
        return self.session.query(User).get(id)

    def get_all(self) -> list[User]:
        return self.session.query(User).all()

    def create(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        return user
```
(every method is a one-line pass-through to SQLAlchemy)
**Instead:** Use the repository pattern only when it provides real value: complex queries that should be named and reusable, queries that need to work across different storage backends, or when you want to mock the data layer in tests without a test database. For simple CRUD, call the ORM directly from the service/handler layer. If you later need a repository, extract it then.

### BACK-AP-14: Cursor Pagination Everywhere
**Mistake:** Uses cursor-based pagination for all list endpoints, including admin panels and backoffice tools where users need to jump to specific pages, see total counts, or navigate to "page 47 of 200."
**Why:** Cursor pagination is recommended as "the scalable choice" in API design guides. The model adopts it universally without considering the UX requirements of different consumers.
**Example:**
```
GET /api/admin/audit-logs?cursor=eyJpZCI6MTAwfQ==&limit=50
→ { "data": [...], "next_cursor": "eyJpZCI6MTUwfQ==" }
```
(admin needs to jump to logs from last Tuesday, has to page through sequentially from the beginning)
**Instead:** Choose pagination strategy based on the consumer. Public APIs with potentially large result sets: cursor pagination (stable, scalable). Admin panels and backoffice: offset pagination with total count (jumpable, filterable). Search results: offset with capped depth (Google stops at ~1000 results). Infinite scroll feeds: cursor pagination. Document the rationale per endpoint category.

### BACK-AP-15: Auth as Afterthought
**Mistake:** Designs all endpoints as public, then adds authentication and authorization as a separate concern later. The permission model is bolted on after the API surface is finalized, leading to gaps where endpoints lack proper access control.
**Why:** Auth adds complexity that slows down the design process. The model separates "API design" from "security" because they appear as different specialist domains. It designs clean APIs first and assumes auth will be layered on, but the API design itself should be informed by who can do what.
**Example:**
```
BACK-05: API Endpoints
GET    /api/users          # list all users
GET    /api/users/:id      # get any user
PATCH  /api/users/:id      # update any user
DELETE /api/users/:id      # delete any user
GET    /api/admin/reports   # admin reports

(auth decisions deferred to security specialist)
```
**Instead:** Define the permission model alongside the API surface. For each endpoint, specify: who can call it (anonymous, authenticated user, admin, owner-only), what data scoping applies (users see only their own data vs admin sees all), and what the authorization check looks like. This changes the API design itself: maybe `/api/users/:id` returns different fields based on role, or maybe you need separate `/api/me` and `/api/admin/users/:id` endpoints. Auth is not a layer; it is a design input.
