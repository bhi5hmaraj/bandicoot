# Future research

This page surveys methods that can improve participant outcomes when human contact time is scarce. It ends with a ranked research agenda for Bandicoot. The survey covers sources up to 2026-10-14. For RMAB papers and libraries, see [related work](related-work.md). For open design decisions, see [open questions](open-questions.md). For the model, see [RMAB fundamentals](rmab-fundamentals.md).

## The problem

An outreach program has many participants and a small budget of human contacts in each period. The goal is better participant outcomes (engagement, adherence, completion, health results) for each hour of staff time. Better targeting of contacts is one way to reach this goal. Other ways change the budget, make each contact stronger, or change the program itself.

## Main finding

- The two-stage method that Bandicoot copies gave 32.0% fewer engagement drops than standard of care in its first trial [1]. In a replication, it gave a 10% reduction that was not significant (p = 0.48) [2].
- Changes to the contact or the program have moved real outcomes by larger amounts. The outcomes differ, so the comparison is approximate. Examples: +44% immunizations from a bundle of ambassadors, incentives, and reminders [24], and 93% vs. 70% completion from a change of delivery format [25].
- A simple rule that sends a human contact after a lapse raised return to care by 14.1 points, with no model [15].
- Automated agents can take most routine contacts [8]. No adequately powered trial shows that an automated contact equals a human contact on adherence [10, 11].
- The first task for Bandicoot is to make each deployment a valid experiment and to compare the Whittle ranking with simple baselines.

## Directions by lever

Evidence strength uses these labels: RCT (randomized trial), observational, simulation, theory, and preprint (no peer-reviewed venue found).

### (a) Better targeting of contacts

| Approach | Best evidence (effect and comparison) | Strength | Fit for low-resource programs | What it means for Bandicoot |
|---|---|---|---|---|
| Two-stage RMAB (cluster, then Whittle index) | 32.0% fewer drops vs. standard of care, p = 0.044; 23,003 participants, 7 weeks [1]. Replication: 10% fewer, p = 0.48; 9,000 participants, 6 weeks [2] | 2 RCTs, mixed | Medium: needs logged contact and engagement data | This is the current method. Present it as unproven outside its first trial. |
| Decision-focused learning (DFL) | 31% fewer drops vs. standard of care, p = 0.024, in the same trial where two-stage was not significant [2] | RCT (1) | Medium: same data as two-stage, more engineering | Candidate replacement for the cluster-then-count step. See Wang et al. (2023) in [related work](related-work.md). |
| Rank by benefit (uplift), not by risk | Nudge to all: +6.4 points over a 37% baseline. Targeting half captured about 75% of that gain. Targeting the lowest baseline was "detrimental" [3] | RCT data, preprint | Medium: needs randomized contact data | Add uplift and risk rankings as baselines. Do not rank by risk alone. |
| Group-level rules (site, cohort, week) | Theory: individual prediction beats rules from group-level statistics only when inequality between units is low and the budget is high [4] | Theory | High: no model | A cheap baseline that the Whittle ranking must beat. |
| Fairness constraints | ProbFair keeps a positive lower bound on each participant's chance of contact in each step, within the budget; tested on adherence data [5] | Simulation | High: small code change | One option for the minimum-contact extension in the [README](../README.md). |
| LLM-written reward functions | An LLM turns staff priorities into reward code for an RMAB and refines it with simulation feedback [6] | Simulation | Medium | A possible staff interface. Needs a per-group outcome check before use. |
| LLM as the allocator | Average accuracy 0.46, best 0.66. Models missed the areas of highest need [7] | Simulation on public data | Low | Keep a transparent optimizer as the decision maker. |

### (b) Changing the constraint (automated agents, staff copilots)

