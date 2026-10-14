# Open questions

This page lists open design decisions for any outreach program that uses Bandicoot. Each row gives the context, the options, and the current lean if a source states one. "Code" means the library does this now. "Design docs" means the earlier design docs (now in git history) proposed it. Questions for one program go in its use-case page, for example [vaccination](use-cases/vaccination.md).

Terms: a **participant** is one person enrolled in the **program** (one arm). A **contact** is one call, SMS, visit, or check-in. The **budget** is the number of contacts per cycle.

## Modeling

| Question | Context | Options | Lean |
|---|---|---|---|
| Index definition | The solver searches one subsidy per state at once, like SAHELI's `planinf`. For the higher-index state, the value differs from the textbook Whittle index (diagram example: 1.21 vs. 1.57). See [RMAB fundamentals](rmab-fundamentals.md). | Keep SAHELI-compatible values; switch to a scalar-subsidy search | None. Check whether the top-K sets change on real data. |
| Number of clusters (k) | Too few clusters lose detail. Too many overfit sparse data and add index computations. | Keep 20 (the SAHELI value); choose k by silhouette score; use segments from program staff; start with coarse clusters, then refine | None. Code default is 20. Sweep k on real data first. |
| Discount factor (gamma) | Gamma sets the planning horizon, about 1/(1 - gamma) steps. | 0.99 (about 100 steps); 0.95 (about 20); 0.90 (about 10); one value per participant life stage | None. Code default is 0.99. Run a sensitivity test. |
| Number of states | Two states can hide partial engagement. More states need more data per cluster and cost more to solve. | 2 states; 3 levels; 4 levels; continuous score (does not fit a discrete RMAB) | 2 states for the first version (decided). Revisit when the data supports more. |
| State observation | The model needs the current state of each participant. Program data seldom labels it. | A rule, such as "responded in the last 7 days"; last observed interaction; hidden-state inference from history; staff labels | A rule-based window (design docs). Check it against staff judgment. |
| Time step | Short windows are noisy and have gaps. Long windows are slow to react. The step length also changes what gamma means. | Daily; weekly; monthly; one step per contact event | Match the contact cadence of the program. |
| Action types | Two actions treat all contacts as equal. Channels differ in cost and effect. | Contact or no contact; one action per channel; intensity levels; one model per channel | 2 actions in code. Channel choice is out of scope for the first version. One option: the RMAB picks who, and a separate model picks how. |
| Reward | The code reward is +1 per step in Responsive and -1 per step in Unresponsive. It may not match the program goal. | Engagement only; add a bonus when a program outcome occurs | None. |
| Budget shape | The budget sets how many IDs the recommender returns. | Fixed count per cycle; staff capacity; cost budget; hard or soft cap; caps per channel; caps per participant; minimum index to recommend | None. Code takes one fixed count. |
| Sparse passive data | Clustering uses passive transitions. Some participants have few passive observations. | Dirichlet smoothing; population prior; minimum observation count; predict from participant features | Code uses Dirichlet smoothing (alpha = 1.0). Test sensitivity to alpha. |
| New participants | New participants have no history. | One default priority for all; cluster from registration features; an exploration phase; population prior | Code gives unknown IDs the median index. Design docs add a features-only mapper and a warmup period. Neither is built. |
| Non-stationarity | RMAB assumes fixed transitions. Behavior changes over time and across life stages. | Assume fixed (code); refit on a sliding window; online updates; one model per life stage | Fixed for now. Check transition stability in real data. |
| Exploration | Contacts that the policy chooses are not a random sample. A policy that only exploits stops learning. | Periodic refit; online updates; inverse propensity weighting; a random holdout group; Thompson sampling | None. |
| Scope beyond "who" | RMAB picks who to contact. Content, channel, timing, frequency, and language could also adapt. | Inside Bandicoot; a separate system behind an API contract | Out of scope for the first version (design docs). |

## Evaluation

