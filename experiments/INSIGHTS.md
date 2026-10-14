# Experiment insights

Both scripts use the synthetic arms in `bandicoot/data/synthetic.py` and $\gamma = 0.99$, unless a table states another value. $p_{s,a}$ is the probability of being Responsive (R) next, from state $s$ under action $a$. All values below come from a rerun on 2026-10-14.

## Experiment 01: solver on synthetic arms

Script: `01_whittle_solver_validation.py`. It needs NumPy only. It uses one arm of each type (seed 42).

| Arm (generator) | $p_{R,0}$ / $p_{R,1}$ | $p_{U,0}$ / $p_{U,1}$ | W(R) | W(U) |
|---|---|---|---|---|
| High engagement (`generate_highly_engaged`) | 0.837 / 0.977 | 0.423 / 0.760 | 0.3521 | 0.8492 |
| Moderate engagement (`generate_moderately_engaged`) | 0.666 / 0.816 | 0.206 / 0.637 | 0.3610 | 1.0367 |
| Disengaged (`generate_disengaged`) | 0.510 / 0.721 | 0.102 / 0.447 | 0.5723 | 0.9370 |

**Finding 1: the index measures the effect of contact, not risk.** In state U, the moderate arm ranks above the disengaged arm (1.0367 against 0.9370). The closed form in [rmab-fundamentals.md](../docs/rmab-fundamentals.md) explains this: $W(s) = \gamma \cdot \text{lift}_s \cdot D$, with $\text{lift}_s = p_{s,1} - p_{s,0}$.

| Arm | Lift in U | $D$ | W(U) |
|---|---|---|---|
| High engagement | 0.337 | 2.548 | 0.8492 |
| Moderate engagement | 0.431 | 2.431 | 1.0367 |
| Disengaged | 0.345 | 2.744 | 0.9370 |

The moderate arm has the largest lift in U. This outweighs its smaller $D$. If a program must reach the highest-risk participants first, the index alone does not do that.

**Finding 2: W(U) > W(R) for these three arms.** Each arm has a larger lift in U than in R. This is not a general property (see experiment 02).

**Finding 3: a higher $\gamma$ widens the gap.** Moderate engagement arm:

| $\gamma$ | W(R) | W(U) | W(U) - W(R) |
|---|---|---|---|
| 0.90 | 0.3218 | 0.9243 | 0.6025 |
| 0.95 | 0.3434 | 0.9862 | 0.6428 |
| 0.99 | 0.3610 | 1.0367 | 0.6757 |

**Finding 4: types overlap in U.** Batch of 20 arms (seed 123), mean and standard deviation:

| Type | Count | W(R) | W(U) |
|---|---|---|---|
| High engagement | 5 | 0.2043 ± 0.0391 | 0.8704 ± 0.0592 |
| Moderate engagement | 10 | 0.3960 ± 0.1048 | 0.9348 ± 0.0706 |
| Disengaged | 5 | 0.5075 ± 0.1119 | 0.7644 ± 0.1275 |

The mean W(R) rises from high engagement to disengaged. The W(U) ranges of the three types overlap.

**Note.** The summary at the end of the script is fixed text. It claims the order disengaged, then moderate, then high engagement. The script's own Property 2 check prints "Unexpected ordering". Ignore the fixed summary.

## Experiment 02: Bandicoot against SAHELI

Script: `02_validate_vs_saheli.py`. It imports `whittle_utils.py` from a SAHELI clone at `/home/user/SAHELI`. It calls `planinf(sleeping_constraint=False)`, the two-state mode. The rerun used the same arms and conversion, with `whittle_utils.py` from GitHub.

**State order.** Bandicoot uses `P[s, s', a]` with state 0 = R. SAHELI takes `T[a, s, s']` with state 1 = engaging. The script flips the states and moves the action axis first. `planinf` then flips the states back.

**Setup.** 53 arms: the 3 synthetic arms and 50 random matrices (`np.random.seed(123)`). Tolerances: $10^{-4}$ (tight) and $10^{-3}$ (loose).

| Metric | Value |
|---|---|
| Mean absolute difference, 50 random arms | 0.000014 |
| Largest difference, 50 random arms | 0.0000916 |
| Arms within $10^{-4}$ | 53 of 53 |
| Arms within $10^{-3}$ | 53 of 53 |

Example, high engagement arm:

| Index | Bandicoot | SAHELI | Difference |
|---|---|---|---|
| W(R) | 0.352081 | 0.352081 | 0.000000 |
| W(U) | 0.849182 | 0.849152 | 0.000031 |

**Meaning.** Bandicoot reproduces SAHELI's two-state solver. The small differences fit the two value-iteration orders and stop rules (see [saheli-analysis.md](../docs/saheli-analysis.md)).

**Limits of this check.**

- It does not test SAHELI's default sleeping mode. That mode gives other values.
- Both codes use the same per-state subsidy method. The check does not compare either code with the textbook Whittle index.
- Test 5, Property 1 (W(U) > W(R) on all 53 arms) fails. Test 5 draws 50 new random matrices, and 20 of them have W(U) ≤ W(R). In the Test 3 matrices, 27 of 50 have W(U) ≤ W(R).
- Property 2 (both codes agree on the order of W(R) and W(U)) checks the 3 synthetic arms only.