| Approach | Best evidence (effect and comparison) | Strength | Fit for low-resource programs | What it means for Bandicoot |
|---|---|---|---|---|
| LLM assistant for frontline staff, with escalation to supervisors | 107 days, 20 community health workers, 15 supervisors. Bot answers were 83.6% of responses to clinical questions. Supervisor consensus answers took 58.59 ± 99.18 hours [8] | Observational | High: messaging app, local language, voice input | The escalation queue needs capacity and a deadline. That is an allocation problem. |
| LLM symptom extraction plus a clinician rule engine | 152,421 queries triaged, 18.7% flagged. Recall rose from 0.565 to 0.810. Over-escalation 17.8% [9] | Observational, preprint | High | Accept a calibrated "needs human" flag as a hard constraint or a state. |
| LLM chatbot in place of a human counselor | Validated abstinence 23% vs. 17%, RR 1.38 (95% CI 0.73 to 2.63), n = 154. 71% used the chatbot at least once [10] | Pilot RCT, preprint | Medium: needs a smartphone | No proof of equivalence. A powered trial is necessary. |
| Copilot for staff decisions | 103 clinical officers, 9,691 patients. Treatment failure 2.2% vs. 2.0%, aOR 0.77 (95% CI 0.55 to 1.08) [11] | Cluster RCT, null | Medium: needs an electronic record | Do not plan on copilot gains without a local test. |
| LLM conversation vs. well-made templates | 1,297 parents. No arm raised self-reported vaccination. Templates matched or beat the chatbots on intent [12] | Online RCT | High for templates | Templates chosen by a policy are the safe default. |
| Chatbot plus brief human calls | 10 chatbot sessions plus 5 weekly brief calls vs. enhanced usual care, n = 344. Effect sizes 0.70 (anxiety) and 0.61 (depression) at 3 months [13]. LLM use not stated | RCT | High: tested in a middle-income country | Supports "automated routine contacts, few targeted human contacts". |
| Chatbot programs on messaging platforms | N = 1,293 in 3 countries. 93.8% completed less than 25% of the content. Platform rules restrict follow-up after non-response [14] | Observational (mixed methods) | Medium | A lapsed participant can be out of reach for a bot. A human contact keeps its value. |

### (c) Adaptive design and evaluation

| Approach | Best evidence (effect and comparison) | Strength | Fit for low-resource programs | What it means for Bandicoot |
|---|---|---|---|---|
| Sequential randomized trial (SMART) with a human contact after a lapse | 1,809 participants. Of 312 who lapsed, 69.1% returned with a peer navigator vs. 55.7% with standard outreach, +14.1 points (95% CI 0.6 to 27.6). SMS vs. standard care: +4.2 points (95% CI -0.7 to 9.2) [15] | RCT | High: a rule, no model | The lapse rule is the baseline to beat, and a default for small programs. |
| Micro-randomized trial of cheap prompts | A notification raised next-hour app use 3.5-fold (95% CI 2.91 to 4.25). Time to disengagement did not differ between arms [16] | RCT | High for digital prompts | Judge a reward on later outcomes, not on next-period engagement. |
| Bandit for contact timing | Call pick-up 0.463 vs. 0.448 with random timing, p = 0.0006; 6,490 vs. 6,416 participants, 2 weeks [17] | RCT, preprint | High: needs call logs | A "when" model can sit next to the "who" ranking. |
| Valid inference for index policies (subgroup estimator) | Re-analysis of [2]: no positive average effect for two-stage; significant effects for participants called in the first weeks. Works better with small budgets, so trials cost less [18] | Re-analysis of an RCT, preprint | High: analysis code | Add the estimator to the evaluation tools. |
| Multi-wave experiments to choose a policy | Exploration sampling beat non-adaptive designs and bandit algorithms in calibrated simulations. Used to choose among 6 recruitment strategies in India [19] | Theory and simulation, with a field use | High for a few variants | Use it to choose among contact variants, for example call vs. message. |
| LLM-simulated participants | 500 simulated participants over 40 weeks. Optimistic bias, accuracy falls over time, and outputs are not causal [20] | Simulation, preprint | Medium: cheap, unvalidated | A pre-screen for failures. Not evidence that one policy beats another. |

