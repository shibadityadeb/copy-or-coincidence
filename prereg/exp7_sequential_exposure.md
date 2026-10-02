# Pre-registration: Experiment 7, sequential exposure

Written 2026-10-02, **before** any Experiment 7 output exists. The git commit time of this file is the
timestamp. Any later change is a deviation and must be reported as such.

## Question
When agent B answers after seeing agent A's answer, how much agreement and shared error appears beyond
what the two agents' independent per-item answer distributions predict; in which direction (toward the
truth or the lure); and how much of it is content-blind copying?

## Agents and items
- OLMo-3-7B-Instruct, agent configs `configs/agents/olmo3_7b_{A,B}.json` (identical to Layer 0: fp16,
  T = 0.7, top-p 0.95, thinking off, structured JSON, prompt `solver_v1`).
- All 600 `cep_v2` items; no exclusions beyond the rules below.
- Scoring: checker `f7805da13b9b` (the Layer 0 / Experiment 1 scoring; syllogism "unanswerable" is a distinct,
  wrong answer).

## Conditions (R = 5 runs per item per condition; 3,000 receiver answers each)
| Condition | Receiver | Receiver sees | Guide label |
|---|---|---|---|
| `seq_steps` | B | A's Layer 0 sample `10+r` (r = 0…4): its steps and final answer | B (observed, steps) |
| `seq_answer` | B | the same A sample's final answer only | B (observed, answer only) |
| `random_answer` | B | an answer drawn uniformly at random from the item's candidate set, in the answer-only format | C |
| `seq_steps_rev` | A | B's Layer 0 sample `10+r`: steps and final answer | replication / order |

Candidate set for `random_answer`: the distinct readable answers given by A or B anywhere in Layer 0 for that
item, plus the correct answer and the lure; uniform over that set; seeded per (item, r).

Message (appended to the question, `prompts/peer_v1.txt`): "Another agent solved this problem
independently." followed by either its steps and final answer or only its final answer. No instruction to
agree, disagree or reconsider.

## Null (expected) values
Per item, from Layer 0 samples 0–9 of each agent (disjoint from the messages, which are samples 10–14):
- shown-agent distribution p_S: Layer 0 of the agent whose answer is shown; for `random_answer`, the exact
  uniform candidate distribution;
- receiver distribution p_R: Layer 0 of the receiving agent.
Expected same answer = Σ_a p_S(a) p_R(a); expected joint error = e_S e_R; expected both-on-lure
= p_S(lure) p_R(lure). Observed values pair the shown answer of run r with the receiver's answer in run r.

## Primary hypotheses (one-sided; Holm-corrected across the five; α = 0.05)
- **H1** `seq_steps`: same-answer residual Δ_ans > 0.
- **H2** Δ_ans(`seq_steps`) − Δ_ans(`seq_answer`) > 0 (paired by item).
- **H3** `random_answer`: Δ_ans > 0 (receiver adopts a content-free peer answer beyond chance).
- **H4** `seq_steps`: joint-error residual Δ_J > 0.
- **H5** `seq_steps`, lure items only: both-on-lure residual Δ_lure > 0.

## Inference
- H1, H3, H4, H5: within-item permutation test (shuffle the receiver's runs within each item, 2,000 shuffles,
  one-sided p) **and** 95% item-bootstrap CI (2,000 resamples). A hypothesis is supported if its Holm-adjusted
  permutation p < 0.05 and the CI excludes 0.
- H2: per-item difference of residuals between the two conditions; 95% item-bootstrap CI and a one-sided
  sign-flip permutation test on the per-item differences (2,000 draws). Supported if Holm-adjusted p < 0.05
  and the CI excludes 0.
- Unit of analysis: the item. Effect sizes are reported with CIs whatever the p-values.

## Exploratory (labelled as such when reported)
Per-family and per-error-cause residuals; `seq_steps_rev` vs `seq_steps` (order; expected equal, because A
and B share weights); receiver accuracy by condition; whether the receiver follows a wrong shown answer more
when the shown agent's answer was the lure; adoption rate of the shown answer as a function of how often the
receiver gives that answer alone; same-wrong-answer residual.

## Exclusions
- Items flagged by the human audit as wrong or ambiguous: none so far (30/30 agreed).
- Unreadable receiver answers are kept as NA (counted wrong, never "the same answer").
- If a Kaggle run fails part-way, resumed trials are kept; no trial is re-run because of its content.
- No other exclusions. Sample size is fixed at 600 items × 5 runs; no optional stopping.
