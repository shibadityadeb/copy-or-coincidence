# Pre-registration: replication on a third model family (Nemotron-Nano-9B-v2)

Written 2026-10-02, **before** any Nemotron Layer 0 or Experiment 7 output exists, after the OLMo-3-7B results
of Experiments 1 and 7 were known and while Qwen3.5-4B's Layer 0 was still running. The git commit time of
this file is the timestamp.

## Why
All primary results so far come from one model (OLMo-3-7B-Instruct, Allen AI) playing both agents; Qwen3.5-4B
(Alibaba) is the second family (`prereg/replication_qwen.md`). This replicates the identical pipeline with a
third family and lab, chosen by the screening rule in `docs/RESEARCH_LOG.md` (comparable stated training
cutoff, comparable size, closest accuracy to OLMo on our items).

## Model
`nvidia/NVIDIA-Nemotron-Nano-9B-v2` rev `6533e8de` (NVIDIA; hybrid Mamba-2/attention; pretraining cutoff
Sep 2024), agents `configs/agents/nemotron_nano9b_{A,B}.json`: vLLM fp16, tensor parallel 2 on both T4s,
`max_num_seqs` 64, T = 0.7, top-p 0.95, thinking off via the model's `/no_think` system switch, structured
JSON, prompt `solver_v1`, max 1024 tokens. Screening: 87.8% on a 60-item `cep_v2` slice vs OLMo 93.0%.

## What is identical to the OLMo runs
Items (all 600 `cep_v2`), checker `f7805da13b9b` (original scoring), Layer 0 design (K = 20, samples 0–9 for
nulls, 10–19 for Experiment 1 pairs, 10–14 as Experiment 7 messages), Experiment 7 conditions (`seq_steps`,
`seq_answer`, `random_answer`, `seq_steps_rev`, R = 5), message template `peer_v1`, analysis scripts
`analysis/exp1.py` and `analysis/exp7.py`.

## Gate
Experiment 1 on Nemotron's Layer 0 uses the rule in `prereg/exp1_independent_duplicates.md`. **Experiment 7
on Nemotron runs only if it passes.**

## Hypotheses
H1–H5 exactly as in `prereg/exp7_sequential_exposure.md` (one-sided, Holm across the five, permutation p and
item-bootstrap CI both required).

## Replication criterion (decided now)
The OLMo result **replicates** on Nemotron for a hypothesis if that hypothesis is supported on Nemotron (same
sign). Effect sizes may differ; magnitude differences between families are reported as exploratory, with CIs,
and are not by themselves a failure to replicate. The overall finding "interaction creates a share of joint
error beyond the item-conditioned null" replicates if H1 and H4 are both supported on Nemotron.

## Known difference to report
Nemotron uses a `/no_think` system-prompt switch (stripped again by its chat template) instead of the
`enable_thinking` flag the other models use; the instruction text the model sees is otherwise identical.
