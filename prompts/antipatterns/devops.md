# DevOps — Common Mistakes & Anti-Patterns

Common mistakes when running the devops specialist. Each pattern
describes a failure mode that leads to poor infrastructure decisions.

**Referenced by:** `specialist_devops.md`
> These patterns are **illustrative, not exhaustive**. They are a starting
> point — identify additional project-specific anti-patterns as you work.
> When a listed pattern doesn't apply to the current project, skip it.

---

## A. Infrastructure

### OPS-AP-01: Kubernetes for 50 users
**Mistake:** Recommends Kubernetes for a project that serves a handful of users and runs a single service. K8s introduces manifests, Helm charts, ingress controllers, node pools, and persistent volume claims — none of which are needed when a single $5/month VPS or a PaaS deploy would suffice.
**Why:** Kubernetes dominates DevOps training data. Blog posts, tutorials, and conference talks disproportionately cover K8s because it solves hard problems at scale. The model defaults to the most-discussed tool rather than the simplest adequate tool.
**Example:**
```
OPS-03: Deploy application to Kubernetes (EKS)
  - Create EKS cluster with 3 worker nodes (t3.medium)
  - Configure Helm charts for application deployment
  - Set up nginx-ingress controller for routing
  - Configure horizontal pod autoscaler
  - Estimated cost: $150-300/month
```
(The app is a side project with 20 users. A $7/month Railway or Fly.io deployment does the same job with zero operational overhead.)
**Instead:** Match infrastructure to actual load. Under 1,000 users with a single service: PaaS (Railway, Fly.io, Render) or a single VPS. 1,000-50,000 users with 2-5 services: container orchestration becomes worth considering. Over 50,000 users with microservices: Kubernetes or equivalent earns its complexity. Include the cost comparison in the decision.

### OPS-AP-02: Docker by default
**Mistake:** Containerizes every project with a multi-stage Dockerfile, docker-compose for local dev, and container registry setup — even when the project deploys to a PaaS that manages the runtime natively.
**Why:** "Containerize everything" is a DevOps best practice that appears constantly in training data. The model does not evaluate whether the deployment target actually benefits from containers.
**Example:**
```
OPS-05: Containerize application
  - Multi-stage Dockerfile (build + production)
  - docker-compose.yml for local development
  - Push to ECR for production deployment

# Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
COPY --from=builder /app/dist ./dist
CMD ["node", "dist/index.js"]
```
(The project deploys to Vercel, which builds from source and manages the runtime. The Dockerfile adds maintenance burden with zero value.)
**Instead:** Evaluate the deployment target first. PaaS with buildpack support (Vercel, Netlify, Railway, Heroku): no Dockerfile needed — the platform handles it. PaaS with container support (Fly.io, Google Cloud Run): Dockerfile is the deployment unit, so it adds value. Self-hosted or IaaS: Docker provides reproducibility, go ahead. Only containerize when the container solves a real problem (environment parity, deployment artifact, dependency isolation).

### OPS-AP-03: Over-provisioning
**Mistake:** Recommends 4 vCPU / 16GB RAM instances "for headroom" when the application processes 100 requests per minute and uses 200MB of RAM. Wastes money and creates a false impression of the app's resource needs.
**Why:** LLMs lack feedback on cost. The model never receives the AWS bill. Recommending larger instances feels "safer" and avoids the hypothetical embarrassment of under-provisioning. Real-world right-sizing requires monitoring data the model does not have.
**Example:**
```
OPS-07: Production instance: t3.xlarge (4 vCPU, 16GB RAM)
  - Provides headroom for traffic spikes
  - Database: db.r6g.large (2 vCPU, 16GB RAM)
  - Redis: cache.r6g.large (2 vCPU, 16GB RAM)
  - Estimated cost: $450/month
```
(The app has 50 daily users. A t3.micro with 1GB RAM would serve this load comfortably. The database could be a managed free tier.)
**Instead:** Start with the smallest instance that runs the application (t3.micro or t3.small). Set up basic monitoring (CPU, memory, response time). Right-size based on actual metrics after 2-4 weeks. Include auto-scaling rules for unexpected spikes rather than permanent over-provisioning. Document the scaling triggers: "Scale up when CPU > 70% sustained for 5 minutes."