### (d) Program and behavioral design

| Approach | Best evidence (effect and comparison) | Strength | Fit for low-resource programs | What it means for Bandicoot |
|---|---|---|---|---|
| SMS reminders | 18 studies, 32,712 infants, 11 countries. Coverage RR 1.16 (95% CI 1.10 to 1.21), I² 90.4% [21] | Meta-analysis | High: needs phone numbers and due dates | The cheap channel for all participants. Human contacts go on top. |
| Message nudges at scale | Journal nudges average +8.7 points. Nudge-unit nudges average +1.4 points (126 RCTs, 23 million people) [22] | Meta-analysis of RCTs | High | Expect small effects from message changes. Test each one. |
| Information-only voice messages | 5,095 participants. No effect on the primary outcome, RR 1.04 (95% CI 0.88 to 1.23). 44% changed SIM cards and stopped receiving calls [23] | RCT | High at scale | Engagement with content is not the outcome. Reachability needs its own state. |
| Bundles (ambassadors, incentives, reminders) | Best policy: +44% immunizations. Most cost-effective: +9.1% immunizations per dollar. Both adjusted for the winner's curse [24] | Cluster RCT | High: needs a one-time network survey | The strength of the contact sets the ceiling for targeting. |
| Change of delivery format | Remote rehabilitation completion 93% (95% CI 90 to 96) vs. 70% for in-person, with little or no difference in walk distance [25] | Review of RCTs and controlled trials | High where phones exist | A format change can exceed any measured targeting gain. |

## Research agenda for Bandicoot

Ranked by value and by order of need. Item 1 makes items 2 to 8 testable.

1. **Make every deployment a valid experiment.** Why: a top-K ranking is deterministic, so its logs cannot evaluate another policy. The two-stage result did not replicate [2]. Test: add a random holdout and a randomized share of contacts near the cut-off, log the probability of each contact, and add the subgroup estimator [18]. In the learned MDP, check that the confidence intervals reach their nominal coverage.
2. **Benchmark against simple baselines.** Why: a lapse rule gave +14.1 points [15], risk ranking can hurt [3], and group-level rules can match prediction [4]. Test: add round robin, random, lapse rule, risk ranking, group-level rule, and uplift ranking to `experiments/`. Compare outcome per contact on simulated programs and on randomized logs.
3. **Run a field test of human vs. automated follow-up.** Why: the only head-to-head trial is a pilot [10], a copilot trial was null [11], and a hybrid design worked [13]. Test: in a partner program, randomize lapsed participants to a human contact, an automated conversational contact, or a standard template. Use adherence or completion as the primary outcome. Pre-register the analysis.
4. **Allocate across contact types with an escalation queue.** Why: bots answered 83.6% of questions, but escalations waited 58.59 hours on average [8], and 18.7% of queries were flagged [9]. Test: extend the solver to actions {none, automated, human} with costs, and add a queue with a deadline for flagged participants. In simulation, check that every flag meets its deadline within the staff-hours budget.
5. **Check the reward against a real outcome.** Why: prompts raised short-term engagement 3.5-fold but did not change time to disengagement [16]. A voice program did not move its primary outcome [23]. Test: in each deployment, link the engagement state to one program outcome, such as completion or attendance. Report the effect on both.
6. **Add a decision-focused training path.** Why: DFL had the stronger field result in the same trial [2]. Test: train both paths on the same randomized logs. Compare them with the subgroup estimator [18].
7. **Model "unreachable" and "never started" as states.** Why: 44% of participants in one program changed SIM cards [23], and 93.8% in another completed less than 25% of the content [14]. Test: add an N-state model with reachability actions, such as an alternate number or a first-week contact. Report the share of participants in each state.
8. **Add a contact-timing model.** Why: a timing bandit raised call pick-up from 0.448 to 0.463 [17]. Test: A/B test a per-participant time slot on pick-up and on later engagement.

## Risks and when not to use AI targeting

