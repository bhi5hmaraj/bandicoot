# SAHELI code analysis

SAHELI is the RMAB system of ARMMAN and Google Research. It selects beneficiaries of the mMitra voice-message program for service calls. Its code is at [github.com/armman-projects/SAHELI](https://github.com/armman-projects/SAHELI) (Apache-2.0). This page describes that code as read on 2026-10-14. It also lists how Bandicoot differs.

## Evidence

| Source | Finding |
|---|---|
| Mate et al. (2022), AAAI | Field study with 23,003 beneficiaries over 7 weeks. Three groups: RMAB-selected service calls, round-robin calls, and the current standard of care. The RMAB group had about 30% fewer engagement drops, a statistically significant result over both other groups. |
| Mate et al. (2022) | Engagement means listening to the automated voice messages. The study did not measure a vaccination outcome. |
| Verma et al. (2023), AAAI | SAHELI reached about 100K beneficiaries. |
| SAHELI `data_description.md` | 98K beneficiaries served, 20K enrolling per month, 1000 interventions per week, 6-week warmup before service calls start. |

## Repository structure

| File | Content |
|---|---|
| `pipeline.py` | The ranking script: load data, predict clusters, find states, look up indices, rank, push the top $K$. |
| `whittle_utils.py` | `get_reward`, `convertAxis`, and `planinf` (the Whittle index solver). |
| `data_description.md` | Schema of the beneficiary features and call records. |
| `README.md`, `LICENSE.txt`, `NOTICE` | Overview, contacts, license. |

Missing parts:

- `pipeline.py` imports `data_utils`, `model_utils`, and `armman_db_utils`. These files are not in the repository.
- `pipeline.py` imports `load_precomputed_whittle_indices` from `whittle_utils`. `whittle_utils.py` does not define it.
- The repository has no clustering code and no transition-estimation code.

So `pipeline.py` does not run as published. `planinf` runs on its own.

## Pipeline steps

1. Load the budget $K$ and the registration window from a parameters table. The docstring gives $K = 1000$.
2. Load static features, beneficiary records, and call records.
3. Load a mapping model (`cls`, `scaler`) and a table of precomputed indices `m_values[cluster, state]`.
4. Predict a cluster for every beneficiary from static features: `cls.predict(scaler.transform(static_features))`.
5. Skip each beneficiary who is already in the intervention table.
6. Find the current state of each remaining beneficiary.
7. Look up the index, sort in descending order, and push the top $K$.

`CONFIG` sets `gamma = 0.99`, `clusters = 20`, `clustering = "kmeans"`, `time_step = 7`, and `transitions = "weekly"`.

## State definition

- The window holds calls with `startdate` in $[d - 7, d)$. Here $d$ is today in days since 2018-01-01.
- Engaged (E, also "L" for low risk of dropout): at least one call in the window has `duration >= 30`. The repository does not state the unit.
- Not engaged (NE, also "H" for high risk): no such call.
- The script also counts connected calls (`duration > 0`), but it does not use that count.
- E maps to column 2 of `m_values` and NE to column 3.

## Whittle computation (`planinf`)

- **Input:** array axes `[action, state, next_state]`, where state 1 is the engaging state. `convertAxis` changes this to `[state, next_state, action]` with state 0 = L.
- **Reward:** $+1$ in L, $-1$ in H. The passive action ("N") adds the subsidy $m$ of the current state.
- **Search:** one subsidy per state in $[-2, 2]$. Each step halves the interval of the state with the largest $\lvert Q(s, I) - Q(s, N) \rvert$.
- **Stop rules:** that largest difference is at most $10^{-5}$, or the subsidies change by less than $10^{-20}$. There is no iteration cap.
- **Value iteration:** restarts from $V = 0$ at each search step. Updates $V$ in place, state by state. Stops when the largest change is at most $10^{-4}$.
- **Output:** `[m[-1], m[-2]]`, which is `[W(NE), W(E)]`.

`planinf` has two modes:

| Mode | Model |
|---|---|
| `sleeping_constraint=True` (default) | Four states: L0, H0, L, H. An intervention in L or H moves the arm to L0 or H0. In L0 and H0, both actions follow the passive dynamics forever. So each beneficiary can benefit from at most one intervention. |
| `sleeping_constraint=False` | The plain two-state model. |

The pipeline reads columns 2 and 3 of a four-column index table. This suggests that the deployed indices use the default four-state mode.

## How Bandicoot differs

| Aspect | SAHELI | Bandicoot |
|---|---|---|
| Array layout | Input `[a, s, s']`, state 1 = engaging | `[s, s', a]`, state 0 = Responsive |
| Model | Default: one intervention per beneficiary (sleeping mode) | Two states, repeated contact allowed. Same as `planinf(sleeping_constraint=False)`. |
| Value iteration | In place, state by state | Both states update from the previous $V$ |
| Stop rules | $10^{-5}$, $10^{-4}$, subsidy change below $10^{-20}$, no cap | $10^{-5}$, $10^{-4}$, cap of 1000 search iterations |
| Return order | `[W(NE), W(E)]` | `(W(R), W(U))` |
| Cluster assignment | Mapping model from static features, for every beneficiary | k-means label from passive history. An unknown ID gets the median index. No feature model. |
| Clustering and estimation | Not published | `clustering.py`, `mdp.py` (Dirichlet smoothing, $\alpha = 1$) |
| Recent contacts | Skips beneficiaries in the intervention table | Not handled |
| State rule | Call with `duration >= 30` in the last 7 days | The caller supplies state 0 or 1 |
| Input checks | None | Shape, range, NaN or Inf, row sums |

The state order flip matters. `experiments/02_validate_vs_saheli.py` maps Bandicoot state $s$ to SAHELI state $1 - s$ and moves the action axis first. `planinf` then flips the states back.

## Agreement check

- `experiments/02_validate_vs_saheli.py` compares Bandicoot with `planinf(sleeping_constraint=False)` on 53 arms (3 synthetic, 50 random). All 53 differ by less than 0.0001 (see [INSIGHTS.md](../experiments/INSIGHTS.md)).
- A rerun on 2026-10-14 with `whittle_utils.py` from GitHub gave the same result. The largest difference was 0.0000916.
- The check does not cover the default sleeping mode. For the high-engagement synthetic arm, sleeping mode gives $W(E) = -0.10$ and $W(NE) = 0.29$ (rerun on 2026-10-14). Bandicoot gives 0.35 and 0.85.
- Both solvers use one subsidy per state. In the two-state model, the result for the state with the higher index differs in general from the textbook Whittle index. See [rmab-fundamentals.md](rmab-fundamentals.md).
