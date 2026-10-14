# Related work

## Papers

| Paper | What it adds | Why it matters for Bandicoot |
|---|---|---|
| Whittle (1988) | Defines restless bandits. Relaxes the budget to a time average and derives an index from a subsidy for the passive action. | Basis of the priority score in `whittle.py`. |
| Weber and Weiss (1990) | Shows the index policy is asymptotically optimal for indexable arms if a fluid approximation has a globally stable equilibrium. Gives an example where the policy is not asymptotically optimal. | The guarantee is for large programs. Bandicoot does not check its conditions. |
| Papadimitriou and Tsitsiklis (1999) | Shows that the restless bandit problem is PSPACE-hard. | Explains why Bandicoot uses an index heuristic and not exact planning. |
| Killian et al. (2019) | Predicts missed tuberculosis doses from 99DOTS digital adherence data, to target interventions. | An example of learning whom to contact from adherence logs. |
| Mate et al. (2020) | "Collapsing bandits": the state is seen only after an action. Gives indexability conditions and fast Whittle index computation via threshold policies. Tested on tuberculosis adherence data. | Relevant when a program observes engagement only after contact. |
| Mate et al. (2022) | Field study of RMAB-selected service calls with 23,003 beneficiaries over 7 weeks. The RMAB group had about 30% fewer engagement drops, a statistically significant improvement over round-robin calls and standard of care. | Field evidence for the method that Bandicoot copies. The outcome was engagement, not a health outcome. |
| Verma et al. (2023) | Describes the deployed SAHELI system, which reached about 100K beneficiaries. | Reference design. See [saheli-analysis.md](saheli-analysis.md). |
| Wang et al. (2023) | Decision-focused learning: trains a feature-to-transition model for Whittle policy quality, not prediction accuracy. Shows the Whittle index policy is differentiable. Uses maternal and child health data. | An option to replace the cluster-then-count step when participant features exist. |
| Danassis et al. (2023) | Shows deviations from the Markov assumption in ARMMAN data. Proposes TARI, a ranking from time-series forecasts. In a secondary analysis, the authors report 90.8% more engagement drops prevented than with the deployed Whittle policy. | Tests the Markov assumption that Bandicoot makes. |
| Liang et al. (2024) | BCoR: Bayesian modeling with Thompson sampling for online RMABs. Handles context, non-stationarity, and short horizons. Evaluated with ARMMAN-based adherence data. | A path to online learning and cold start. |

### Full references

- Whittle, P. (1988). "Restless Bandits: Activity Allocation in a Changing World." *Journal of Applied Probability*.
- Weber, R. R., and Weiss, G. (1990). "On an Index Policy for Restless Bandits." *Journal of Applied Probability*.
- Papadimitriou, C. H., and Tsitsiklis, J. N. (1999). "The Complexity of Optimal Queuing Network Control." *Mathematics of Operations Research*.
- Killian, J. A., et al. (2019). "Learning to Prescribe Interventions for Tuberculosis Patients Using Digital Adherence Data." *KDD*.
- Mate, A., et al. (2020). "Collapsing Bandits and Their Application to Public Health Interventions." *NeurIPS*.
- Mate, A., et al. (2022). "Field Study in Deploying Restless Multi-Armed Bandits: Assisting Non-Profits in Improving Maternal and Child Health." *AAAI*.
- Verma, S., et al. (2023). "Increasing Impact of Mobile Health Programs: SAHELI for Maternal and Child Care." *AAAI*.
- Wang, K., et al. (2023). "Scalable Decision-Focused Learning in Restless Multi-Armed Bandits with Application to Maternal and Child Health." *AAAI*.
- Danassis, P., et al. (2023). "Limited Resource Allocation in a Non-Markovian World: The Case of Maternal and Child Healthcare." *IJCAI*.
- Liang, B., et al. (2024). "A Bayesian Approach to Online Learning for Contextual Restless Bandits with Applications to Public Health." arXiv:2402.04933. Later arXiv versions use the title "Context in Public Health for Underserved Communities: A Bayesian Approach to Online Restless Bandits."

## Libraries

| Library | What it offers | Fit for Bandicoot |
|---|---|---|
| SAHELI ([armman-projects/SAHELI](https://github.com/armman-projects/SAHELI)) | `planinf` Whittle solver and a ranking script. No clustering or estimation code. Apache-2.0. | Reference for the solver. Bandicoot matches its two-state mode (`experiments/02_validate_vs_saheli.py`). |
| scikit-learn | k-means, silhouette score | In use in `clustering.py`. |
| OR-Gym ([hubbs5/or-gym](https://github.com/hubbs5/or-gym)) | Gym environments for knapsack, bin packing, inventory, routing, and other OR problems. MIT license. | No bandit environment. Low fit. |
| Stable-Baselines3 | RL algorithms such as PPO, A2C, and SAC | RL baselines against the index policy. Needs a custom RMAB environment. |
| Google OR-Tools | LP and MIP solvers | An LP relaxation baseline. The RMAB formulation must be written. |
| PuLP | LP modeling in Python | Same use as OR-Tools, with a smaller dependency. |
| JAX | `jit`, `vmap`, `grad` | See [research/jax/README.md](../research/jax/README.md). The prototype returns wrong values. |
| Optax, Flax | Gradient optimizers, neural networks | Research ideas only, such as a neural index approximator. The current solver does not need them. |

Dropped from the earlier survey (`research/libraries/existing_rmab_libraries.md`, in git history):

- **RMABPy, PyRMAB:** no repository confirmed.
- **bayesianbandits:** listed as "mentioned in SAHELI". The SAHELI repository does not mention it.
- **JAX-MD:** a molecular dynamics library with no RMAB use.
- **"RMAB benchmark datasets":** no dataset confirmed.
