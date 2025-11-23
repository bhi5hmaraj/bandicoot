# Open Questions Tracker

This directory tracks unanswered questions, design decisions, and uncertainties across different aspects of the Bandicoot RMAB project.

## Question Categories

### 📊 [Modeling Questions](./modelling.md)
RMAB algorithm choices, mathematical assumptions, parameter tuning, and optimization strategies.

### 🔌 [Suvita Integration](./suvita-integration.md)
Questions about integrating Bandicoot with Suvita's production system, data pipelines, and deployment.

### 🏗️ [Technical Design](./tech-design.md)
Architecture decisions, performance optimization, scalability, and implementation choices.

### 📈 [Evaluation & Metrics](./evaluation.md)
How to measure success, A/B testing strategy, and performance metrics.

## How to Use This

1. **Add new questions** as they arise during development
2. **Mark status** for each question:
   - ❓ **Open** - Needs answer
   - 🔍 **Investigating** - Research in progress
   - ⚠️ **Blocked** - Waiting on external input
   - ✅ **Resolved** - Decision made (move to decisions/)
3. **Link to decisions** when questions are resolved
4. **Update regularly** during sprint planning and retrospectives

## Question Template

When adding a new question, use this format:

```markdown
## ❓ Question Title

**Status:** Open | Investigating | Blocked | Resolved
**Priority:** High | Medium | Low
**Category:** Modeling | Integration | Performance | etc.

### Context
Brief background on why this question matters.

### The Question
Clear articulation of what needs to be decided or answered.

### Options
- Option A: ...
- Option B: ...

### Implications
What depends on this decision?

### Next Steps
What needs to happen to resolve this?
```

## Recent Activity

- **2025-11-23**: Created questions tracker structure
- Track updates here as questions are added/resolved
