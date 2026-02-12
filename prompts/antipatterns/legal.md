# Legal — Common Mistakes & Anti-Patterns

Common mistakes when running the legal specialist. Each pattern
describes a failure mode that leads to poor compliance decisions.

**Referenced by:** `specialist_legal.md`
> These patterns are **illustrative, not exhaustive**. They are a starting
> point — identify additional project-specific anti-patterns as you work.
> When a listed pattern doesn't apply to the current project, skip it.

---

## A. Compliance

### LEGAL-AP-01: GDPR-Only Thinking
**Mistake:** Treats GDPR as the only privacy regulation that exists. The legal analysis covers GDPR requirements exhaustively but ignores CCPA/CPRA (California), LGPD (Brazil), PIPEDA (Canada), POPIA (South Africa), and sector-specific regulations like HIPAA (health data) or PCI-DSS (payment data).
**Why:** GDPR dominates LLM training data because it generated an enormous volume of compliance content after 2018. Other regulations have less written commentary in English. The model equates "privacy compliance" with "GDPR compliance" because GDPR is the regulation it has seen discussed most frequently.
**Example:**
```
LEGAL-01: Privacy Compliance
Implement GDPR compliance:
- Consent management for EU users
- Right to access and deletion
- Data Processing Agreement with sub-processors
- Privacy policy with Art. 13/14 disclosures
This covers our privacy obligations.
```
**Instead:** Map each user jurisdiction to applicable regulations: (1) EU/EEA users: GDPR. (2) California users: CCPA/CPRA (different consent model — opt-out, not opt-in). (3) Brazilian users: LGPD (similar to GDPR but with unique requirements like a DPO equivalent called "encarregado"). (4) Health data: HIPAA (US), regardless of other regulations. (5) Payment data: PCI-DSS, globally. (6) Children's data: COPPA (US, under 13). Create a jurisdiction matrix showing which regulations apply and where requirements conflict or overlap. A single "privacy compliance" decision is insufficient.

### LEGAL-AP-02: Copy-Paste Privacy Policy
**Mistake:** Generates a generic privacy policy template without mapping it to the project's actual data collection, processing, and sharing practices. The policy mentions cookies, analytics, and third-party sharing in boilerplate language that does not describe what the application actually does.
**Why:** Privacy policy generators and templates are heavily represented in training data. The model has seen thousands of privacy policies and can generate plausible-sounding text, but it lacks the connection between the policy language and the project's actual technical implementation. Generating text that "sounds like a privacy policy" is easy; generating one that is accurate requires system knowledge.
**Example:**
```
LEGAL-03: Privacy Policy
Generate a privacy policy covering:
- Information we collect
- How we use your information
- Sharing with third parties
- Your rights and choices
- Data security measures

Use standard privacy policy language.
```
**Instead:** Build the privacy policy from the project's actual data flows: (1) Enumerate every data collection point (registration form, cookies, analytics scripts, API integrations). (2) For each data point, document: what is collected, why, the legal basis (consent, legitimate interest, contractual necessity), retention period, and who has access. (3) List every third-party service that receives user data (analytics, payment processor, email provider) with their specific purposes. (4) Map user rights to implementation: "You can delete your account at Settings > Account > Delete" — not just "you have the right to deletion." The policy must be a factual description of the system, not a legal template.

### LEGAL-AP-03: DPO Threshold Confusion
**Mistake:** States that a Data Protection Officer is "not required for companies with fewer than 250 employees." The 250-employee threshold in GDPR Article 30 applies to record-keeping obligations, not DPO appointment. DPO requirements under Article 37 depend on core activities involving large-scale monitoring or special category data.
**Why:** The 250-employee threshold is a commonly misquoted GDPR fact in blog posts and compliance guides. The model has absorbed this misconception from training data. The actual DPO requirement (Art. 37) is nuanced and less frequently explained correctly in popular content.
**Example:**
```
LEGAL-04: Data Protection Officer
DPO appointment is not required. Our organization has fewer than 250
employees, which exempts us from the DPO requirement under GDPR.
```
**Instead:** Assess DPO requirement against GDPR Article 37 criteria: (1) Is the controller a public authority? (2) Do core activities require regular and systematic monitoring of data subjects on a large scale? (3) Do core activities involve large-scale processing of special categories of data (health, biometric, racial/ethnic origin) or criminal conviction data? If ANY of these apply, a DPO is required regardless of company size. A 10-person health-tech startup processing patient records needs a DPO. A 500-person company with no systematic user monitoring may not. Cite Art. 37, not Art. 30.

