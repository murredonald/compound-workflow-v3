# Testing — Common Mistakes & Anti-Patterns

Common mistakes when running the testing specialist. Each pattern
describes a failure mode that leads to poor test strategy decisions.

**Referenced by:** `specialist_testing.md`
> These patterns are **illustrative, not exhaustive**. They are a starting
> point — identify additional project-specific anti-patterns as you work.
> When a listed pattern doesn't apply to the current project, skip it.

---

## A. Strategy

### TEST-AP-01: 100% coverage target
**Mistake:** Sets 100% line coverage as the project goal. The team writes trivial tests for property accessors, configuration constants, and auto-generated code to hit the number, while complex business logic (calculations, state machines, permission checks) gets a single happy-path test.
**Why:** Coverage percentage is the most visible testing metric. LLMs produce round, confident numbers. "100% coverage" sounds like the obviously correct answer. The model does not distinguish between high-value test targets (business logic, error handling) and low-value targets (boilerplate, framework glue code).
**Example:**
```
TEST-03: Achieve 100% line coverage
  - All modules must have corresponding test files
  - Coverage gate: PR blocked if coverage drops below 100%
  - No exclusion patterns allowed
```
(Team writes `test_user_model.py` that tests `User.full_name` returns `f"{first} {last}"` but does not test the tax calculation engine's edge cases with negative numbers, rounding, or multi-state rules.)
**Instead:** Set coverage targets by module risk: "Business logic (calculations, workflows, permissions): 90%+ branch coverage with explicit edge case requirements. API endpoints: 80%+ with error path coverage. Configuration and boilerplate: excluded from coverage requirements. Overall project floor: 75% line coverage as a safety net, not the goal. Quality metric: each test file must include at least one edge case and one error path test."

### TEST-AP-02: Inverted test pyramid
**Mistake:** Plans mostly end-to-end (E2E) browser tests with few unit tests. E2E tests are slow (minutes each), flaky (network, timing, browser state), and expensive to maintain (break on any UI change). When the E2E suite fails, developers cannot tell which component is broken.
**Why:** E2E tests are visually impressive — "watch the browser click through the entire flow." LLMs default to the most demonstrable testing approach. Unit tests are unglamorous but catch 80% of bugs in 1% of the execution time.
**Example:**
```
TEST-05: Test strategy
  - E2E tests: 45 scenarios covering all user flows (Playwright)
  - Integration tests: 10 API endpoint tests
  - Unit tests: "as needed"
```
(45 E2E tests take 20 minutes to run. 3 fail intermittently due to animation timing. The team stops trusting the suite.)
**Instead:** Follow the test pyramid: "Unit tests (70% of tests): pure functions, business logic, state transitions, validators. Run in under 30 seconds. Integration tests (20%): API endpoints, database queries, service interactions. Run in under 3 minutes. E2E tests (10%): critical user journeys only (sign up, core workflow, payment). Run in under 5 minutes. Smoke tests: 3-5 E2E tests that run on every deploy to verify the application loads and the critical path works."

### TEST-AP-03: Testing implementation, not behavior
**Mistake:** Tests assert on internal state, mock call counts, method invocation order, or private variable values. Every refactor — even one that preserves the same external behavior — breaks the tests.
**Why:** LLMs generate tests by examining the implementation code. The model sees internal methods and private state, so it naturally writes assertions against them. Behavior-driven testing requires understanding the contract (inputs/outputs) separately from the implementation, which requires higher-level reasoning.
**Example:**
```python
def test_process_order():
    service = OrderService()
    service.process(order)

    # Testing implementation details
    assert service._internal_state == "processed"
    assert service.repository.save.call_count == 1
    assert service.email_service.send.call_args[0][0] == "order@test.com"
    assert service._validate_stock.called_before(service._charge_payment)
```
(Renaming `_internal_state` to `_status`, changing save to batch saves, or reordering internal steps all break these tests even if the order is processed correctly.)
**Instead:** Test observable behavior: "Given a valid order, when processed, then the order status returned is 'confirmed', the order appears in the database with correct totals, and the customer receives a confirmation email." Assert on outputs, side effects visible to the caller, and state accessible through the public API. Mock external dependencies (database, email) but assert on what was sent to them, not how many times or in what order.

### TEST-AP-04: No test data strategy
**Mistake:** Each test creates its own data inline with arbitrary values. There is no factory, fixture, or seed data system. Test data becomes inconsistent, duplicated across files, and fragile when the data model changes (every test that creates a User must be updated when a required field is added).
**Why:** LLMs generate self-contained tests because each test is produced independently. The model does not plan a test data architecture that spans multiple test files.
**Example:**
```python
def test_calculate_tax():
    user = User(name="Test", email="t@t.com", state="CA", income=50000,
                filing_status="single", created_at=datetime.now())
    # 15 fields of setup data duplicated in every test...

def test_calculate_deductions():
    user = User(name="Test2", email="t2@t.com", state="CA", income=75000,
                filing_status="married", created_at=datetime.now())
    # Same 15 fields, slightly different values, repeated 200 times...
```
(Adding a required `phone_number` field breaks 200 tests.)
**Instead:** Define a test data strategy: "Factories (pytest-factoryboy or custom): `UserFactory` with sensible defaults for all required fields. Tests override only the fields relevant to the test case. Fixtures: shared test data for integration tests (realistic users, orders, products) defined in `conftest.py` or `fixtures/`. Seed data: `scripts/seed.py` for development databases with representative data. Rule: no test should specify more than 3 fields unless those fields are directly relevant to the assertion."

### TEST-AP-05: One test approach for everything
**Mistake:** Uses the same testing pattern — typically integration tests through the HTTP layer — for both trivial utility functions and complex multi-step workflows. Simple functions get tested through the entire stack, making tests slow and failures hard to diagnose.
**Why:** LLMs reproduce the most common test pattern they have seen for the framework in question. For web apps, that is HTTP request/response tests. The model does not differentiate between code that needs integration testing and code that is purely functional.
**Example:**
```python
# Testing a pure math function through the entire HTTP stack
def test_calculate_percentage(client):
    response = client.post("/api/calculate", json={"value": 200, "percent": 15})
    assert response.json()["result"] == 30

# This function has no dependencies — it could be tested directly
def calculate_percentage(value: float, percent: float) -> float:
    return value * percent / 100
```
(If the HTTP test fails, is it the calculation, the serialization, the routing, or the authentication middleware? A direct unit test would pinpoint the issue instantly.)
**Instead:** Match the test approach to the code's dependency profile: "Pure functions (no I/O, no state): unit test directly, no HTTP, no database. Service layer (orchestrates dependencies): unit test with mocked dependencies for logic, integration test for one happy path. API endpoints: integration test through HTTP for contract validation (correct status codes, response shapes, auth). Full workflows: one E2E test for the critical path, covering the entire stack end-to-end."

---

## B. Implementation

### TEST-AP-06: Tautological assertions
**Mistake:** The test asserts that the code does what the code does, rather than asserting against an independently known correct value. The test always passes, even if the function is completely wrong.
**Why:** LLMs generate tests by calling the function and asserting the result matches... calling the function. The model pattern-matches on "call function, assert result" without verifying the expected value is independently correct.
**Example:**
```python
def test_calculate_total():
    items = [Item(price=10, qty=2), Item(price=5, qty=3)]
    result = calculate_total(items)
    assert result == calculate_total(items)  # Always passes

# Subtler version — recomputing the expected value with the same logic
def test_tax_calculation():
    income = 85000
    expected = income * 0.22  # Just reimplements the function's logic
    assert calculate_tax(income, "single") == expected
```
(If `calculate_tax` has a bug in the 22% bracket logic, the test has the same bug.)
**Instead:** Assert against hand-calculated values or known reference data: "For single filer with $85,000 income (2024 brackets): first $11,600 at 10% = $1,160, next $35,550 at 12% = $4,266, remaining $37,850 at 22% = $8,327. Expected total: $13,753. Source: IRS tax table." The expected value must be computed independently of the code being tested.

### TEST-AP-07: Brittle selectors in E2E
**Mistake:** E2E tests locate elements using CSS class names (`.btn-primary`), generated IDs (`#root > div:nth-child(3) > button`), or XPath expressions. Any design change, component refactor, or CSS framework update breaks every test.
**Why:** LLMs generate selectors from the current DOM structure because that is what is visible in the code. CSS classes and structural selectors are the first thing the model reaches for. `data-testid` attributes require intentional test infrastructure that is not present in most training examples.
**Example:**
```javascript
// Breaks when button class changes from "btn-primary" to "btn-accent"
await page.click('.btn-primary');

// Breaks when any parent element is added or removed
await page.click('#app > div.container > div.row:nth-child(2) > button');

// Breaks when the text changes for i18n
await page.click('text=Submit Your Application');
```
(A designer changes the button variant and 15 E2E tests break. The functionality is unchanged.)
**Instead:** Use stable selectors designed for testing: `data-testid="submit-application"` for specific elements, ARIA roles (`role="dialog"`, `role="alert"`) for semantic elements, and ARIA labels (`aria-label="Close"`) for interactive elements. Establish the convention at project start: "Every interactive element that E2E tests target must have a `data-testid` attribute. Test IDs follow the pattern `{page}-{component}-{action}` (e.g., `checkout-payment-submit`)."

### TEST-AP-08: Over-mocking
**Mistake:** Mocks so many dependencies that the test does not exercise any real code path. The test verifies that mocks return what they were configured to return, not that the system works correctly.
**Why:** LLMs mock every dependency they encounter because mock setup is well-documented and follows a repeatable pattern. The model does not evaluate which dependencies are worth mocking (external services, file system) versus which should be real (in-memory database, local computation).
**Example:**
```python
def test_create_user(mock_db, mock_validator, mock_hasher, mock_emailer, mock_logger):
    mock_validator.validate.return_value = True
    mock_hasher.hash.return_value = "hashed_pw"
    mock_db.save.return_value = User(id=1, name="Test")
    mock_emailer.send.return_value = True

    result = user_service.create_user("Test", "test@test.com", "password")

    assert result.id == 1  # Just asserting what the mock returns
    mock_db.save.assert_called_once()
```
(This test passes even if `create_user` does not call `validate` at all, hashes the wrong field, or saves incomplete data. The mocks ensure the test passes regardless of what the actual code does.)
**Instead:** Mock only external boundaries (network calls, file system, email sending). Use real implementations for everything else: "Validator: use real validator (it is pure logic). Password hasher: use real hasher (fast enough for tests). Database: use test database or in-memory SQLite. Email: mock (external service). The test should fail if validation logic is wrong, if hashing is skipped, or if the database receives incorrect data."

### TEST-AP-09: Shared mutable state between tests
**Mistake:** Tests share a database, global variable, or module-level state that persists between test runs. Tests pass when run individually but fail in suite because earlier tests pollute the state.
**Why:** LLMs generate tests sequentially and each test appears correct in isolation. The model does not simulate test execution order or reason about cross-test state contamination. Shared fixtures and module-level setup appear efficient, so the model uses them.
**Example:**
```python
# Module-level "optimization" that couples all tests
test_user = None

def test_create_user(db):
    global test_user
    test_user = db.create_user(name="Test", email="a@b.com")
    assert test_user.id is not None

def test_update_user(db):
    # Depends on test_create_user running first
    test_user.name = "Updated"
    db.save(test_user)
    assert db.get_user(test_user.id).name == "Updated"
```
(Running `test_update_user` alone fails with `NoneType has no attribute 'name'`. Running in randomized order fails. Adding a test between them may fail if it deletes the user.)
**Instead:** Each test creates its own state and cleans up after itself: "Use `pytest` fixtures with `function` scope (default). Each test creates the data it needs via factories. Database tests use transaction rollback (`@pytest.mark.django_db(transaction=True)` or equivalent) so each test starts with a clean state. Never use module-level mutable variables for test data. If setup is expensive (e.g., loading a large file), use `session` scope fixtures that are read-only."

### TEST-AP-10: Missing edge case coverage
**Mistake:** Tests cover the happy path (valid input produces expected output) but ignore boundaries, error conditions, and unusual inputs. The test suite passes with 80% coverage but the application crashes on the first real-world edge case.
**Why:** LLMs generate the obvious test case first and stop. The model produces what looks like a complete test (call function, assert result) without considering: what if the input is empty? What if it is at the boundary? What if it is null? What if two users submit simultaneously?
**Example:**
```python
def test_calculate_discount():
    assert calculate_discount(100, 0.2) == 80  # Happy path only

# Never tested:
# calculate_discount(0, 0.2)       — zero price
# calculate_discount(100, 0)       — zero discount
# calculate_discount(100, 1.0)     — 100% discount
# calculate_discount(100, 1.5)     — over 100% discount
# calculate_discount(-50, 0.2)     — negative price
# calculate_discount(100, -0.1)    — negative discount
# calculate_discount(0.01, 0.001)  — floating point precision
```
(The function has 7 edge cases. The test covers 1.)
**Instead:** For each function, enumerate edge cases systematically: "Zero values, boundary values (min/max), negative inputs, empty collections, None/null, extremely large values, floating point precision, Unicode strings, concurrent access. Use parameterized tests to cover multiple cases concisely. Rule: every test function must include at least one edge case alongside the happy path. For critical business logic, add property-based tests (Hypothesis/fast-check) to discover edge cases automatically."

---

## C. Maintenance & CI

### TEST-AP-11: Slow test suite
**Mistake:** The full test suite takes 10+ minutes to run. Developers stop running tests locally because the feedback loop is too slow. Tests are only run in CI, where failures are discovered 30 minutes after the commit.
**Why:** LLMs do not optimize for test execution time. Each test is generated independently without considering the cumulative runtime. The model does not distinguish between tests that need a real database (slow) and tests that could run in-memory (fast).
**Example:**
```
Test suite results:
  - 200 unit tests: 45 seconds (many hit the database unnecessarily)
  - 50 integration tests: 4 minutes (each spins up a test server)
  - 20 E2E tests: 8 minutes (full browser automation)
  Total: 12 minutes 45 seconds
```
(Developers run `git push` and go get coffee instead of running tests first.)
**Instead:** Separate test suites by speed: "Fast suite (under 30 seconds): unit tests with no I/O, mocked dependencies. Run on every save in watch mode. Medium suite (under 3 minutes): integration tests with test database. Run before commit. Slow suite (under 10 minutes): E2E tests. Run in CI only, or on-demand locally. Configure `pytest` markers: `@pytest.mark.slow` for anything over 1 second. Default `pytest` run excludes slow tests. CI runs all suites in parallel."

### TEST-AP-12: Flaky test tolerance
**Mistake:** Tests that intermittently fail are left in the suite with retry-on-failure configuration. The team accepts "oh, that test is flaky, just re-run" as normal. Flaky tests erode confidence in the entire suite — when a legitimate failure occurs, the team assumes it is flaky and ignores it.
**Why:** LLMs do not generate flaky tests intentionally, but they create the conditions for flakiness: timing-dependent assertions, shared state, network calls without retries, and animation-dependent E2E waits. When asked how to handle flaky tests, the model suggests retry logic because that is the most-documented immediate fix.
**Example:**
```yaml
# "Fixing" flaky tests by retrying them
pytest --retries 3 --retry-delay 5

# Or in Playwright
test.describe.configure({ retries: 2 });
```
(The test is flaky because it depends on a 300ms animation completing, or a background job finishing, or a race condition in shared state. Retrying masks the root cause.)
**Instead:** Flaky tests must be fixed or quarantined immediately: "When a test fails intermittently: 1) Move it to a `quarantine` directory or mark it `@pytest.mark.quarantine`. 2) Create a ticket to fix the root cause (timing issue, shared state, race condition). 3) Quarantined tests run in CI but do not block the pipeline. 4) Quarantine is reviewed weekly — tests are either fixed and restored or deleted. Maximum quarantine time: 2 sprints. If a test cannot be made reliable, it is not providing value."

### TEST-AP-13: No test categorization
**Mistake:** All tests run on every commit regardless of type. A commit to the payment module triggers E2E tests for the user profile page. A documentation change triggers the full integration test suite.
**Why:** The simplest CI configuration runs all tests on every trigger. LLMs reproduce this pattern because test categorization and selective execution require project-specific configuration that does not appear in basic tutorials.
**Example:**
```yaml
# Every push runs everything
on: push
jobs:
  test:
    steps:
      - run: pytest  # All 500 tests, every time
```
(A typo fix in a utility function triggers 20 minutes of E2E tests.)
**Instead:** Categorize tests and trigger selectively: "Smoke tests (5 tests, 30 seconds): run on every commit — verify the app starts and critical paths work. Unit tests: run on commits touching `src/`. Integration tests: run on commits touching `src/` or `tests/integration/`. E2E tests: run on PRs to main only, or when `tests/e2e/` is modified. Performance tests: run nightly or on-demand. Use pytest markers and CI path filters to implement selective execution."

### TEST-AP-14: Testing third-party behavior
**Mistake:** Writes tests that verify the behavior of frameworks, libraries, or ORMs rather than the project's own code. These tests add execution time and maintenance burden while testing code that the library maintainers already test.
**Why:** LLMs generate tests based on what code they see in the project. If the project uses SQLAlchemy, the model writes tests that verify SQLAlchemy correctly saves and retrieves data. The model does not distinguish between "code I wrote" and "code a library provides."
**Example:**
```python
def test_sqlalchemy_saves_correctly(db_session):
    """Tests that SQLAlchemy can save and retrieve a record."""
    user = User(name="Test", email="test@test.com")
    db_session.add(user)
    db_session.commit()
    retrieved = db_session.query(User).filter_by(name="Test").first()
    assert retrieved.email == "test@test.com"

def test_requests_parses_json():
    """Tests that the requests library can parse JSON."""
    response = requests.get("https://httpbin.org/json")
    data = response.json()
    assert isinstance(data, dict)
```
(SQLAlchemy's own test suite has 10,000+ tests. The `requests` library is one of the most tested Python packages. Your tests add no value here.)
**Instead:** Test YOUR code that uses the library: "Instead of testing that SQLAlchemy saves correctly, test that your `UserRepository.create()` method validates required fields, handles duplicate emails, and returns the correct shape. Instead of testing that `requests` parses JSON, test that your `APIClient.fetch_prices()` handles 404s, timeouts, and malformed responses. The boundary is: if you wrote the logic, test it. If a library wrote the logic, trust their tests and test your integration with it."
