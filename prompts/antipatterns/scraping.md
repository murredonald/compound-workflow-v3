# Scraping — Common Mistakes & Anti-Patterns

Common mistakes when running the scraping specialist. Each pattern
describes a failure mode that leads to poor data ingestion decisions.

**Referenced by:** `specialist_scraping.md`
> These patterns are **illustrative, not exhaustive**. They are a starting
> point — identify additional project-specific anti-patterns as you work.
> When a listed pattern doesn't apply to the current project, skip it.

---

## A. Technical

### INGEST-AP-01: Scraping When an API Exists
**Mistake:** Builds a web scraper before checking whether the target source offers an official API, RSS feed, data export, or bulk download. APIs are more reliable, faster, structured, rate-limit-friendly, and usually legal.
**Why:** LLM training data contains far more scraping tutorials than API integration guides for the same data sources. "How to scrape X" generates more blog content than "how to use X's API." The model defaults to the approach it has seen most frequently, not the most appropriate one.
**Example:**
```
INGEST-02: Product Data Ingestion
Scrape product listings from Amazon using BeautifulSoup. Parse the HTML
to extract product name, price, rating, and review count from the search
results page.
```
**Instead:** First check: does the source offer an API? Amazon has the Product Advertising API. Most major platforms (GitHub, Twitter/X, Reddit, Google Maps, Yelp) have APIs. Check for RSS feeds, sitemaps, data exports, or partner data programs. Only scrape when no structured access exists AND the data is legally accessible. Document why scraping was chosen over alternatives.

### INGEST-AP-02: Brittle CSS Selectors
**Mistake:** Uses deeply nested, position-dependent CSS selectors that break when the target site changes its markup. A single class name change or DOM restructuring silently breaks the scraper.
**Why:** The model generates selectors by imagining a plausible DOM structure and writing the most specific selector that would match it. It has no concept of selector fragility because training data shows working selectors, not selectors that broke after a site redesign.
**Example:**
```
INGEST-04: Price Extraction
selector = "div.search-results > div:nth-child(3) > div.product-card > \
            div.details > span.price-whole"
price = soup.select_one(selector).text
```
**Instead:** Use resilient selector strategies in priority order: (1) data attributes (`[data-testid="price"]`, `[data-product-id]`) — these are designed for programmatic access and change less often. (2) Semantic selectors (`article`, `[itemprop="price"]`, `[role="listitem"]`) — tied to meaning, not layout. (3) Text-matching as a fallback (find element containing "$" near a product name). Layer multiple strategies with fallback chains. Alert on selector failures rather than returning garbage.

### INGEST-AP-03: No Rate Limiting
**Mistake:** Sends concurrent requests as fast as the network allows. Overwhelms the target server, gets IP-banned, triggers WAF blocks, and potentially violates computer access laws (CFAA in the US, Computer Misuse Act in the UK).
**Why:** The model optimizes for task completion speed. Rate limiting is a politeness and legal constraint that does not appear in the typical "scrape this page" code snippet. Training data emphasizes getting the data, not getting it responsibly.
**Example:**
```
INGEST-03: Crawl Strategy
async def crawl_all(urls: list[str]):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for url in urls]
        return await asyncio.gather(*tasks)  # 10,000 concurrent requests
```
**Instead:** Implement rate limiting at multiple levels: (1) Respect `Crawl-delay` in robots.txt. (2) Add a minimum delay between requests (1-2 seconds for most sites, more for small sites). (3) Limit concurrency (5-10 concurrent connections max). (4) Use exponential backoff on 429/503 responses. (5) Rotate user agents and respect `Retry-After` headers. (6) Consider time-of-day scheduling to hit sites during low-traffic periods. Document the rate-limiting strategy in the decision.