### LEGAL-AP-04: Cookie Consent as Checkbox
**Mistake:** Treats cookie consent as a simple "Accept All" banner without categorizing cookies or providing granular control. A single "I accept cookies" button does not meet ePrivacy Directive or GDPR requirements for informed, specific consent.
**Why:** Simple cookie banners are ubiquitous on the web, and the model has seen more bad implementations than good ones. The compliant cookie consent UX (categorized, granular, with a real "reject" option) is less common in training data than the non-compliant "accept all" banner.
**Example:**
```
LEGAL-05: Cookie Compliance
Add a cookie consent banner at the bottom of the page:
"This site uses cookies. By continuing to use this site, you accept
our use of cookies. [OK]"
```
**Instead:** Implement compliant cookie consent: (1) Categorize cookies: strictly necessary (no consent needed), analytics/performance, functionality, and marketing/advertising. (2) Present each category with a clear description and a toggle — default OFF for non-essential categories. (3) Provide a "Reject All" button with equal prominence to "Accept All." (4) Do NOT load non-essential cookies until consent is given (consent must be prior, not retroactive). (5) Store consent records with timestamp and categories accepted. (6) Provide a way to withdraw consent at any time. Reference a Consent Management Platform (OneTrust, Cookiebot) rather than building from scratch.

### LEGAL-AP-05: Consent as Legal Basis Default
**Mistake:** Uses consent as the GDPR legal basis for every data processing activity. Consent is the most restrictive basis — it must be freely given, specific, informed, and withdrawable at any time. Using it when other bases apply creates unnecessary compliance burden.
**Why:** Consent is the most intuitive and most frequently discussed GDPR legal basis. It appears in virtually every GDPR explainer article. The model defaults to consent because it is the basis it has seen most often, not because it has analyzed which basis fits each processing activity.
**Example:**
```
LEGAL-06: Legal Basis
Use consent (Art. 6(1)(a)) as the legal basis for all data processing:
- Account creation: consent
- Order processing: consent
- Email notifications: consent
- Fraud detection: consent
- Legal compliance reporting: consent
```
**Instead:** Match legal basis to processing purpose: (1) Account creation and order processing: contractual necessity (Art. 6(1)(b)) — you need the data to fulfill the contract the user entered. (2) Fraud detection: legitimate interest (Art. 6(1)(f)) — you have a legitimate interest in preventing fraud, and users would reasonably expect it. (3) Tax record retention: legal obligation (Art. 6(1)(c)) — you are legally required to keep these records. (4) Marketing emails: consent (Art. 6(1)(a)) — this is genuinely optional and consent is appropriate. Using the correct basis reduces UX friction (fewer consent prompts) and legal risk (consent withdrawal cannot destroy your ability to process orders).

---

## B. Contracts & IP

