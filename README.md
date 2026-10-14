# Bandicoot

> Open-source restless bandit (RMAB) library that decides who to contact when outreach capacity is limited.

Bandicoot ranks the participants of an outreach program by how much a contact (a call, SMS, visit, or check-in) can help them stay engaged. It uses the Whittle index method of SAHELI, the RMAB system that ARMMAN and Google Research deployed in India.

**Status:** early development. The core library and a FastAPI service exist. There is no production deployment and no measured impact yet.

![How Bandicoot works](docs/diagrams/rmab-workflow.svg)

## When to use it

The method fits a program with these properties:

- Many participants, each with engagement that changes over time
- A fixed budget of human contacts per period
- A contact can change a participant's chance to stay engaged
- Logged engagement and contact data

| Program | Arm | Engagement state | Action (uses the budget) |
|---|---|---|---|
| Vaccination reminders ([reference use case](docs/use-cases/vaccination.md)) | Caregiver | Responds to SMS, attends clinic | Ambassador call |
| Maternal health voice messages (SAHELI) | Mother | Listens to weekly messages | Health worker call |
| TB treatment adherence (research: Mate et al., NeurIPS 2020) | Patient | Takes daily doses | Health worker follow-up |
| Digital rehabilitation (Respira Health, candidate) | Participant | Completes weekly exercise sessions | Physiotherapist or coach check-in |

### Candidate use case: Respira Health

[Respira Health](https://respirahealth.org) delivers an 8-week pulmonary rehabilitation program in India through a WhatsApp chatbot, with physiotherapist oversight. In its 2026 pilot (n = 51), 31% of participants completed half or more of the 24 exercise sessions. Functional gains increased with the number of sessions completed (Spearman ρ = 0.69).

Physiotherapist time is the limited budget. The goal is to spend it on the lapsing participants where a check-in has the largest effect. Before an RMAB can help, the program needs:

1. Weekly engagement data per participant
2. A randomized test of a human check-in vs. an automated reminder, to measure the effect of a contact
3. Enough participants (on the order of 1,000) to learn differences between participant groups

Bandicoot has no deployment or partnership with Respira Health. This section describes a possible application.

## How it works

1. **Cluster** participants by their behavior without contact (k-means on passive transition probabilities).
2. **Learn** the transition probabilities of each cluster, with and without a contact.
3. **Score** each (cluster, state) pair with a Whittle index: the value of a contact now.
4. **Rank** participants by index and contact the top K, where K is the budget.

See [RMAB fundamentals](docs/rmab-fundamentals.md) for the model and [architecture](docs/architecture.md) for the code.

## Evidence behind the method

Bandicoot has no impact data yet. The method comes from SAHELI, which runs in mMitra, ARMMAN's voice-message program for pregnant women and new mothers:

- **Field study** ([Mate et al., AAAI 2022](https://arxiv.org/abs/2109.08075)): 23,003 beneficiaries over 7 weeks. RMAB-selected service calls reduced engagement drops by ~30% and beat both comparison groups (round-robin calls and the current standard of care). Engagement means listening to the automated health voice messages.
- **Deployment** ([Verma et al., AAAI 2023](https://ojs.aaai.org/index.php/AAAI/article/view/26849)): SAHELI reached ~100K beneficiaries.

These results measure engagement with voice messages. Each new program must measure its own outcomes with an A/B test.

In experiment 02, the solver in this repository matched SAHELI's `planinf` solver (without its sleeping constraint) on 53 of 53 test cases (max difference 0.00009). Both solvers search one subsidy per state. For the higher-index state, this value differs from the textbook Whittle index. See [experiments/INSIGHTS.md](experiments/INSIGHTS.md) and [RMAB fundamentals](docs/rmab-fundamentals.md).

## Quick start

```bash
pip install -e .
```

```python
import numpy as np
import pandas as pd
from bandicoot.core.recommender import BandicootRMAB

# One row per participant per period. state: 0 = Responsive, 1 = Unresponsive.
# action: 0 = no contact, 1 = contact. The column name caregiver_id is the code's ID field.
rng = np.random.default_rng(0)
history = pd.DataFrame(
    [{"caregiver_id": pid, "timestamp": t,
      "state": int(rng.random() < 0.4), "action": int(rng.random() < 0.2)}
     for pid in range(200) for t in range(12)]
)

model = BandicootRMAB(n_clusters=4).fit(history, verbose=False)
current_states = history.groupby("caregiver_id")["state"].last().to_numpy()
result = model.recommend(states=current_states, budget=10)
print(result.recommended_ids)
```

To run the API service, see [app/README.md](app/README.md).

## Limits and next extensions

The code supports a 2-state model with one contact type. Other programs need these extensions:

- **N-state models.** The solver assumes 2 states (`(2, 2, 2)` arrays). Respira needs states such as (week, sessions completed).
- **Finite horizon.** The solver uses an infinite horizon (γ = 0.99). Fixed-length programs need time-dependent indices: a contact in week 2 has more value than a contact in week 7.
- **Feature-based cold start.** Clusters come from each participant's own history. New participants get the median index. Enrollment features must map new participants to clusters.
- **Multiple action types.** For example SMS, call, and visit, each with a different cost.
- **Fairness constraints.** Give every lapsed participant a minimum contact, and let the RMAB allocate the remaining budget.

## Documentation

| Document | Contents |
|---|---|
| [RMAB fundamentals](docs/rmab-fundamentals.md) | The model, the Whittle index, and how the solver computes it |
| [Architecture](docs/architecture.md) | Library, API service, planned jobs and storage |
| [Vaccination use case](docs/use-cases/vaccination.md) | The reference use case and its evaluation plan |
| [Open questions](docs/open-questions.md) | Open decisions on modeling, evaluation, and engineering |
| [SAHELI analysis](docs/saheli-analysis.md) | How SAHELI's open-source code works and how Bandicoot differs |
| [Related work](docs/related-work.md) | Papers and libraries |
| [Experiments](experiments/INSIGHTS.md) | Solver validation results |
| [Diagrams](docs/diagrams/README.md) | Graphviz sources and style rules |

## Roadmap

- [x] Core library: clustering, MDP learning, Whittle solver, recommender
- [x] API service (FastAPI) and web UI
- [ ] Partner data integration and storage
- [ ] Batch jobs: weekly training, nightly state update
- [ ] A/B test with a partner program
- [ ] Generalize the solver: N states, finite horizon, feature-based cold start

## Contributing

Open an issue to discuss a change. Contribution guidelines are not written yet.

## References

1. Mate, A. et al. (2022). "Field Study in Deploying Restless Multi-Armed Bandits: Assisting Non-Profits in Improving Maternal and Child Health." *AAAI*.
2. Verma, S. et al. (2023). "Increasing Impact of Mobile Health Programs: SAHELI for Maternal and Child Care." *AAAI*.
3. Whittle, P. (1988). "Restless Bandits: Activity Allocation in a Changing World." *Journal of Applied Probability*.

Inspiration: ARMMAN and Google Research built SAHELI, the first deployed RMAB system in public health.

## License

**MIT License.** The LICENSE file is not in the repository yet.

## Contact

[GitHub Issues](https://github.com/bhi5hmaraj/bandicoot/issues)

*Bandicoot is named after the small marsupial that digs to find food. The system digs through data to find the participants who need help.*