### OPS-AP-04: Multi-region before single-region works
**Mistake:** Plans multi-region deployment with cross-region replication, global load balancing, and failover — before the application reliably serves traffic in a single region.
**Why:** Multi-region architecture is a prestigious topic in DevOps literature. The model produces impressive-sounding decisions about global availability without considering that multi-region adds data consistency challenges, deployment complexity, and cost that are irrelevant for most projects.
**Example:**
```
OPS-09: Multi-region deployment
  - Primary: us-east-1, Secondary: eu-west-1, Tertiary: ap-southeast-1
  - Aurora Global Database with cross-region read replicas
  - CloudFront for global CDN
  - Route 53 latency-based routing with health checks
  - Estimated cost: $1,200/month minimum
```
(The app has 30 users, all in one country. A single-region deployment with a CDN for static assets would provide sub-100ms response times.)
**Instead:** Deploy in one region closest to the majority of users. Add a CDN (CloudFront, Cloudflare) for static assets — this handles 90% of "global performance" needs. Plan multi-region only when: regulatory requirements mandate data residency, user base spans continents with measurable latency issues, or uptime SLA exceeds 99.9% and single-region outage is unacceptable. Document the trigger for multi-region expansion.

### OPS-AP-05: Cloud-native lock-in
**Mistake:** Builds the entire stack on provider-specific services (Lambda + DynamoDB + SQS + SNS + Step Functions + Cognito) without assessing the lock-in risk. Migration to another provider would require rewriting every component.
**Why:** Cloud-native tutorials and AWS/GCP/Azure documentation dominate DevOps training data. The model recommends the provider's native services because that is what the documentation demonstrates. Portability considerations appear in architecture discussions but rarely in DevOps-specific content.
**Example:**
```
OPS-11: Serverless architecture on AWS
  - API: Lambda + API Gateway
  - Database: DynamoDB
  - Queue: SQS
  - Auth: Cognito
  - Storage: S3
  - Orchestration: Step Functions
```
(Every component is AWS-specific. Moving to GCP or Azure requires rewriting the entire application. If AWS pricing changes or the team needs to self-host, they are trapped.)
**Instead:** Assess lock-in risk per component. High lock-in acceptable when: the service has no adequate open-source equivalent (e.g., S3 for object storage is de facto standard), or the cost/convenience benefit is overwhelming for the project's lifecycle. Prefer portable alternatives when: the project may outlive the current provider choice, or open-source equivalents exist (PostgreSQL over DynamoDB, RabbitMQ/Redis over SQS, Keycloak over Cognito). Document the lock-in decision explicitly: "DynamoDB chosen for its zero-ops scaling. Lock-in risk: HIGH. Migration path: export to PostgreSQL via DynamoDB Streams if needed."

---

## B. CI/CD

### OPS-AP-06: 30-minute CI pipeline
**Mistake:** CI pipeline runs every possible check sequentially — lint, type checking, unit tests, integration tests, E2E tests, security scan, container build, deploy preview — on every commit. Developers wait 30 minutes for feedback, so they batch commits or skip CI.
**Why:** LLMs produce comprehensive CI configurations because "more checks = more thorough." The model does not experience the developer's frustration of waiting for a 30-minute pipeline to tell them they have a lint error on line 7.
**Example:**
```yaml
# .github/workflows/ci.yml
jobs:
  ci:
    steps:
      - run: npm run lint          # 2 min
      - run: npm run typecheck     # 3 min
      - run: npm run test:unit     # 5 min
      - run: npm run test:integration  # 8 min
      - run: npm run test:e2e      # 10 min
      - run: npm run security:scan # 3 min
      - run: docker build .        # 5 min
      - run: npm run deploy:preview # 4 min
```
(Total: ~40 minutes sequential. Lint failure is not discovered until minute 2.)
**Instead:** Parallelize independent stages. Fast feedback first: lint + typecheck in parallel (fail fast, under 3 minutes). Then unit tests. Integration and E2E tests run in parallel with each other. Container build only on main branch. Deploy preview only on PRs. Target: developer gets lint/type feedback in under 3 minutes, full pipeline completes in under 10 minutes.

### OPS-AP-07: No rollback strategy
**Mistake:** Defines the deployment pipeline (build, test, deploy) but not the rollback procedure. "Redeploy the previous version" is not a strategy if there is no documented way to identify which version was previous, how to trigger the rollback, or how to verify it succeeded.
**Why:** Deployment pipelines are heavily documented in CI/CD tutorials. Rollback procedures are project-specific and less glamorous, so they appear far less frequently in training data.
**Example:**
```
OPS-15: Deployment pipeline
  1. Push to main triggers CI
  2. Tests pass → build Docker image
  3. Push image to ECR
  4. Update ECS task definition
  5. ECS deploys new version

Rollback: Redeploy previous version if issues detected.
```
(How is "issues detected"? Who detects them — a human checking the dashboard, an automated health check, an alert? Which "previous version" — the Git SHA, the Docker tag, the ECS task revision? How long does rollback take?)
**Instead:** Define rollback concretely: "Rollback trigger: automated (health check fails 3 consecutive times within 5 minutes of deploy) or manual (engineer runs `./scripts/rollback.sh`). Rollback target: previous ECS task definition revision (tracked in deploy log at `s3://deploys/log.json`). Rollback time: under 2 minutes (ECS service update). Verification: health check passes for 5 minutes post-rollback. Post-incident: deploy is blocked until root cause is identified and fixed."