### LEGAL-AP-06: Open-Source License Blindness
**Mistake:** Uses open-source dependencies without checking their license compatibility. Includes AGPL or GPL-licensed libraries in a proprietary SaaS product without understanding viral licensing (copyleft) implications that may require open-sourcing the application code.
**Why:** Developers treat `npm install` and `pip install` as permission to use. Training data rarely discusses license compatibility because it is a legal concern, not a technical one. The model lists dependencies by functionality without checking their licenses.
**Example:**
```
LEGAL-07: Dependency Audit
Dependencies reviewed for security vulnerabilities and version compatibility.
All packages are up to date and free of known CVEs. No legal issues identified.
```
(dependency list includes an AGPL-licensed PDF library used server-side in a proprietary SaaS)
**Instead:** Audit every dependency's license: (1) Categorize licenses: permissive (MIT, BSD, Apache 2.0 — safe for proprietary use), weak copyleft (LGPL — safe if dynamically linked), strong copyleft (GPL, AGPL — viral, may require open-sourcing your code). (2) AGPL is especially dangerous for SaaS because it triggers copyleft through network interaction, not just distribution. (3) Create an allowlist of approved licenses. (4) Use automated tools (`license-checker`, `pip-licenses`, `fossa`) in CI to flag new dependencies with non-approved licenses. (5) For each copyleft dependency, evaluate: can it be replaced with a permissive alternative? If not, what are the specific obligations?

### LEGAL-AP-07: No CLA/DCO for Contributions
**Mistake:** Accepts external code contributions to the project without a Contributor License Agreement (CLA) or Developer Certificate of Origin (DCO). When external developers contribute code, IP ownership is ambiguous — the contributor may retain copyright, creating legal risk for the project.
**Why:** Open-source contribution workflows focus on git mechanics (fork, PR, merge), not legal mechanics. The model generates contribution guides that cover code style and review process but omit IP assignment. CLA/DCO is a legal process that exists outside the typical developer workflow in training data.
**Example:**
```
LEGAL-08: Contribution Guidelines
Contributing:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request
4. Maintain code style and add tests
```
**Instead:** Establish IP clarity for contributions: (1) For corporate-owned projects: require a CLA (Contributor License Agreement) that grants the project owner a license to use, modify, and relicense the contributed code. Use a CLA bot (cla-assistant) to automate signing. (2) For community projects: use DCO (Developer Certificate of Origin) — contributors sign off commits with `Signed-off-by:` to certify they have the right to contribute the code. (3) Document the requirement in CONTRIBUTING.md. (4) Configure CI to block merges without CLA/DCO signature. Choose CLA vs DCO based on the project's ownership model and relicensing needs.

### LEGAL-AP-08: Terms of Service as Afterthought
**Mistake:** Ships the product and writes Terms of Service later. Limitation of liability, dispute resolution, acceptable use policies, content ownership, and account termination rules should be defined before users interact with the product, not retroactively.
**Why:** ToS is a legal document that feels disconnected from the product development process. Training data focuses on building features, not on the legal wrapper around them. The model treats ToS as a documentation task to be done "when we launch" rather than a design constraint that affects feature decisions.
**Example:**
```
LEGAL-09: Launch Checklist
- [x] Core features implemented
- [x] Performance testing complete
- [x] Security audit passed
- [ ] Write Terms of Service (post-launch)
- [ ] Write Privacy Policy (post-launch)
```
**Instead:** Draft ToS before the first user interacts with the product: (1) Limitation of liability — caps on damages, disclaimer of warranties, force majeure. (2) Acceptable use policy — what users cannot do (abuse, illegal content, scraping). (3) Content ownership — who owns user-generated content, what license does the platform have. (4) Account termination — under what conditions accounts are suspended or deleted. (5) Dispute resolution — jurisdiction, arbitration clause, class action waiver (if applicable). (6) ToS affects feature decisions: if the ToS prohibits certain content, the product needs content moderation. Ship ToS on day one with user acceptance required at signup.

