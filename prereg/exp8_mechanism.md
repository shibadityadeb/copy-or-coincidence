# Pre-registration: Experiment 8, what in a peer's reasoning persuades?

Written 2026-10-10, after Experiments 7/7b and the why-analyses (`prereg/why1_n4_tipping.md`,
`prereg/why2_rational_deference.md`) and **before** any Experiment 8 output exists. The git commit time of this
file is the timestamp.

## Motivation
Receivers defer to a peer's reasoning almost blindly (α_wrong ≈ 0.88 with reasoning shown vs 0.24 for the same
wrong answer alone, Nemotron). Reasoning bundles an *argument* (steps) and a *conclusion* (final answer), and has
both *content* and the mere *form* of careful work. Experiment 8 separates them.

## Design
Identical to Experiment 7b (items, agents, settings, Layer 0 nulls from samples 0–9, sender messages from A's
Layer 0 samples 10–14, receiver B, R = 5, message `prompts/peer_v2.txt`, checker `f7805da13b9b`, pinned Kaggle
stack) except the content of the peer block (`coc/sequential.py`):

| Condition | Receiver sees | Shown answer s | Argued answer |
|---|---|---|---|
| `steps_redacted` (guide E) | A's steps with A's final answer masked as "[...]" wherever stated (numbers; true/false/yes/no/"follows"; "unanswerable" phrases); no final-answer line | — (A's answer is hidden) | A's answer |
| `steps_flipped` (guide F, N10) | A's real steps followed by "Its final answer: s", s ≠ A's answer: uniform over the item's other candidate answers; fallback true↔false, the complete-problem answer for missing-premise items, else 2× the number | s | A's answer |
| `steps_mismatched` (form control) | steps of A's sample 10+r on a *different* item of the same template (chosen uniformly, seeded), followed by A's real final answer for this item | A's answer | — |

Known limitations: masking cannot remove intermediate results from which the answer can be inferred
("2x = 60"); mismatched steps carry their own numbers and conclusion for the other item.

Models: OLMo-3-7B, Qwen3.5-4B, Nemotron-Nano-9B-v2 (`experiments/exp8_{olmo,qwen,nemotron}.json`), 9,000
receiver answers each.

## Validity check
As in 7b: a condition is invalid for a model if > 5% of its number-item answers are verdicts on the peer
(true/false/yes/no/correct/incorrect).

## Primary hypotheses (per model; one-sided; Holm across the four within a model; α = 0.05)
Residuals are item-conditioned exactly as in Experiment 7 (`analysis/exp7.py`), with "shown" = A's answer
unless stated.
- **H1 argument alone persuades.** `steps_redacted`: same-answer residual between the receiver and A's (hidden)
  answer > 0.
- **H2 conclusion beats argument.** `steps_flipped`, per item: mean over runs of
  [1(receiver = s) − p_B(s)] − [1(receiver = A's answer) − p_B(A's answer)] > 0 (follow the attached conclusion
  more than the argued answer, each relative to the receiver's solo rate).
- **H3 form persuades.** Per-item same-answer residual: `steps_mismatched` − Exp 7b `seq_answer` > 0
  (same shown answers, run for run).
- **H4 content persuades.** Per-item same-answer residual: Exp 7b `seq_steps` − `steps_mismatched` > 0.

Inference: H1 within-item permutation p (2,000 shuffles) and 95% item-bootstrap CI; H2–H4 per-item differences
with 95% item-bootstrap CI and one-sided sign-flip permutation p (2,000). A hypothesis is supported if its
Holm-adjusted p < 0.05 and its CI excludes 0. H3/H4 compare with Exp 7b runs made a week earlier on the same
pinned stack; reported as such.

## Exploratory (labelled)
Deference weight α per condition and for right vs wrong shown answers (why2 method); receiver accuracy;
H2 split by whether A's argued answer is right or wrong; per-family breakdowns; how often redacted replies
still recover A's exact answer when A was wrong.

## Exclusions
As in Experiment 7. Sample size fixed (600 items × 5 runs × 3 conditions per model); no optional stopping.
