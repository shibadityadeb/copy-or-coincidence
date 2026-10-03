# Pre-registration: Experiment 7b, sequential exposure with a clarified peer message

Written 2026-10-03, after the Experiment 7 results for OLMo-3-7B, Qwen3.5-4B and Nemotron-Nano-9B-v2 were
known, and **before** any Experiment 7b output exists. The git commit time of this file is the timestamp.

## Why
In Experiment 7 the peer message (`prompts/peer_v1.txt`) ended with the peer's answer and no instruction.
Qwen3.5-4B often read it as a request to *verify the peer*: it answered number questions with "true"/"false"
in 48.0% of `seq_answer`, 38.5% of `random_answer` and 3.4% of `seq_steps` answers (OLMo and Nemotron: 0% in
every condition; all models 0% in Layer 0). Qwen's answer-only and random conditions therefore did not
measure what they were meant to.

## The only change
`prompts/peer_v2.txt` appends one line: **"Give your final answer to the problem above."** It states what to
answer and deliberately does not ask for independence or reconsideration, which could itself change copying.
Everything else is identical to Experiment 7: items, agents and settings, Layer 0 nulls (samples 0–9), messages
(samples 10–14), conditions (`seq_steps`, `seq_answer`, `random_answer`, `seq_steps_rev`, R = 5), checker
`f7805da13b9b`, analysis `analysis/exp7.py`, and the pinned Kaggle stack (`kaggle/env.json`).

## Models
OLMo-3-7B-Instruct, Qwen3.5-4B, Nemotron-Nano-9B-v2 (configs as in their Experiment 7 runs).

## Validity check (per model and condition, decided now)
"Judging" replies = number items answered with true/false/yes/no/correct/incorrect. If more than 5% of a
condition's number-item answers are judging replies, that condition is reported as invalid for that model and
excluded from its hypothesis tests and from cross-model comparisons.

## Hypotheses
H1–H5 exactly as in `prereg/exp7_sequential_exposure.md`, tested separately for each model (one-sided, Holm
across the five within a model; permutation p and item-bootstrap CI both required).

## How results are reported
- OLMo's original Experiment 7 (peer_v1) remains the pre-registered primary result.
- Experiment 7b is the replication with an identical, clarified protocol for all three families; the
  three-family comparison uses 7b.
- **Framing robustness (secondary):** for OLMo and Nemotron, compare each condition's same-answer and
  joint-error residuals between peer_v1 and peer_v2 (per-item paired differences, item-bootstrap CIs). The
  conclusion "interaction creates a share of joint error" is robust to framing if H1 and H4 are supported
  under both messages.
- Replication criterion across families: H1 and H4 supported (same sign) for each model whose conditions pass
  the validity check.