### LEGAL-AP-09: Ignoring AI-Specific Regulations
**Mistake:** Deploys AI features without considering the EU AI Act, state-level AI regulations (Colorado AI Act, NYC Local Law 144), or sector-specific AI guidance. Treats AI compliance as a future concern rather than a current design constraint.
**Why:** AI regulation is rapidly evolving and the model's training data contains incomplete or outdated information. The EU AI Act was finalized in 2024 with phased enforcement through 2027. The model may have pre-enforcement training data that treats AI regulation as speculative rather than enacted law.
**Example:**
```
LEGAL-10: AI Compliance
Our AI features use LLMs for content generation and recommendation.
No specific AI regulations apply at this time. We will monitor
the regulatory landscape and adapt as needed.
```
**Instead:** Conduct an AI-specific regulatory assessment: (1) EU AI Act: classify each AI feature by risk level (unacceptable, high, limited, minimal). High-risk AI (hiring, credit, healthcare) requires conformity assessments, transparency, and human oversight. (2) NYC LL144: automated employment decision tools require annual bias audits. (3) Colorado AI Act: deployers of high-risk AI systems have disclosure and impact assessment obligations. (4) Sector-specific: FDA guidance for AI/ML in medical devices, SEC guidance for AI in financial services. (5) Transparency: users must be informed when they are interacting with AI, when AI makes decisions about them, and what data the AI uses. Create a risk classification matrix for each AI feature.

---

## C. Implementation

### LEGAL-AP-10: Legal Requirements Without Implementation Path
**Mistake:** States legal requirements ("must comply with GDPR," "implement right to deletion") without specifying which technical controls, data flows, or processes satisfy each requirement. Legal decisions without implementation guidance become aspirational, not actionable.
**Why:** The model generates legal analysis from legal training data, which discusses requirements in legal language, not technical language. Bridging "Article 17 right to erasure" to "DELETE FROM users WHERE id = ? plus purge from Elasticsearch, Redis cache, S3 backups, and Stripe" requires cross-domain knowledge that is split across legal and technical training data.
**Example:**
```
LEGAL-11: GDPR Implementation
- Implement right to access (Art. 15)
- Implement right to rectification (Art. 16)
- Implement right to erasure (Art. 17)
- Implement data portability (Art. 20)
- Maintain records of processing (Art. 30)
```
**Instead:** Map each legal requirement to a concrete technical implementation: (1) Right to access: build an export endpoint that collects all user data from PostgreSQL (users, orders, preferences), Elasticsearch (search history), Redis (session data), and third-party services (Stripe customer record) into a downloadable JSON/CSV file. (2) Right to erasure: build a deletion pipeline that cascades through all data stores, queues backup purge (within 30-day backup retention), notifies sub-processors (Stripe, analytics), and logs the erasure completion for compliance records. (3) For each right, specify: which systems are affected, which API endpoints implement it, what the user-facing flow is, and how compliance is verified.

### LEGAL-AP-11: Data Retention as Infinite
**Mistake:** No retention policy defined. Data accumulates forever, increasing storage costs, data breach surface area, and compliance obligations. GDPR requires that data be kept only as long as necessary for the purpose it was collected.
**Why:** Retention limits are a legal constraint that runs counter to the engineering instinct to keep all data (it might be useful later). Training data focuses on collecting and processing data, not on deleting it. The concept of mandatory data deletion is underrepresented in technical training data.
**Example:**
```
LEGAL-12: Data Storage
Store all user data in PostgreSQL. Maintain complete transaction history
and interaction logs for analytics and potential future use cases.
```
**Instead:** Define retention periods per data category: (1) Account data: retained while account is active + 30 days after deletion. (2) Transaction records: retained for 7 years (tax law requirement — cite the specific statute). (3) Support tickets: retained for 2 years after resolution. (4) Access logs: retained for 90 days. (5) Analytics data: anonymized after 26 months (Google Analytics default aligns). Implement automated deletion: scheduled jobs that purge data past its retention period. Implement anonymization as an alternative to deletion where aggregate data is needed. Document the legal basis for each retention period.

