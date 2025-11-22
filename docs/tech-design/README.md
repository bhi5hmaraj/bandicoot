# Technical Design Documentation

Modular technical design for Bandicoot's MVP (6-week launch).

## Document Structure

| Doc | Title | Lines | Focus |
|-----|-------|-------|-------|
| [00-overview.md](00-overview.md) | System Overview | ~200 | Architecture, stack, principles |
| [01-data-architecture.md](01-data-architecture.md) | Data & Storage | ~400 | PostgreSQL/Redis schemas, flows |
| [02-rmab-core.md](02-rmab-core.md) | RMAB Algorithms | ~400 | Clustering, Whittle index, FO mapper |
| [03-api-design.md](03-api-design.md) | API Endpoints | ~350 | FastAPI specs, auth, rate limiting |
| [04-deployment.md](04-deployment.md) | Infrastructure | ~350 | Cloud Run, cost optimization |
| [05-integration.md](05-integration.md) | ETL & Pipelines | ~400 | Suvita integration, data flows |

**Total:** ~2100 lines across 6 modular docs

---

## Quick Navigation

### I want to understand...

**The big picture** → Start with [00-overview.md](00-overview.md)

**How data is stored** → Read [01-data-architecture.md](01-data-architecture.md)
- PostgreSQL tables (clusters, caregiver_states, whittle_indices)
- Redis caching strategy
- Data flows (training, recommendation, state updates)

**The core RMAB math** → Read [02-rmab-core.md](02-rmab-core.md)
- SAHELI's clustering method (passive transitions)
- MDP parameter learning (bayesianbandits)
- Whittle index computation (binary search + value iteration)
- Full training pipeline

**The API contracts** → Read [03-api-design.md](03-api-design.md)
- `/train_clusters`, `/precompute_indices`, `/assign_cluster`
- `/recommend` (main endpoint for getting top-K caregivers)
- `/update_state` (bulk state updates)
- Authentication, rate limiting, error codes

**How to deploy** → Read [04-deployment.md](04-deployment.md)
- Cloud Run setup (serverless FastAPI)
- Cloud Functions (nightly/weekly batch jobs)
- PostgreSQL + Redis configuration
- Cost breakdown (~$157/month)
- CI/CD pipeline (GitHub Actions)

**How to integrate with Suvita** → Read [05-integration.md](05-integration.md)
- ETL from Suvita's PostgreSQL
- State update logic (Responsive/Unresponsive)
- Recommendation output (API pull, CSV export, Pub/Sub)
- Event-driven updates (optional)

---

## Key Design Decisions

### 1. SAHELI-Inspired Architecture
Based on proven Google/ARMMAN deployment (100K+ users, 30% dropout reduction):
- **Clustering:** ~20 groups by passive engagement behavior
- **Pre-computed indices:** O(1) lookup during `/recommend`
- **Warmup period:** 6 weeks data collection for new caregivers
- **Features-Only mapping:** RandomForest for cold-start

### 2. Cost Optimization (~$157/month)
- **Serverless-first:** Cloud Run scales to zero
- **Shared infrastructure:** Reuse Suvita's PostgreSQL
- **Minimal Redis:** 1GB cache for indices only
- **Batch on preemptible VMs:** 60-90% savings on training jobs

### 3. Simplicity Over Complexity
- **2-state model:** Responsive / Unresponsive (extensible to 3-4 later)
- **Batch updates:** Nightly state refresh (vs real-time streaming)
- **API-first:** Clean contracts, easy to test and mock
- **Human-in-the-loop:** Recommendations, not automation

### 4. Delivery-Agnostic
- No hard dependency on Twilio or specific SMS provider
- Generic event bus (Pub/Sub or Kafka)
- CSV export fallback for manual processing

---

## Implementation Order

Follow this sequence for 6-week MVP:

### Week 1-2: Core Infrastructure
1. Read [02-rmab-core.md](02-rmab-core.md) → Implement clustering and Whittle solver
2. Read [01-data-architecture.md](01-data-architecture.md) → Set up PostgreSQL/Redis schemas
3. Validate with synthetic data (Jupyter notebook)

### Week 3-4: API & Integration
1. Read [03-api-design.md](03-api-design.md) → Build FastAPI endpoints
2. Read [05-integration.md](05-integration.md) → Connect to Suvita's data
3. Run `/train_clusters` on real historical data

### Week 5-6: Deployment & Testing
1. Read [04-deployment.md](04-deployment.md) → Deploy to Cloud Run
2. Set up nightly/weekly Cloud Functions
3. A/B test with 1,000 caregivers
4. Monitor, tune, iterate

---

## Reference Documents

- **MVP PRD:** [docs/MVP_PRD.md](../MVP_PRD.md)
- **Project Purpose:** [PROJECT_PURPOSE.md](../../PROJECT_PURPOSE.md)
- **Chat Archive:** [archive/suvita_rmab_chat.md](../../archive/suvita_rmab_chat.md)
- **SAHELI Paper:** Google Research (IAAI 2023)
- **ARMMAN Field Study:** Mate et al. (AAAI 2022)

---

## Design Principles

1. **Modularity:** Each doc is self-contained, reference overview for context
2. **Practicality:** Real code snippets, not pseudocode
3. **Traceability:** Every decision traced back to chat archive or SAHELI paper
4. **Testability:** Unit tests, integration tests, load tests specified
5. **Cost-awareness:** Every component includes cost estimates

---

## FAQ

**Q: Why split into 6 docs instead of one big design doc?**
A: Easier to review, update, and reference. Each doc is ~300-400 lines (readable in one sitting).

**Q: Do I need to read all docs to start coding?**
A: No. Start with 00-overview.md, then jump to whichever component you're implementing.

**Q: Where's the code?**
A: This is design documentation. Implementation lives in `bandicoot/` (Python package) and `functions/` (Cloud Functions).

**Q: What if I find an issue or want to update a doc?**
A: Open a PR! These docs are living documents that evolve with the project.

**Q: How do I know if a design decision is from SAHELI vs chat archive vs our own?**
A: Look for citations:
- "SAHELI approach" → From Google/ARMMAN paper
- "From chat archive" → From `archive/suvita_rmab_chat.md`
- No citation → Our own design decision (but usually justified)

---

## Next Steps

1. ✅ Review all 6 docs
2. ⏳ Prototype Whittle solver (Week 1)
3. ⏳ Set up staging environment (Week 2)
4. ⏳ Implement FastAPI endpoints (Week 3)
5. ⏳ Deploy to Cloud Run (Week 5)
6. ⏳ Launch A/B test (Week 6)

---

**Last Updated:** November 2025
**Maintainers:** Bandicoot Core Team
**Questions?** Open an issue or ask in Slack #bandicoot-dev