### INGEST-AP-04: Headless Browser for Static Content
**Mistake:** Uses Playwright, Puppeteer, or Selenium for pages that serve their content in the initial HTML response. Headless browsers are 10-50x slower, consume significantly more memory, and are harder to deploy than simple HTTP requests.
**Why:** Headless browser scraping is heavily represented in training data because it solves the hardest case (JavaScript-rendered content). The model defaults to the tool that handles the most complex scenario rather than matching the tool to the actual page type.
**Example:**
```
INGEST-05: Scraping Engine
Use Playwright for all scraping tasks. Launch a headless Chromium instance,
navigate to each page, wait for content to load, then extract the HTML.
This handles both static and dynamic content uniformly.
```
**Instead:** Profile each target page first: (1) Fetch with a simple HTTP GET and check if the needed data is in the HTML response. If yes, use `httpx` + `BeautifulSoup`/`selectolax`. (2) Only use a headless browser for pages where content is rendered client-side by JavaScript (SPAs, infinite scroll, lazy-loaded data). (3) Before reaching for a browser, check if the page's JS fetches data from an API endpoint — intercepting that API directly is faster than rendering the page.

### INGEST-AP-05: No Retry with Backoff
**Mistake:** Treats the first request failure as a permanent error. A single timeout, 503, or connection reset aborts the entire scraping task for that URL. No retry logic, no backoff, no distinction between transient and permanent failures.
**Why:** Training data code examples typically show the "happy path." Error handling in scraping tutorials is often limited to a try/except that logs and continues. The model generates optimistic code because that is what it has seen most.
**Example:**
```
INGEST-06: Error Handling
try:
    response = requests.get(url, timeout=10)
    return parse(response.text)
except Exception:
    logger.error(f"Failed to scrape {url}")
    return None
```
**Instead:** Implement tiered retry with exponential backoff and jitter: retry transient errors (429, 500, 502, 503, 504, timeouts, connection resets) up to 3-5 times with increasing delays (1s, 2s, 4s + random jitter). Do NOT retry permanent errors (404, 403, 410). Use a library like `tenacity` or `stamina` for retry logic. Log each retry attempt with the error type. After max retries, move the URL to a dead-letter queue for manual review rather than silently dropping it.

---

## B. Legal & Ethics

### INGEST-AP-06: robots.txt Ignored
**Mistake:** Scrapes pages without checking or respecting the site's robots.txt directives. While robots.txt is not legally binding in all jurisdictions, ignoring it signals bad faith and weakens any legal defense if challenged.
**Why:** robots.txt compliance is a legal/ethical concern that exists outside the technical scraping domain. The model focuses on "how to get the data" rather than "whether you should get the data." Training data scraping tutorials often omit robots.txt checks entirely.
**Example:**
```
INGEST-07: Target Pages
Scrape all product pages by crawling from the sitemap:
sitemap_url = "https://example.com/sitemap.xml"
# Parse sitemap, extract all URLs, scrape each one
```
**Instead:** Before any scraping: (1) Fetch and parse `robots.txt`. (2) Check if your user-agent is disallowed from the target paths. (3) Respect `Crawl-delay` directives. (4) Use a library like `robotexclusionrulesparser` for compliant parsing. (5) Document the robots.txt analysis in the decision: "robots.txt allows /products/ for all user-agents, disallows /admin/ and /api/. Crawl-delay: 2 seconds. Our scraper complies with all directives."

### INGEST-AP-07: Assuming Public Means Scrapeable
**Mistake:** Declares "the data is publicly accessible, so we can scrape it" without legal analysis. Publicly visible data is not the same as legally scrapeable data. Multiple court cases have established limits on scraping public data.
**Why:** The model conflates technical accessibility with legal permission. This is a common human misconception amplified in training data. Blog posts titled "how to scrape public data" reinforce the assumption. The nuance of hiQ v. LinkedIn (2022 reversal), Meta v. Bright Data, and GDPR applicability to public data is underrepresented.
**Example:**
```
INGEST-08: Legal Assessment
The target data is publicly accessible on the web without authentication.
No legal concerns — public data can be freely collected and used.
```
**Instead:** Legal analysis must consider: (1) Terms of Service — does the site prohibit automated access? (2) Jurisdiction — CFAA (US), Computer Misuse Act (UK), GDPR (EU) all have different standards. (3) Data type — personal data has stricter protections even when public. (4) Purpose — commercial use of scraped data faces more scrutiny. (5) Volume — scraping at scale may constitute an "unfair burden" on the server. Flag this as a cross-domain gap for the legal specialist: `GAP-NN [LEGAL] (from: scraping)`.