### OPS-AP-08: Trunk-based for solo developer
**Mistake:** Recommends GitFlow (develop, feature branches, release branches, hotfix branches) or another elaborate branching strategy for a team of 1-2 developers.
**Why:** GitFlow is heavily documented and appears authoritative. LLMs reproduce it because it is the most-described branching model. The model does not adapt the recommendation to team size.
**Example:**
```
OPS-17: Git branching strategy (GitFlow)
  - main: production releases only
  - develop: integration branch
  - feature/*: individual features
  - release/*: release candidates
  - hotfix/*: production fixes
  - Naming: feature/TICKET-123-description
```
(Solo developer creates a feature branch, opens a PR to develop, merges to develop, creates a release branch, merges to main. For one person, this is pure ceremony.)
**Instead:** Scale branching to team size. Solo developer: commit to main with CI checks, or simple feature branches merged directly to main. 2-5 developers: feature branches + PR reviews + merge to main. 5+ developers: trunk-based development with short-lived feature branches, or GitHub Flow. GitFlow only if you maintain multiple release versions simultaneously.

### OPS-AP-09: Deploying everything on every change
**Mistake:** The CI/CD pipeline triggers a full build, test, and deploy cycle for every commit regardless of what changed. A README typo fix triggers the entire E2E test suite and a production deployment.
**Why:** Simple CI configurations trigger on all pushes to all branches. Path-based filtering is a CI-specific feature that does not appear in basic tutorials.
**Example:**
```yaml
on:
  push:
    branches: [main]

jobs:
  deploy:
    steps:
      - run: npm ci
      - run: npm test
      - run: npm run build
      - run: npm run deploy
```
(Changing `docs/README.md` triggers a full deploy.)
**Instead:** Scope CI triggers to relevant paths: "Application deploy triggers on changes to `src/`, `package.json`, `package-lock.json`. Documentation pipeline triggers on `docs/`. Infrastructure pipeline triggers on `terraform/` or `infra/`. Lint/format runs on all file changes but does not trigger deploy." Use `paths` and `paths-ignore` filters in GitHub Actions (or equivalent in other CI systems).

---

## C. Monitoring & Operations

### OPS-AP-10: Log everything strategy
**Mistake:** Logs every request body, response body, header, and query parameter at INFO level. At any meaningful scale, this produces millions of log entries per day, costs hundreds of dollars in log storage, and makes finding actual issues harder because signal drowns in noise.
**Why:** "Log everything for debugging" sounds prudent. LLMs optimize for thoroughness and cannot experience the pain of searching through 50 million log entries for one error. The model has no feedback mechanism for log volume or storage cost.
**Example:**
```python
@app.middleware("http")
async def log_everything(request, call_next):
    body = await request.body()
    logger.info(f"REQUEST: {request.method} {request.url} "
                f"headers={dict(request.headers)} body={body}")
    response = await call_next(request)
    logger.info(f"RESPONSE: {response.status_code} body={response.body}")
    return response
```
(At 1,000 req/s this generates ~86 million log entries per day. CloudWatch cost: ~$1,500/month just for ingestion.)
**Instead:** Define a logging strategy by level: ERROR — exceptions, failed operations (always logged with stack trace). WARN — degraded performance, retry attempts, approaching limits. INFO — request summary (method, path, status, duration) without bodies. DEBUG — detailed payloads, only enabled per-request via header flag or for specific endpoints during active debugging. Set retention policies: ERROR logs kept 90 days, INFO logs kept 14 days, DEBUG logs kept 3 days.

