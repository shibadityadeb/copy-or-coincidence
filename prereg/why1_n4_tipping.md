# Pre-registered analysis plan: N4 "tipping" test, deference models, three-way error decomposition

Written 2026-10-03. **Status: analysis plan on existing data.** Experiments 7 and 7b (all three families) have
been run and their pre-registered results are known; **none of the analyses below has been computed yet**.
The git commit time of this file is the timestamp. Labelled in the paper as planned after data collection,
before analysis.

## Data
Primary: Experiment 7b (`outputs/exp7b_{olmo,qwen,nemotron}`), conditions `seq_steps`, `seq_answer`,
`random_answer` (Qwen: `seq_steps` only, per the 7b validity check). Robustness: Experiment 7 (peer_v1) for
OLMo and Nemotron. Per item, the sender distribution p_S and receiver distribution p_R come from Layer 0
samples 0–9 (disjoint from messages, samples 10–14), as in Experiment 7.

## Definitions
- Product distribution q(a) ∝ p_S(a) · p_R(a) over readable answers. **Joint mode** m* = argmax q (items with a
  tie for the max are excluded). **Contested item**: max q < 0.7 (field guide §5, N4).
- **Informative run**: contested item where the shown answer differs from m*.

## Analysis 1: tipping vs transmission (primary)
On informative runs (`seq_steps`), compare P(receiver = shown answer) with P(receiver = m*).
- **Transmission** predicts P(shown) > P(m*); **tipping (N4)** predicts P(m*) > P(shown).
- Baselines for both: the receiver's solo rates p_R(shown) and p_R(m*).
- Report per model: both rates with 95% item-bootstrap CIs, and the per-item paired difference
  P(shown) − P(m*) with CI. Prediction (direction stated now, from the exploratory analysis of OLMo Exp 7):
  **P(shown) > P(m*) for OLMo and Nemotron** (transmission dominates when reasoning is shown).

## Analysis 2: which model of the receiver fits best (theory)
Per model and condition, log-likelihood of every receiver answer under five models, with ε = 0.01 smoothing
(mass ε spread uniformly over the item's answer set, the rest by the model):
1. **Independent (N3)**: p_R.
2. **Mixture**: ½ (p_S + p_R).
3. **Mode-finding (N4)**: point mass on m*.
4. **Pure copy**: point mass on the shown answer.
5. **Deference weight**: (1 − α) p_R + α · 1[shown], with α fitted by maximum likelihood (one α per model ×
   condition), CI by item bootstrap.
Report log-likelihood per answer and AIC (model 5 has one parameter, the rest none). Prediction: model 5 fits
best, with α(`seq_steps`) > α(`seq_answer`) for OLMo and Nemotron.

## Analysis 3: three-way error decomposition (field guide §8), `seq_steps`
Over all receiver answers that are wrong after exposure:
- **Shared**: the receiver's own solo mode (from p_R) is wrong — the error would likely have happened anyway.
- **Interaction-created**: the receiver's solo mode is correct, it was shown a wrong answer, and it is wrong.
  Reported net of the same quantity in `random_answer` (exposure to any wrong answer vs this peer's).
- **Interaction-amplified (lure)**: on contested lure items, lure rate after exposure minus the N4-predicted lure
  rate (q(lure)).
Report shares with item-bootstrap CIs. No directional prediction for the shares.

## Exclusions
Same as Experiment 7 (no item excluded so far; unreadable answers are NA and never match). Items with an
empty readable answer set for an agent's samples 0–9 are skipped and counted.