- **Equity.** A ranking can move contacts away from some groups. An LLM allocator missed the areas of highest need [7]. Report outcomes per group, and use a minimum-contact constraint [5].
- **Privacy.** The model needs logs for each participant. An LLM agent can send participant messages to an outside service. Collect the minimum data, get consent, and keep identifiers out of prompts.
- **Safety.** An automated agent can miss a danger sign, and the human escalation step can be slow [8]. Use a rule engine for danger signs [9] and a deadline for each escalation.
- **Small programs.** Few contacts give few observations of what a contact does. Use a lapse rule, which needs no model [15], until randomized data exists.
- **Homogeneous programs.** If a contact has a similar effect on all participants, the order of contacts does not change the total effect. Round robin is then sufficient.
- **High budget fraction.** The gain from targeting falls as more participants get a contact. In one trial, 60% of an arm got a call, and a re-analysis could not show a positive average effect for the two-stage method [18].
- **Weak contacts.** Targeting cannot make an ineffective contact effective. Make the contact or the program stronger first [24, 25].
- **Proxy outcomes.** Do not report fewer engagement drops as program impact until a real outcome confirms it [23].

## References

1. Mate, A., et al. (2022). "Field Study in Deploying Restless Multi-Armed Bandits: Assisting Non-Profits in Improving Maternal and Child Health." *AAAI*. [arXiv:2109.08075](https://arxiv.org/abs/2109.08075)
2. Verma, S., et al. (2023). "Restless Multi-Armed Bandits for Maternal and Child Health: Results from Decision-Focused Learning." *AAMAS*. [PDF](https://www.southampton.ac.uk/~eg/AAMAS2023/pdfs/p1312.pdf)
3. Athey, S., Keleher, N., and Spiess, J. (2023). "Machine Learning Who to Nudge: Causal vs Predictive Targeting in a Field Experiment on Student Financial Aid Renewal." Preprint. [arXiv:2310.08672](https://arxiv.org/abs/2310.08672)
4. Shirali, A., Abebe, R., and Hardt, M. (2024). "Allocation Requires Prediction Only if Inequality Is Low." *ICML*. [arXiv:2406.13882](https://arxiv.org/abs/2406.13882)
5. Herlihy, C., et al. (2023). "Planning to Fairly Allocate: Probabilistic Fairness in the Restless Bandit Setting." *KDD*. [doi:10.1145/3580305.3599467](https://doi.org/10.1145/3580305.3599467)
6. Behari, N., et al. (2024). "A Decision-Language Model (DLM) for Dynamic Restless Multi-Armed Bandit Tasks in Public Health." *NeurIPS*. [arXiv:2402.14807](https://arxiv.org/abs/2402.14807)
7. Afane, M., Wang, Y., and Chen, J. (2025). "Can LLMs Help Allocate Public Health Resources? A Case Study on Childhood Lead Testing." *IEEE BigData*. [arXiv:2511.18239](https://arxiv.org/abs/2511.18239)
8. Ramjee, P., et al. (2025). "ASHABot: An LLM-Powered Chatbot to Support the Informational Needs of Community Health Workers." *CHI*. [doi:10.1145/3706598.3713680](https://doi.org/10.1145/3706598.3713680)
9. Jagga, S., et al. (2026). "Auditable Emergency Triage for Maternal and Newborn Care in India." Preprint. [arXiv:2609.09356](https://arxiv.org/abs/2609.09356)
10. Luk, T. T., et al. (2026). "Generative AI chatbot vs telephone counseling for youth tobacco cessation: a pragmatic pilot randomized trial." Preprint, *Research Square*. [doi:10.21203/rs.3.rs-8048239/v1](https://doi.org/10.21203/rs.3.rs-8048239/v1)
11. Agweyu, A., et al. (2026). "Generative AI-enabled clinical decision support system in primary care: a pragmatic, cluster-randomized trial." *Nature Medicine*. [doi:10.1038/s41591-026-04503-6](https://doi.org/10.1038/s41591-026-04503-6)
12. Sehgal, N. K. R., et al. (2026). "Large Language Model Chatbot Conversations vs Public Health Materials and Parental HPV Vaccination Intentions: A Randomized Clinical Trial." *JAMA Network Open*. [doi:10.1001/jamanetworkopen.2026.16822](https://doi.org/10.1001/jamanetworkopen.2026.16822)
13. Bryant, R. A., et al. (2026). "A guided chatbot-based psychological intervention for psychologically distressed older adolescents and young adults: a randomised clinical trial in Jordan." *npj Digital Medicine*. [doi:10.1038/s41746-025-02142-8](https://doi.org/10.1038/s41746-025-02142-8)
14. Klapow, M. C., et al. (2026). "Chatbot-based health interventions in low- and middle-income countries: effective access, early attrition, and design strategies from a mixed-methods study." *npj Digital Public Health*. [doi:10.1038/s44482-026-00027-5](https://doi.org/10.1038/s44482-026-00027-5)
15. Geng, E. H., et al. (2023). "Adaptive Strategies for Retention in Care among Persons Living with HIV." *NEJM Evidence* 2(4). [doi:10.1056/EVIDoa2200076](https://doi.org/10.1056/EVIDoa2200076)
16. Bell, L., et al. (2023). "How Notifications Affect Engagement With a Behavior Change App: Results From a Micro-Randomized Trial." *JMIR mHealth and uHealth*. [doi:10.2196/38342](https://doi.org/10.2196/38342)
17. Dasgupta, A., et al. (2025). "Learning to Call: A Field Trial of a Collaborative Bandit Algorithm for Improved Message Delivery in Mobile Maternal Health." Preprint. [arXiv:2507.16356](https://arxiv.org/abs/2507.16356)
18. Boehmer, N., et al. (2024). "Evaluating the Effectiveness of Index-Based Treatment Allocation." Preprint. [arXiv:2402.11771](https://arxiv.org/abs/2402.11771)
19. Kasy, M., and Sautmann, A. (2021). "Adaptive Treatment Assignment in Experiments for Policy Choice." *Econometrica* 89(1), 113-132. [doi:10.3982/ECTA17527](https://doi.org/10.3982/ECTA17527)
20. Martinson, S., et al. (2025). "LLM-based Agent Simulation for Maternal Health Interventions: Uncertainty Estimation and Decision-focused Evaluation." Preprint. [arXiv:2503.22719](https://arxiv.org/abs/2503.22719)
21. Eze, P., Lawani, L. O., and Acharya, Y. (2021). "Short message service (SMS) reminders for childhood immunisation in low-income and middle-income countries: a systematic review and meta-analysis." *BMJ Global Health*. [doi:10.1136/bmjgh-2021-005035](https://doi.org/10.1136/bmjgh-2021-005035)
22. DellaVigna, S., and Linos, E. (2022). "RCTs to Scale: Comprehensive Evidence from Two Nudge Units." *Econometrica* 90(1), 81-116. [doi:10.3982/ECTA18709](https://doi.org/10.3982/ECTA18709)
23. LeFevre, A. E., et al. (2022). "The impact of a direct to beneficiary mobile communication program on reproductive and child health outcomes: a randomised controlled trial in India." *BMJ Global Health*. [doi:10.1136/bmjgh-2022-008838](https://doi.org/10.1136/bmjgh-2022-008838)
24. Banerjee, A., Chandrasekhar, A. G., et al. (2025). "Selecting the Most Effective Nudge: Evidence from a Large-Scale Experiment on Immunization." *Econometrica* 93(4), 1183-1223. [doi:10.3982/ECTA19739](https://doi.org/10.3982/ECTA19739)
25. Cox, N. S., et al. (2021). "Telerehabilitation for chronic respiratory disease." *Cochrane Database of Systematic Reviews*. [doi:10.1002/14651858.CD013040.pub2](https://doi.org/10.1002/14651858.CD013040.pub2)