### OPS-AP-11: Alert fatigue
**Mistake:** Configures 50+ alerts on day one covering every metric: CPU, memory, disk, network, request latency p50/p90/p99, error rate, queue depth, cache hit rate, database connections, etc. The team ignores all alerts within a week because most fire on normal traffic patterns.
**Why:** LLMs produce comprehensive alert configurations because completeness scores well. The model cannot model the human experience of receiving 20 alerts at 3 AM because CPU briefly touched 80% during a scheduled batch job.
**Example:**
```
Alerts configured:
  - CPU > 70% for 5 minutes
  - Memory > 60% for 5 minutes
  - Disk > 50% for any duration
  - Response time p50 > 200ms
  - Response time p90 > 500ms
  - Response time p99 > 1000ms
  - Error rate > 0.1%
  - Database connections > 10
  - Cache miss rate > 20%
  ... (40 more alerts)
```
(Every threshold is set without baseline data. The team receives 15 alerts on a normal Monday and starts ignoring them.)
**Instead:** Start with 3-5 critical alerts that indicate genuine user impact: "Error rate > 5% sustained for 5 minutes (users are seeing errors). Response time p95 > 3s sustained for 10 minutes (users are waiting). Health check fails 3 consecutive times (service is down). Disk > 90% (service will crash soon). Certificate expires within 14 days." Run for 2 weeks to establish baselines, then add specific alerts based on actual operational patterns. Every alert must have a documented response procedure.

### OPS-AP-12: Monitoring the monitoring
**Mistake:** Proposes a full observability stack — Prometheus + Grafana + Loki + Tempo + Jaeger + AlertManager — for a single-service application that could be monitored with the deployment platform's built-in metrics.
**Why:** Observability is a hot topic with extensive documentation for each tool. LLMs assemble the "full stack" because each tool appears in best-practice guides. The model does not consider the operational cost of running and maintaining 5+ monitoring services.
**Example:**
```
OPS-25: Observability stack
  - Metrics: Prometheus + Grafana
  - Logs: Loki
  - Traces: Tempo + Jaeger
  - Alerts: AlertManager + PagerDuty
  - Dashboards: 12 pre-built Grafana dashboards
```
(The monitoring stack requires more infrastructure than the application itself. A single-service app does not need distributed tracing.)
**Instead:** Start with what the platform provides. Vercel/Railway/Fly.io: built-in metrics, logs, and health checks cover most needs. AWS/GCP: CloudWatch/Cloud Monitoring with basic dashboards. Add dedicated observability tools only when: you have multiple services that need correlated traces, built-in monitoring lacks a specific capability you need, or you are debugging a performance issue that requires detailed profiling. One tool at a time, driven by a specific operational need.

### OPS-AP-13: No secret rotation plan
**Mistake:** Defines how secrets are stored (secrets manager, environment variables) but not how they are rotated. API keys, database passwords, and TLS certificates all expire or can be compromised, but the rotation procedure is undefined.
**Why:** Secret storage is a well-documented topic. Secret rotation is an operational process that varies per secret type and infrastructure, making it less common in training data.
**Example:**
```
OPS-27: Secrets management
  - Store all secrets in AWS Secrets Manager
  - Access via IAM roles, no hardcoded credentials
  - Secrets referenced in ECS task definitions
```
(What happens in 90 days when the API key expires? What happens when a developer's laptop is stolen and they had local `.env` access? How is the database password rotated without downtime?)
**Instead:** Define rotation per secret type: "Database password: rotated every 90 days via AWS Secrets Manager automatic rotation (Lambda function swaps credentials, application reads new value on next connection pool refresh). API keys (third-party): calendar reminder at 80% of expiration, manual rotation with overlap period (old key valid for 24 hours after new key is active). TLS certificates: auto-renewed via Let's Encrypt 30 days before expiration. Incident response: if any secret is suspected compromised, rotate immediately, audit access logs for the exposure window, and notify affected parties."

### OPS-AP-14: Missing disaster recovery plan
**Mistake:** Production database has no backup strategy, no tested restore procedure, and no defined RTO (Recovery Time Objective) or RPO (Recovery Point Objective). The team discovers this when the database crashes.
**Why:** Disaster recovery planning is tedious and does not appear in typical "deploy your app" tutorials. LLMs skip it because it is not part of the glamorous deployment pipeline narrative.
**Example:**
```
OPS-29: Database: PostgreSQL on RDS
  - Instance: db.t3.medium
  - Storage: 100GB gp3
  - Multi-AZ: No (cost saving)
  - Backups: Default (7-day retention)
```
(The "default" backup has never been tested. Nobody knows if a restore actually works, how long it takes, or how much data would be lost. There is no procedure documented for "the database is gone, what do we do?")
**Instead:** Define DR explicitly: "RPO: 1 hour (maximum acceptable data loss). RTO: 30 minutes (maximum acceptable downtime). Implementation: automated daily snapshots retained 30 days + continuous WAL archiving to S3 for point-in-time recovery. Tested quarterly: restore to a test instance, verify data integrity, measure actual restore time. Procedure documented in `runbooks/database-recovery.md` with step-by-step commands. Monitoring: alert if backup job fails or last successful backup is older than 25 hours."
