# Pre-registration: replication on a second model family (Qwen3.5-4B)

Written 2026-10-02, **before** any Qwen Layer 0 or Experiment 7 output exists, and after the OLMo-3-7B results
of Experiments 1 and 7 were known (`docs/RESEARCH_LOG.md`). The git commit time of this file is the timestamp.

## Why
All primary results so far come from one model (OLMo-3-7B-Instruct, Allen AI) playing both agents. This
replicates the identical pipeline with a model from a different family and lab.

## Model
`Qwen/Qwen3.5-4B` rev `851bf6e8` (Alibaba), agents `configs/agents/qwen35_4b_{A,B}.json`: vLLM fp16 on one T4,
T = 0.7, top-p 0.95, thinking off, structured JSON, prompt `solver_v1`, max 1024 tokens. Its training cutoff
is not stated; this does not matter here because every `cep_v2` item was generated fresh.

## What is identical to the OLMo runs
Items (all 600 `cep_v2`), checker `f7805da13b9b` (original scoring), Layer 0 design (K = 20, samples 0–9 for
nulls, 10–19 for Experiment 1 pairs, 10–14 as Experiment 7 messages), Experiment 7 conditions (`seq_steps`,
`seq_answer`, `random_answer`, `seq_steps_rev`, R = 5), message template `peer_v1`, analysis scripts
`analysis/exp1.py` and `analysis/exp7.py` unchanged in substance (only their input/output paths became arguments).

## Gate
Experiment 1 on Qwen Layer 0 uses the rule in `prereg/exp1_independent_duplicates.md`. **Experiment 7 on Qwen
runs only if it passes.**

## Hypotheses
H1–H5 exactly as in `prereg/exp7_sequential_exposure.md` (one-sided, Holm across the five, permutation p and
item-bootstrap CI both required).

## Replication criterion (decided now)
The OLMo result **replicates** on Qwen for a hypothesis if that hypothesis is supported on Qwen (same sign).
Effect sizes may differ; differences in magnitude between families are reported as exploratory, with CIs, and
are not by themselves a failure to replicate. The overall OLMo finding "interaction creates a share of joint
error beyond the item-conditioned null" replicates if H1 and H4 are both supported on Qwen.

## Known difference to report
Qwen3.5-4B was 98% accurate on the easy `cep_v1` Experiment 0 slice (OLMo 82%), so it may make fewer errors on
`cep_v2`; joint-error and lure tests then have less information. No items will be added to compensate.
