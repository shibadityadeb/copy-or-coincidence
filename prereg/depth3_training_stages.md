# Pre-registration: Depth 3, which training stage creates deference?

Written 2026-10-10, after the training-stage pilot and **before** any full Depth 3 output exists. The git commit
time of this file is the timestamp.

## Question
OLMo-3-7B-Instruct (the main model) defers heavily to a peer's reasoning (α ≈ 0.86, Exp 7b). OLMo publishes the
same model at every training stage. Which stage introduces the deference?

## Receivers (stages that passed the pilot rule, `docs/RESEARCH_LOG.md`)
| Stage | Checkpoint | Prompt |
|---|---|---|
| Base | `allenai/Olmo-3-1025-7B` (pretraining only) | plain text + two neutral worked examples (`plain_fewshot`; the one documented fix) |
| SFT | `allenai/Olmo-3-7B-Instruct-SFT` | chat template |
| DPO | `allenai/Olmo-3-7B-Instruct-DPO` | chat template |
| Final | `allenai/Olmo-3-7B-Instruct` (= SFT + DPO + RL) | chat template; **existing Exp 7b data** (receiver agent B) |
RL-Zero-Mix was excluded by the pilot rule (86.1% readable after its one fix) and is not part of this test.

## Design: same peer, different receivers
For Base, SFT and DPO: Layer 0 solo answers (600 `cep_v2` items × K = 10; samples 0–9 give the receiver's null),
then Exp 7b's `seq_steps`, `seq_answer` and `random_answer` (R = 5) with **byte-identical messages** to Exp 7b:
sender = OLMo-3-7B-Instruct agent A's Layer 0 samples 10–14; random answers drawn from the same candidate sets
(built from OLMo agents A and B, as in 7b); message `prompts/peer_v2.txt`. Only the receiver differs. Same
settings, structured JSON, pinned Kaggle stack, checker `f7805da13b9b`. 15,000 answers per new stage.

## Measures (the why1/why2 methods, unchanged)
- Deference weight α per stage × condition: P(y) = (1 − α) p_R(y) + α · 1[y = shown], ε = 0.01, grid MLE.
- Discrimination D = α_right − α_wrong on mixed items (receiver solo accuracy strictly between 0 and 1).
- Exp 7 residuals (same answer, joint error) and the interaction share of joint error under `seq_steps`.
Because every stage sees identical messages, stage contrasts are paired by item; CIs by item bootstrap
(resampling items jointly across stages, 1,000 resamples), p-values by the one-sided bootstrap tail.

## Primary hypotheses (one-sided; Holm across the four; α = 0.05)
- **H1** α_steps(Final) > α_steps(Base): post-training increases deference to reasoning.
- **H2** α_steps(SFT) > α_steps(Base): supervised instruction tuning increases it.
- **H3** α_steps(DPO) > α_steps(SFT): preference tuning increases it further.
- **H4** D_steps(Final) < D_steps(Base): post-training reduces discrimination between right and wrong peers.

## Exploratory (labelled)
The same contrasts for `seq_answer` and `random_answer`; the full α and D curves across the four stages;
interaction share of joint error per stage; accuracy per stage; Final − DPO (the RL stage).

## Validity and exclusions
A stage × condition with > 5% judging replies on number items is invalid for that condition. No item exclusions.
Limitation stated in advance: Base sees a few-shot plain-text prompt, the others a chat template, so Base
contrasts mix "training stage" with "prompt format".