### INGEST-AP-08: No ToS Review
**Mistake:** Scrapes a website without reading its Terms of Service. Many sites explicitly prohibit automated access, scraping, or data collection in their ToS. Violating ToS can create breach-of-contract liability.
**Why:** Terms of Service are legal documents that exist outside the technical domain. The model has no mechanism to check or interpret ToS for a specific website. It treats scraping as a purely technical problem without a legal gate.
**Example:**
```
INGEST-09: Data Source Approval
Approved data sources: LinkedIn profiles, Twitter posts, Glassdoor reviews.
All are publicly accessible and can be scraped for our dataset.
```
**Instead:** For each scraping target: (1) Read the ToS and identify clauses about automated access, data collection, and commercial use. (2) Document relevant ToS clauses in the decision. (3) Assess risk: "LinkedIn ToS Section 8.2 explicitly prohibits scraping. Risk: HIGH — LinkedIn actively litigates. Recommendation: use the official API or find an alternative data source." (4) If ToS prohibits scraping but the data is needed, escalate to legal specialist — do not make the call unilaterally.

### INGEST-AP-09: Personal Data Scraped Without GDPR Analysis
**Mistake:** Scrapes profiles, names, email addresses, or other personal data without considering data protection regulations. GDPR applies to personal data even when it is publicly available on the internet.
**Why:** The model treats all data as equivalent. It does not distinguish between product prices (non-personal) and user profiles (personal data). GDPR's applicability to public personal data is a legal nuance that is underrepresented in technical training data.
**Example:**
```
INGEST-10: User Data Collection
Scrape public GitHub profiles to build a developer directory: username,
real name, email, location, company, and bio. Store in our database
for the recruiter search feature.
```
**Instead:** When scraping involves personal data: (1) Identify the GDPR legal basis — consent is impractical for scraping, legitimate interest requires a balancing test. (2) Conduct a Data Protection Impact Assessment (DPIA) if processing is large-scale. (3) Consider data minimization — do you need all these fields? (4) Plan for data subject rights — how will you handle deletion requests? (5) Cross-reference with the legal specialist: `GAP-NN [LEGAL] (from: scraping) — personal data scraping needs GDPR analysis`. Never decide "GDPR doesn't apply" within the scraping specialist.

---

## C. Data Quality & Operations

### INGEST-AP-10: No Schema Validation
**Mistake:** Trusts scraped data without validating structure, types, or completeness. Missing fields, changed formats, and encoding issues silently corrupt downstream databases and analytics.
**Why:** Scraping tutorials focus on extraction, not validation. The model generates code that parses and stores, skipping the validation step because it is not part of the "get the data" narrative. The implicit assumption is that if the parser runs without errors, the data is correct.
**Example:**
```
INGEST-11: Data Pipeline
def scrape_product(url):
    soup = BeautifulSoup(requests.get(url).text, "html.parser")
    return {
        "name": soup.select_one(".product-name").text,
        "price": soup.select_one(".price").text,
        "rating": soup.select_one(".rating").text,
    }
# Insert directly into database
db.products.insert_one(scrape_product(url))
```
**Instead:** Validate every scraped record against a Pydantic model or schema: required fields must be present, prices must be numeric and positive, ratings must be within 1-5, dates must parse to valid datetimes. Reject records that fail validation and route them to a quarantine queue for investigation. Track validation failure rates — a sudden spike indicates a site layout change. Log the raw HTML alongside parsed data for debugging failed extractions.

