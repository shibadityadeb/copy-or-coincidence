# Pre-registered analysis plan: is deference rational? (right vs wrong peers, certainty, plausibility)

Written 2026-10-03, after `prereg/why1_n4_tipping.md` and its results (deference-weight model fits best) and
**before** any analysis below is computed. Data already exist (Experiments 7b and 7). The git commit time of this
file is the timestamp; reported as planned after data collection, before analysis.

## Model
Receiver answer y on a run that showed answer s: P(y) = (1 − α) · p_R(y) + α · 1[y = s], smoothed with ε = 0.01
over the item's answer set (as in why1). p_R from Layer 0 samples 0–9 of the receiver. α fitted by maximum
likelihood (grid 0–1, step 0.001) on a subset of runs; 95% CI by item bootstrap (500 resamples).

## Data
Primary: Experiment 7b, `seq_steps`, `seq_answer`, `random_answer` (Qwen: `seq_steps` only). Robustness: Exp 7.
**Mixed items only**: items whose receiver solo accuracy over samples 0–9 is strictly between 0 and 1, so that
deference can be detected for both correct and wrong shown answers. The number of mixed items is reported.

## Analyses
1. **Right vs wrong peer.** α_right (runs whose shown answer is correct) and α_wrong (shown answer wrong, not NA).
   Discrimination D = α_right − α_wrong, with a paired item-bootstrap CI (both refitted on each resample).
   A *blind* receiver has D ≈ 0; a *rational* receiver has D > 0 and α_wrong well below α_right.
   **Prediction:** D > 0 (some discrimination), and α_wrong > 0.5 with reasoning shown for OLMo and Nemotron
   (deference to wrong peers remains strong).
2. **Receiver certainty.** Entropy H of the receiver's solo answers on the item: certain (H = 0, all items, not
   only mixed), some doubt (0 < H ≤ 1 bit), very unsure (H > 1 bit). α per bin for wrong shown answers (for
   H = 0 items the receiver's solo answer is fixed, so α measures how often it abandons it).
   **Prediction:** α increases with uncertainty.
3. **Plausibility.** For wrong shown answers: α when the shown answer has p_R(s) = 0 (the receiver never gives
   it alone) vs p_R(s) > 0. **Prediction:** α higher when p_R(s) > 0.

All analyses per model and condition; no multiplicity correction (descriptive, CIs reported). Exclusions as in
Experiment 7.
