---
license: cc-by-4.0
language:
- en
pretty_name: "Copy or Coincidence: Correlated Error Probe (CEP v2)"
size_categories:
- n<1K
task_categories:
- question-answering
tags:
- multi-agent
- llm-evaluation
- error-correlation
- reasoning
- synthetic
- contamination-free
configs:
- config_name: default
  data_files:
  - split: test
    path: data/test.jsonl
---

# Copy or Coincidence: Correlated Error Probe (CEP v2)

> **Canary:** `{{CANARY}}`
> Please do not train on this dataset. Every row carries this string so it can be filtered from training corpora.

600 short reasoning questions built to study **when several LLM agents give the same wrong answer,
how much of that agreement each agent's own behaviour already predicts, and how much is caused by the
agents interacting**. Half of the items have a **pre-specified lure**: the tempting wrong answer the
question is designed to elicit, so "both agents converged on the lure" can be measured directly.

- **Code, generators, experiments:** https://github.com/shibadityadeb/copy-or-coincidence
- **Every item was generated fresh** for this release (seed 1), so it cannot appear in any model's
  training data from before September 2026.

## Composition

| Family | Generator | Items | Lure | `error_cause_by_construction` |
|---|---|---|---|---|
| `lure` | 20 classic intuitive-error templates (bat-and-ball, widgets, lily pads, overtaking, siblings, average speed, fence posts, handshakes, snail in a well, …) with fresh numbers and wording | 200 | intuitive answer | `intuitive_lure` |
| `logic` | False-world rule chains that contradict common knowledge ("Every whale is a fish…"), 25 cases × 2 polarities × 2 depths | 100 | common-sense answer | `prior_override` |
| `logic` | Categorical syllogisms (Yes/No), 50 valid + 50 invalid, generated with Reasoning Gym 0.1.25 | 100 | — | `deduction_slip` |
| `math` | Multi-step word problems, 10 templates | 100 | — | `multi_step` |
| `math` | The same templates with one needed quantity replaced by a vague phrase; correct answer is `UNANSWERABLE` | 100 | — | `missing_premise` |

## Fields

| Field | Description |
|---|---|
| `item_id` | Stable id, e.g. `cep_v2-lure-035` |
| `family` | `lure`, `logic` or `math` |
| `template_id` | Template or source; items sharing a template share structure (use as a random effect) |
| `error_cause_by_construction` | Why the item is expected to cause errors (see table) |
| `question` | Prompt text |
| `answer_type` | `number` or `bool` |
| `correct` | Canonical answer: a number string (`"12"`, `"67.5"`), `TRUE`/`FALSE`, or `UNANSWERABLE` |
| `lure` | Canonical tempting wrong answer, or null |
| `difficulty_param` | Number of operations (math) or rule depth (false-world); null otherwise |
| `source` | Generator and instance id |
| `meta` | JSON string with the generator parameters (e.g. the numbers used), so answers can be re-derived |
| `canary` | The canary string above |

Answers should be compared after normalisation; the reference normaliser and checker are in the GitHub
repo (`cep/normalize.py`, `cep/checker.py`, version `{{CHECKER}}`). No LLM judge is involved in grading.

## How the answer keys were verified

1. **Independent solver on all 600 items** (`analysis/verify_keys.py`), written separately from the
   generators: syllogisms by enumerating every set-model over the three terms under both modern and
   Aristotelian (existential-import) semantics; false-world items by forward chaining; trick questions
   by simulation; math by separately written formulas. **600/600 keys confirmed.**
2. **Wording review** of a 30-item sample by an LLM, which led to two generator fixes before release
   (scope-ambiguous negations rewritten as "No X is P"; distractor facts never mention the queried property).
3. **Human audit** of a stratified 30-item sample (10 per family) by the author, answering independently:
   **{{N_AUDIT}}/{{N_AUDIT}} agree with the key, none unclear** (`human_audit.csv`).

Syllogisms whose validity depends on existential import ("Some X are Y" drawn from All/No premises)
were removed, so every key holds under both logic conventions. Valid and invalid syllogisms are balanced.

## Intended use

- Measuring item-conditioned error correlation between LLM agents, and the effect of interaction
  (sequential exposure, debate, critique) on shared errors.
- Measuring lure capture and whether models answer unanswerable questions.

Not intended as a general capability leaderboard: the items are short, templated and English-only.

## Limitations

- Synthetic and template-based; surface variety is limited within a template.
- Lures exist only for the `lure` family and false-world logic items (300 of 600).
- Missing-premise items have no lure: the hidden quantity is random, so no single wrong answer is privileged.
- Syllogisms use real-world nouns in arbitrary relations, so belief bias is present but not controlled.

## Reproducibility

`python -m cep.build --version cep_v2` in the GitHub repo regenerates the items byte-identically
(items SHA-256 `{{SHA}}`). The generators also accept other seeds, so fresh, never-published item sets
can be made at any time.

## Licence

CC-BY-4.0. Syllogism items were generated with [Reasoning Gym](https://github.com/open-thought/reasoning-gym)
(Apache-2.0); all other items come from this project's own generators.

## Citation

```bibtex
@misc{deb2026copyorcoincidence,
  title  = {Copy or Coincidence: Correlated Error Probe (CEP v2)},
  author = {Deb, Shibaditya},
  year   = {2026},
  url    = {https://github.com/shibadityadeb/copy-or-coincidence}
}
```