### INGEST-AP-11: No Freshness Strategy
**Mistake:** Scrapes data once and uses it indefinitely. No scheduled re-scraping, no change detection, no staleness indicators. Users see outdated prices, discontinued products, or dead links.
**Why:** Scraping is framed as a one-time data collection task in training data. The model solves "how to scrape this data" without considering "how to keep this data current." Ongoing operational concerns are outside the typical scraping tutorial scope.
**Example:**
```
INGEST-12: Data Refresh
Run the scraper during initial setup to populate the database.
Data will be available for the application immediately after scraping.
```
**Instead:** Define a freshness strategy per data type: (1) Prices and availability: re-scrape daily or on-demand with cache. (2) Product details and descriptions: re-scrape weekly. (3) Reviews and ratings: re-scrape every 2-3 days. (4) Historical data (company info, regulations): re-scrape monthly. Add a `last_scraped_at` timestamp to every record. Display staleness indicators in the UI when data exceeds its freshness threshold. Monitor for sources that have gone offline or changed structure.

### INGEST-AP-12: Schema Drift Not Detected
**Mistake:** Scraper runs on a schedule without monitoring whether the target site's structure has changed. The site redesigns, the scraper silently extracts garbage data or returns empty fields, and nobody notices until a user reports wrong data.
**Why:** Schema drift monitoring is an operational concern that goes beyond the initial scraping implementation. Training data covers "build the scraper" but not "detect when the scraper is broken." The model produces a working scraper and considers the task complete.
**Example:**
```
INGEST-13: Scheduled Scraping
Set up a cron job to run the scraper every 6 hours:
0 */6 * * * python scrape.py >> /var/log/scraper.log
```
**Instead:** Implement drift detection: (1) Track the number of successfully extracted fields per page — alert if the success rate drops below 90%. (2) Monitor the shape of extracted data — alert if field distributions change significantly (e.g., all prices suddenly null). (3) Store a hash of the page structure (tag hierarchy, key class names) and alert when it changes. (4) Run a canary test against 5-10 known URLs before each full scrape — if canaries fail, abort and alert. (5) Set up PagerDuty/Slack alerts for scraper health, not just cron logs.

### INGEST-AP-13: No Data Normalization
**Mistake:** Stores scraped data as-is with inconsistent formats across sources. Prices as "$1,299.00", "1299", "EUR 1.299,00". Dates as "Jan 5, 2025", "2025-01-05", "05/01/2025". Units as "5 kg", "5000g", "11 lbs". Downstream code must handle every variant.
**Why:** The model generates scrapers per-source that extract data in the format it appears on the page. Normalization is a cross-source concern that does not arise when building a single scraper. Training data focuses on single-source extraction, not multi-source data integration.
**Example:**
```
INGEST-14: Multi-Source Aggregation
Source A prices: "$1,299.00" (stored as string)
Source B prices: "1299 USD" (stored as string)
Source C prices: "EUR 1.299,00" (stored as string)
# Let the frontend handle display formatting
```
**Instead:** Normalize at ingestion time, not at query time: (1) Prices: parse to integer cents with a currency code (`{"amount_cents": 129900, "currency": "USD"}`). (2) Dates: parse to ISO 8601 (`2025-01-05T00:00:00Z`). (3) Units: convert to a canonical unit (grams, meters, seconds). (4) Text: normalize Unicode (NFC), strip HTML entities, standardize whitespace. (5) Define a canonical schema and reject records that cannot be normalized. Source-specific parsing lives in source adapters; the storage layer receives normalized data only.

### INGEST-AP-14: Missing Provenance Tracking
**Mistake:** Stores scraped data without recording when it was scraped, from which URL, using which scraper version, or under what conditions. When a data quality issue is reported, there is no way to trace it back to the source.
**Why:** Provenance is a metadata concern that adds storage and complexity without immediate functional benefit. The model optimizes for the data itself, not its lineage. Training data rarely includes provenance tracking in scraping examples.
**Example:**
```
INGEST-15: Data Storage
products_collection.insert_one({
    "name": product_name,
    "price": price,
    "category": category
})
```
**Instead:** Every scraped record must include provenance metadata: `{"source_url": "https://...", "scraped_at": "2025-01-05T14:30:00Z", "scraper_version": "v2.3.1", "raw_html_hash": "sha256:abc...", "extraction_confidence": 0.95}`. Store raw HTML snapshots (compressed) for high-value data to enable re-extraction when parsers improve. This enables: debugging data quality issues, compliance audits (proving when and how data was collected), reproducibility (re-running extraction on stored HTML), and freshness tracking.
