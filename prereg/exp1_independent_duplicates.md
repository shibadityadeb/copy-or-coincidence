# Pre-registration: Experiment 1, independent duplicates

Written 2026-10-02, **before** any Layer 0 output was downloaded or inspected. The git commit time of
this file is the timestamp. Any later change to this file is a deviation and must be reported as such.

## Question
Does the item-conditioned null model return zero residual for two agents that cannot influence each other?
This is a calibration of the instrument, not a research finding (field guide §7, Experiment 1).

## Data
`experiments/layer0_olmo.json`: OLMo-3-7B-Instruct agents A and B (same weights, prompt and settings;
different seeds), 600 `cep_v2` items, K = 20 independent samples each. No interaction of any kind.

## Split (fixed in advance)
For each item and agent: samples 0–9 estimate the agent's answer distribution; samples 10–19 form the
observed pairs, A's sample 10+r paired with B's sample 10+r (r = 0…9). Observed and expected never share samples.

## Metrics (all item-conditioned, `coc/nulls.py`)
joint_error, same_answer, same_wrong_answer, both_lure (lure items only). For contrast only: the naive
global joint-error excess (N1).

## Inference
Residual = mean over items of (observed − expected). 95% CI from 2,000 item-bootstrap resamples.
One-sided within-item permutation test, 1,000 shuffles of B's runs within each item.

## Prediction and pass rule
- **Pass** if, for every metric, overall **and** within each family (lure / logic / math), the 95% CI
  contains 0 **and** |residual| < 0.02.
- Also expected (not part of pass/fail): naive global excess > 0.
- **Fail** → pipeline bug or leakage between A and B (shared seed, batching, caching). Stop and diagnose;
  do not run Experiment 7 until Experiment 1 passes.

## Exclusions (fixed in advance)
- Items found wrong or ambiguous by the human audit are excluded from all analyses and listed.
- Unreadable answers are kept as `NA` (counted wrong, never "the same answer"); the NA rate is reported per family.
- No other exclusions.