| Question | Context | Options | Lean |
|---|---|---|---|
| Primary metric | RMAB maximizes reward. The program needs a real-world metric to judge success. | Engagement rate; retention after a fixed period; content consumption; behavior outcome; engagement per contact | None. Pre-register one primary metric. |
| Study design | A causal effect needs a valid comparison group. | Participant-level RCT; cluster RCT by staff member; difference-in-differences; regression discontinuity; synthetic control; propensity matching | RCT or cluster RCT. |
| Control policy | The baseline sets the bar. | Current program method; random; greedy (least engaged first); round-robin; other bandit methods; oracle (analysis only) | One or two baselines: the current method plus a simple one. |
| Withholding contacts | A control arm can get fewer contacts than it would get otherwise. | Randomize only when no arm is known to be better; delayed control; staggered rollout | The control arm keeps the standard care of the program. |
| Randomization | Simple randomization can leave arms unbalanced. | Simple; stratified (tenure, baseline engagement, region); blocked by staff member; clustered; split 50/50, 80/20, or three arms | None. |
| Sample size | The minimum detectable effect drives the sample size. | Fix the effect size, alpha, and power before launch | Example: baseline 40%, +5 points, alpha 0.05, and power 0.80 need about 1,530 per arm (two-proportion test). |
| Success rule | Many outcomes and early looks at the data both inflate false positives. | Fixed horizon; sequential test with correct bounds; Bayesian threshold; Bonferroni or Holm correction for many outcomes | Significant on the primary metric, larger than a minimum effect set before launch, and no harm on secondary metrics. |
| Offline evaluation | Historical data comes from the old policy. Counterfactual outcomes are missing. Propensity methods need logged contact probabilities. | Replay (biased); inverse propensity scoring; doubly robust estimation; simulation in the learned MDP | Simulate in the learned MDP first. |
| Online metrics | Production needs outcome, system, model, and fairness signals. | Outcome rates; latency, errors, and budget use; cluster sizes, index range, and state shares; coverage and per-cluster outcomes | None. |
| Rollout | Full replacement has no safety net. | Shadow mode; parallel A/B test; mixed list; full replacement | None. |
| Long-term effect | Early lift can fade. Seasons and policy changes confound trends. | Extended test; interrupted time series; staggered rollout by region | None. |

## Engineering

| Question | Context | Options | Lean |
|---|---|---|---|
| Batch or real time | The program workflow decides when lists are needed. | Daily batch; on-demand API; batch plus on-demand refresh; event-driven | None. |
| Deployment | The service must fit the infrastructure and budget of the program. | Serverless functions; container service; scheduled batch job; batch plus API | Design docs plan a container service with scheduled batch jobs. |
| NumPy or JAX | A JAX prototype exists in [research/jax](../research/jax/README.md). Nobody has benchmarked it. | Keep NumPy; move to JAX | Benchmark NumPy at target scale first. Target for a switch: more than 5x faster, and results within 1e-6 of NumPy. |
| Model persistence | Fitted models need save, load, and versions. | Pickle; NumPy .npz; MLflow registry; Protocol Buffers | None. Version the parameters, the config (k, gamma, alpha), a data fingerprint, the git commit, and the metrics. |
| Storage | Recommendations, outcomes, state history, and models need a store. | PostgreSQL; time-series extension; object storage with Parquet; Redis cache; a hot, warm, and cold mix | Design docs plan PostgreSQL plus Redis. Neither is built. |
| Monitoring | Production needs alerts on system and model health. | Prometheus and Grafana; cloud provider monitoring; an application monitoring service; structured logs with alerts | None. |
| Pre-launch tests | Unit and integration tests exist. | Performance benchmark at target scale; load test; validation on real data; shadow run | None run yet. |
| Drift and retraining | Participant behavior and data inputs change. | Scheduled refit; refit on detected drift (Kolmogorov-Smirnov test, population stability index); refit on demand; full, incremental, or sliding-window data | Design docs plan weekly batch retraining. |
| Multi-tenancy | Bandicoot has one reference use case. | One model per program; pooled model; shared base with a fit per program; federated learning | Defer until a second program joins. |
