# RMAB Fundamentals: Restless Multi-Armed Bandits

**Level:** Intermediate (some math required)
**Prerequisites:** Basic probability, Markov chains
**Reading Time:** 20 minutes

---

## Table of Contents
1. [What is a Multi-Armed Bandit?](#what-is-a-multi-armed-bandit)
2. [From MAB to RMAB: The "Restless" Extension](#from-mab-to-rmab-the-restless-extension)
3. [Why RMAB for Healthcare?](#why-rmab-for-healthcare)
4. [Key Concepts](#key-concepts)
5. [The Optimization Problem](#the-optimization-problem)
6. [Whittle Index Solution](#whittle-index-solution)

---

## What is a Multi-Armed Bandit?

### The Classic Problem

Imagine you're at a casino with **K slot machines** (one-armed bandits). Each machine has:
- An unknown probability of paying out
- You have a limited budget (N pulls total)

**Goal:** Maximize total reward by learning which machines are best while also exploiting that knowledge.

**Trade-off:**
- **Explore:** Try different machines to learn their payout rates
- **Exploit:** Pull the machine you currently think is best

### Formal Definition

A Multi-Armed Bandit (MAB) is a tuple:
```
MAB = (K, {P_i}, {R_i})
```

Where:
- **K** = Number of arms (bandits)
- **P_i** = Probability distribution of rewards for arm i
- **R_i** = Reward obtained from pulling arm i

**Policy:** A strategy π for choosing which arm to pull at each timestep

**Objective:** Find policy π* that maximizes expected cumulative reward:
```
π* = argmax E[Σ_{t=1}^T R_{a_t}]
         π
```

### Classic Algorithms

1. **ε-greedy:** Pull best arm with probability (1-ε), random arm with probability ε
2. **UCB (Upper Confidence Bound):** Pull arm with highest upper confidence bound
3. **Thompson Sampling:** Bayesian approach using posterior sampling

---

## From MAB to RMAB: The "Restless" Extension

### The Key Difference

**Classic MAB Assumption:** Arms don't change when you don't pull them.
- If you ignore a slot machine for 100 turns, it's the same when you return

**Real-World Reality:** Many systems are **restless** - they change even when not acted upon.
- A patient's health evolves whether you intervene or not
- A caregiver's engagement drifts even without SMS reminders
- A machine degrades even when idle

### Restless Multi-Armed Bandit (RMAB)

**Definition:** Each arm is a **Markov Decision Process (MDP)** with:
- **States:** S = {s₁, s₂, ..., s_n}
- **Actions:** A = {active, passive}
- **Transitions:** P(s' | s, a) - state evolves based on action
- **Rewards:** R(s, a) - reward received in state s with action a

**Key Property: Restlessness**
```
P(s' | s, passive) ≠ P(s' | s, stay_same)
```

Even without intervention (passive action), the state changes probabilistically.

### Example: Healthcare Caregiver

**States:**
- **Responsive (R):** Opens SMS, engaged with reminders
- **Unresponsive (U):** Ignores messages, at-risk

**Actions:**
- **Active:** Send SMS reminder or call
- **Passive:** No intervention

**Transitions:**
```
P(R | R, active)   = 0.85  (high engagement maintained)
P(R | R, passive)  = 0.60  (engagement drifts without reminders)
P(R | U, active)   = 0.50  (intervention can re-engage)
P(R | U, passive)  = 0.10  (unlikely to self-recover)
```

**Restlessness:** Even without SMS (passive), the caregiver's state changes:
- Responsive → Unresponsive with probability 0.40
- Unresponsive → Responsive with probability 0.10

---

## Why RMAB for Healthcare?

### The Resource Allocation Problem

**Scenario:**
- Hospital has **200,000 pregnant women** enrolled in vaccination program
- **50 health workers** available for outreach (calls, visits)
- Each worker can contact ~20 caregivers per day
- **Budget constraint:** Only 1,000 contacts per day

**Question:** Which 1,000 caregivers should we prioritize today?

### Why Traditional Methods Fail

**1. Random Selection**
- Wastes resources on caregivers who would vaccinate anyway
- Misses high-risk caregivers who need intervention

**2. Rule-Based Heuristics**
```
IF missed_last_appointment AND age < 25 THEN priority = HIGH
```
- Doesn't account for engagement history
- Ignores individual response to interventions
- No learning from outcomes

**3. Supervised ML (Predict Dropout Risk)**
```
Model: P(dropout | features) → priority
```
- Static predictions, no sequential decision-making
- Doesn't model how interventions change behavior
- No budget constraints

### Why RMAB is Ideal

✅ **Models dynamics:** States evolve over time (restlessness)
✅ **Personalized:** Each caregiver is an arm with unique MDP
✅ **Budget-aware:** Whittle index naturally handles constraints
✅ **Causal:** Learns effect of interventions, not just correlations
✅ **Adaptive:** Updates as new data arrives

---

## Key Concepts

### 1. Markov Decision Process (MDP)

Each caregiver is modeled as an MDP:

**States (S):**
```
S = {Responsive, Unresponsive}
```

**Actions (A):**
```
A = {active (SMS/call), passive (no intervention)}
```

**Transition Probabilities P(s'|s,a):**
```
┌─────────────────────────────────────────────┐
│  Current   Action    Next State  Probability│
├─────────────────────────────────────────────┤
│  R         active    R           0.85       │
│  R         active    U           0.15       │
│  R         passive   R           0.60       │
│  R         passive   U           0.40       │
│  U         active    R           0.50       │
│  U         active    U           0.50       │
│  U         passive   R           0.10       │
│  U         passive   U           0.90       │
└─────────────────────────────────────────────┘
```

**Reward R(s,a):**
```
R(s,a) = P(vaccination | s, a)

R(R, active)  = 0.80  (responsive + reminder → high vaccination)
R(R, passive) = 0.40  (responsive but no reminder → moderate)
R(U, active)  = 0.30  (unresponsive but outreach helps)
R(U, passive) = 0.05  (unresponsive + ignored → very low)
```

### 2. The Restless MAB Problem

**Given:**
- K caregivers (arms), each with MDP (S_i, A_i, P_i, R_i)
- Budget B (can intervene on at most B caregivers per day)

**Find:**
Policy π: S₁ × S₂ × ... × S_K → {subset of size B}

**That maximizes:**
```
E[Σ_{t=1}^T Σ_{i=1}^K R_i(s_i^t, a_i^t)]
```

Subject to:
```
Σ_{i=1}^K 1[a_i^t = active] ≤ B  (budget constraint)
```

### 3. Complexity

This problem is **PSPACE-hard** (Papadimitriou & Tsitsiklis, 1999).

**Why?**
- State space explodes: |S|^K possible joint states
- For K=200,000 caregivers, S=2 states → 2^200,000 states (intractable)

**Need approximations!**

---

## The Optimization Problem

### Bellman Equation (Single Arm)

For one caregiver, the value function satisfies:
```
V(s) = max_{a ∈ A} [R(s,a) + γ Σ_{s'} P(s'|s,a) V(s')]
```

Where:
- **V(s):** Expected future reward from state s
- **γ:** Discount factor (0 < γ < 1, typically 0.95)
- **R(s,a):** Immediate reward
- **P(s'|s,a) V(s'):** Expected future value after transition

### Indexability (Whittle's Condition)

An RMAB arm is **indexable** if the optimal policy has a monotone structure:

**Definition:** There exists a threshold λ(s) such that:
```
Active policy is optimal   ⟺   λ(s) ≥ λ*
Passive policy is optimal  ⟺   λ(s) < λ*
```

Where λ is a "subsidy" for taking the passive action.

**Intuition:** If we pay you λ(s) dollars to stay passive, there's a threshold λ* where you're indifferent between active and passive.

### Whittle Index Definition

The Whittle index for state s is:

```
W(s) = inf{λ : V_passive(s; λ) ≥ V_active(s)}
```

Where:
- **V_active(s):** Value of always acting (active policy)
- **V_passive(s; λ):** Value of never acting + subsidy λ

**Interpretation:** W(s) is the minimum subsidy needed to make you prefer passive over active.

**Higher W(s) → More valuable to intervene in state s**

---

## Whittle Index Solution

### Whittle's Index Policy (1988)

**Algorithm:**
1. Compute Whittle index W_i(s_i) for each arm i in each state s_i
2. At each timestep:
   - Observe current states: (s₁, s₂, ..., s_K)
   - Rank all arms by their indices: W₁(s₁), W₂(s₂), ..., W_K(s_K)
   - Intervene on the top B arms (highest indices)

**Properties:**
✅ **Near-optimal:** Proven to be asymptotically optimal as K → ∞
✅ **Scalable:** O(K log K) to sort, O(1) per arm
✅ **Interpretable:** Index = priority score

### Example Computation

Consider a caregiver in state **Unresponsive**:

**Step 1: Value Iteration for Active Policy**
```
V_active(U) = R(U, active) + γ [P(R|U,active) V_active(R) + P(U|U,active) V_active(U)]
V_active(U) = 0.30 + 0.95 [0.50 × V_active(R) + 0.50 × V_active(U)]
```

Solve system:
```
V_active(R) = 8.33
V_active(U) = 4.17
```

**Step 2: Value Iteration for Passive Policy (with subsidy λ)**
```
V_passive(U; λ) = R(U, passive) + λ + γ [P(R|U,passive) V_passive(R) + P(U|U,passive) V_passive(U)]
V_passive(U; λ) = 0.05 + λ + 0.95 [0.10 × V_passive(R) + 0.90 × V_passive(U)]
```

**Step 3: Binary Search for λ where V_passive(U; λ) = V_active(U)**
```
Find λ such that V_passive(U; λ) = 4.17
```

Result: **W(U) ≈ 0.73**

Similarly: **W(R) ≈ 0.42**

**Interpretation:**
- Unresponsive state has higher index (0.73 > 0.42)
- → Prioritize interventions for unresponsive caregivers
- → Responsive caregivers are already engaged, less urgent

---

## Key Assumptions

### 1. Indexability
Not all RMABs are indexable. We assume:
- Monotone transition probabilities
- Non-negative rewards
- Discount factor γ < 1

**Healthcare satisfies these:** State transitions are well-behaved.

### 2. Known MDP Parameters
We assume P(s'|s,a) and R(s,a) are known or can be learned from data.

**In practice:** Learn from historical SMS logs and vaccination records.

### 3. Homogeneous Horizon
All caregivers are optimized over the same time horizon T.

**For Bandicoot:** T ≈ 40 weeks (pregnancy to child's first year)

### 4. No Constraints Beyond Budget
We don't model:
- Geographic constraints (can't visit all districts)
- Fairness requirements (equal allocation across demographics)

**Future work:** Multi-objective RMAB with fairness constraints.

---

## Theoretical Guarantees

### Optimality Results (Weber & Weiss, 1990)

**Theorem:** If all arms are indexable, Whittle's index policy is:
1. **Asymptotically optimal** as K → ∞
2. Achieves performance within O(1/K) of the optimal policy

**Proof sketch:**
- As K grows, the "marginal cost" of deviating from index policy → 0
- Whittle index approximates Lagrangian relaxation of budget constraint

### Regret Bounds (Recent Work)

For **unknown MDP parameters** (online learning setting):

**Theorem (Mate et al., 2020):**
Thompson Sampling with Whittle indices achieves:
```
Regret = O(√(K² T log T))
```

**Meaning:** After T timesteps, average loss vs optimal policy is O(√T).

---

## Comparison to Other Approaches

| Approach | Pros | Cons | Use Case |
|----------|------|------|----------|
| **Random** | Simple, unbiased | No learning, wastes resources | Baseline only |
| **Greedy (myopic)** | Fast, interpretable | Ignores future value | Short-term objectives |
| **Supervised ML** | Handles rich features | No sequential planning | Risk prediction only |
| **Contextual Bandits** | Learns from features | Assumes i.i.d. contexts | Non-sequential settings |
| **RMAB (Whittle Index)** | Sequential, budget-aware, near-optimal | Requires MDP learning | Healthcare, education, resource allocation |
| **Reinforcement Learning** | Handles complex dynamics | Sample inefficient, hard to scale | Robotics, games (K small) |

---

## Summary

### Key Takeaways

1. **RMAB extends MAB** by modeling arms that change even when not acted upon (restlessness)
2. **Healthcare is restless:** Patient states evolve whether we intervene or not
3. **Whittle index** provides a scalable, near-optimal solution for budget-constrained RMABs
4. **Index = priority score:** Higher index → more valuable to intervene
5. **Proven approach:** Used in Google/ARMMAN SAHELI deployment (30% dropout reduction)

### Mathematical Foundations

```
RMAB = K arms × MDP per arm × Budget constraint B

MDP = (States, Actions, Transitions P(s'|s,a), Rewards R(s,a))

Whittle Index W(s) = subsidy needed to prefer passive over active

Policy: Intervene on top-B arms ranked by W(s)
```

### Next Steps

- **02-healthcare-problem.md:** How RMAB applies to vaccination adherence
- **04-whittle-index.md:** Deep dive into index computation algorithms
- **05-clustering-rationale.md:** Why we cluster caregivers instead of individual RMABs

---

## References

1. **Whittle, P. (1988).** "Restless Bandits: Activity Allocation in a Changing World." *Journal of Applied Probability*.
2. **Weber, R. & Weiss, G. (1990).** "On an Index Policy for Restless Bandits." *Journal of Applied Probability*.
3. **Papadimitriou, C. & Tsitsiklis, J. (1999).** "The Complexity of Optimal Queuing Network Control." *Mathematics of Operations Research*.
4. **Mate, A. et al. (2020).** "Collapsing Bandits and Their Application to Public Health Interventions." *NeurIPS*.
5. **Killian, J. et al. (2021).** "Learning to Prescribe Interventions for Tuberculosis Patients using Digital Adherence Data." *KDD*.
6. **Verma, A. et al. (2023).** "Restless Multi-Armed Bandits for Maternal and Child Health: SAHELI Deployment." *IAAI*.

---

**Author:** Bandicoot Team
**Last Updated:** November 2025
**Feedback:** See `/mentor_notes.md` for MedhAI's critique