### LEGAL-AP-12: Right-to-Deletion Theater
**Mistake:** Implements user account deletion by soft-deleting the primary database record while leaving user data in backups, analytics systems, search indexes, caches, third-party services, and audit logs. The user thinks their data is deleted, but it persists in 6+ systems.
**Why:** The model implements deletion as a database operation because that is the technical pattern for "delete." GDPR's comprehensive deletion requirement spans all data stores, including systems the model may not consider part of the "user data" (backups, analytics, CDN caches). Training data treats deletion as a single operation, not a multi-system cascade.
**Example:**
```
LEGAL-13: Account Deletion
def delete_account(user_id: int):
    user = db.query(User).get(user_id)
    user.is_deleted = True
    user.email = f"deleted_{user_id}@placeholder.com"
    db.commit()
```
**Instead:** Build a comprehensive deletion pipeline: (1) Primary database: hard-delete user record and all associated data (orders, preferences, messages). (2) Search indexes: remove user documents from Elasticsearch/Algolia. (3) Caches: invalidate Redis/Memcached entries containing user data. (4) File storage: delete S3/GCS objects (profile photos, uploaded documents). (5) Third-party services: trigger deletion via Stripe API, remove from email marketing (Mailchimp/SendGrid), purge from analytics (Mixpanel/Amplitude). (6) Backups: implement backup rotation that ensures deleted user data is purged within a defined window (30 days is common). (7) Audit log: retain a minimal deletion record (user_id, deletion_date, deletion_completed_at) for compliance proof without retaining personal data.

### LEGAL-AP-13: Cross-Border Transfer Ignored
**Mistake:** Stores EU user data on US servers or uses US-based sub-processors (AWS US-East, Google Cloud US) without establishing a valid legal mechanism for the data transfer. Post-Schrems II (2020), EU-US data transfers require specific safeguards.
**Why:** Cloud infrastructure is global and developers deploy to regions based on latency and cost, not legal geography. Training data treats server region as a performance decision, not a compliance one. The model defaults to US regions because US-based training data defaults to US infrastructure.
**Example:**
```
LEGAL-14: Infrastructure
Deploy to AWS us-east-1 for best latency and lowest cost.
All user data stored in RDS (PostgreSQL) in us-east-1.
EU users will be served from the same region with CloudFront CDN.
```
**Instead:** Map data flows against cross-border transfer rules: (1) EU user data stored in EU: no transfer issue — use eu-west-1 or eu-central-1. (2) EU user data accessed from US: requires a transfer mechanism — EU-US Data Privacy Framework (if certified), Standard Contractual Clauses (SCCs), or Binding Corporate Rules (BCRs). (3) Sub-processor transfers: verify each third-party service's data transfer compliance (Stripe, SendGrid, Mixpanel all process user data — where?). (4) Document the transfer mechanism for each data flow in the data processing register. (5) If using DPF, verify the recipient's certification is current. If using SCCs, ensure supplementary measures (encryption, pseudonymization) are implemented per EDPB guidance.

### LEGAL-AP-14: Disclaimer Overload
**Mistake:** Adds disclaimers to every page, feature, and interaction as a blanket legal shield. "This is not financial advice," "results may vary," "we are not responsible for..." on every screen. Excessive disclaimers are often unenforceable, erode user trust, and create a negative user experience.
**Why:** The model generates disclaimers as a risk-mitigation pattern. In training data, legal advice often recommends "add a disclaimer" as a generic protective measure. The model applies this pattern broadly without considering enforceability, user experience impact, or legal effectiveness.
**Example:**
```
LEGAL-15: Risk Mitigation
Add disclaimers to all AI-generated content:
"DISCLAIMER: This content is generated by AI and may contain errors.
[Company] makes no warranties regarding accuracy, completeness, or
reliability. Use at your own risk. This is not professional advice.
Always consult a qualified professional. [Company] assumes no liability
for decisions made based on this content."
```
(this disclaimer is shown after every AI response, including "here's a recipe for pasta")
**Instead:** Use targeted, proportionate disclaimers: (1) High-risk contexts (medical, financial, legal): clear, specific disclaimers at the feature entry point, not on every output. "This tool provides general information, not medical advice. Consult your doctor for personal health decisions." (2) Low-risk contexts (recipes, general knowledge): no disclaimer needed — over-disclaiming signals distrust in your own product. (3) AI transparency: a single, clear disclosure that the feature is AI-powered, placed at the feature level, not repeated on every output. (4) Terms of Service: put comprehensive liability limitations in the ToS (where they are legally effective), not inline as user-facing disclaimers (where they are often ignored and unenforceable).
