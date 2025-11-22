# Theory Documentation

This folder contains theoretical foundations and explanations for the Bandicoot RMAB system.

## Documents

### Core Concepts
1. **[01-rmab-fundamentals.md](01-rmab-fundamentals.md)** - Introduction to Restless Multi-Armed Bandits
2. **[02-healthcare-problem.md](02-healthcare-problem.md)** - The vaccination adherence challenge
3. **[03-our-solution.md](03-our-solution.md)** - Bandicoot's approach and architecture

### Advanced Topics
4. **[04-whittle-index.md](04-whittle-index.md)** - Understanding Whittle indices and computation
5. **[05-clustering-rationale.md](05-clustering-rationale.md)** - Why clustering over individual learning

## Reading Path

**For stakeholders/non-technical:**
- Start with 02-healthcare-problem.md
- Then 03-our-solution.md
- Skip the mathematical details in 01 and 04

**For engineers/researchers:**
- Read in order: 01 → 02 → 03 → 04 → 05
- Refer to these when implementing algorithms in `/src`

**For data scientists:**
- Focus on 01, 04, and 05
- These explain the statistical foundations

## Key Takeaways

### The Problem
- **200K+ caregivers**, limited health worker bandwidth
- Need to prioritize: who to contact for maximum vaccination impact?
- Random/heuristic allocation is inefficient

### The Solution
- **RMAB** framework models caregivers as bandits with changing states
- **Whittle index** provides optimal priority scores under budget constraints
- **Clustering** shares statistical strength across similar caregivers
- **Proven approach**: SAHELI deployment showed 30% dropout reduction

### Why It Works
- Learns from historical data (SMS engagement, vaccinations)
- Adapts to individual behavior patterns
- Balances exploration (uncertain caregivers) vs exploitation (known high-risk)
- Scales to 200K+ caregivers with <$200/month cost

---

**Related Documentation:**
- Product: `/docs/MVP_PRD.md`
- Technical Design: `/docs/tech-design/`
- Archive: `/archive/suvita_rmab_chat.md` (5,909-line design discussion)
