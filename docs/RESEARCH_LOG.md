# Research log: copy-or-coincidence

The single running record of this project: what we are doing, what we used, what we decided and why,
and what we found. Updated at the end of every step. Newest entries go at the top of each log section.

- Plan we follow: *Excess Error Correlation in Multi-Agent LLM Systems: a research field guide* (Sept 2026)
- Plain-language overview: [`project-explainer.html`](../project-explainer.html)
- Code: https://github.com/shibadityadeb/copy-or-coincidence

---

## 1. The project in one paragraph

When two AI agents give the same wrong answer, three different things could be going on: the question
was simply hard for both (difficulty), both share the same blind spot and would make that mistake
alone (shared prior), or one changed its answer because it saw the other's (interaction). Most
published work counts "both wrong" against a naive baseline that ignores question difficulty, and so
overstates the third. We measure, question by question, how much joint error each agent's **solo**
behaviour already predicts, and attribute only the **leftover (residual)** to interaction. Then we
break the residual down: did agents move toward the truth or the lure, is it blind copying or
evaluation, and does who-speaks-first matter.

**Research questions**
- **Q1, similarity:** working alone, how similar are two agents' per-question answer profiles, by model
  family and error type?
- **Q2, dependence:** when one agent sees the other's answer, how much extra agreement appears beyond
  the solo prediction, in which direction, and by what mechanism?

## 2. Status

| # | Step | Status |
|---|---|---|
| 0 | Read guide, plain-language explainer | ✅ 2026-09-30 |
| 1 | Item set `cep_v1` + programmatic checker + tests | ✅ 2026-10-01 |
| 2 | Model runner (Mac + Kaggle), Experiment 0 sanity | ✅ 2026-10-01 (one open item: GPU wording drift, see Findings) |
| 2b | Contamination-proof setup: OLMo-3-7B main model + generated-only `cep_v2` (600 items) | ✅ 2026-10-02 |
| 2a | Item audit: independent solver on all 600 keys ✅; LLM wording review of 30 ✅ (2 design flaws fixed); human audit 30/30 ✅ | ✅ 2026-10-02 |
| 3 | Layer 0: each agent answers all 600 items × 20 alone (Kaggle) | ✅ 2026-10-02 (24,000 answers, 3.4 GPU-h) |
| 4 | Checker validation vs 150 hand-labelled answers (target ≥95% / ≥85%) | ⏳ |
| 5 | Null-model code validated on simulated data; **Experiment 1 PASS** on real data | ✅ 2026-10-02 |
| 6 | Experiment 7: A→B (steps / answer only), B→A, random-answer control | ✅ 2026-10-02 — **all 5 pre-registered hypotheses supported** |
| 7 | Analysis + write-up | ⏳ |
| 8 | Publish dataset on Hugging Face as `copy-or-coincidence` (CC-BY-4.0, public, canary GUID `92afb6b4-…`) | ⏳ **at the end**, after final tweaks; prepared by `release/make_hf_release.py` |

## 3. What we are using

### Models
| Role | Model | Exact version | Where | Notes |
|---|---|---|---|---|
| **Agents A and B (main)** | `allenai/Olmo-3-7B-Instruct` | rev `6e5971d9`; **training cutoff Dec 2024**; training data public (Dolma 3) | Kaggle, vLLM 0.30, fp16, both T4s (tensor parallel 2) | E0: 82% accuracy, 9/60 lure hits, 100% JSON, stable answers |
| **Second family (replication)** | `google/gemma-4-E4B-it` (8B total, ~4B effective) | rev `ee0ef602`; **training cutoff Jan 2025** | Kaggle, both T4s | Does not start under vLLM's default attention on T4; FlexAttention via engine args still to test |
| Superseded | `Qwen/Qwen3.5-4B` | rev `851bf6e8`; training cutoff **not stated** | Kaggle | Used for Exp 0 only; dropped because its training data can't be dated |
| Mac development copy | `mlx-community/Qwen3.5-4B-4bit` | rev `0e7ffd5c` | Mac, mlx-lm, 4-bit | Dev only, never reported |

Agent settings (`configs/agents/qwen35_4b_*.json`): temperature 0.7, top-p 0.95, max 1024 output
tokens, thinking mode **off**, prompt `prompts/solver_v1.txt`, one fixed seed per answer derived from
(agent, item, protocol, sample number).

### Item set `cep_v2` (current): every item generated fresh, seed 1
| Group | Generator | n | Lure | Error cause |
|---|---|---|---|---|
| Trick questions | `cep/generators/crt.py` (20 templates × 10) | 200 | intuitive answer | `intuitive_lure` |
| False-world logic | `cep/generators/false_ontology.py` (25 cases × 2 polarities × 2 depths) | 100 | common-sense answer | `prior_override` |
| Syllogisms (Yes/No), 50 valid + 50 invalid | Reasoning Gym 0.1.25 `syllogism` (Apache-2.0, first released Feb 2025), filtered | 100 | none | `deduction_slip` |
| Math, complete | `cep/generators/math_word.py` (10 templates × 10) | 100 | none | `multi_step` |
| Math, one quantity made vague | same | 100 | none | `missing_premise` |

600 items, 300 with a lure; hash in `datasets/cep_v2/manifest.json`. No item exists in any public dataset,
so no model's training data can contain it, whatever its cutoff.

### Superseded item set `cep_v1` (kept frozen, used only for Exp 0)
GSM-Plus (`qintongli/GSM-Plus` @ `3b708db5`, CC-BY-SA-4.0; 100 items), ProntoQA (`renma/ProntoQA` @ `6f3e0386`,
MIT; 50 items), plus 150 generated items. Dropped because GSM-Plus (2024) and ProntoQA (2022) predate every
candidate model's training cutoff.

### Tools and infrastructure
| What | Version / detail |
|---|---|
| Python (Mac) | 3.11 in `.venv` (uv) |
| Mac | Apple M3, 8 GB RAM; mlx-lm 0.32.0, mlx 0.32.3; ~32 tokens/s |
| Kaggle | 2× Tesla T4 (15 GB each, compute capability 7.5), 30 GPU-h/week; Python 3.12, torch 2.10+cu128; vLLM 0.30.0 installed per job; `max_num_seqs` 128 |
| Kaggle access | Kaggle CLI 2.2.4, account `debshibaditya`, jobs pushed by `kaggle/push.py` (clones a pinned git commit) |
| Grading | `cep/parse.py` → `cep/normalize.py` → `cep/checker.py`; checker version `f7805da13b9b`; no LLM judge |
| Logs | one JSONL row per answer (`coc/schema.py`, ~50 fields), append-only, resumable |

## 4. Decisions (and why)

| Date | Decision | Why | Alternatives considered |
|---|---|---|---|
| 2026-10-02 | **Third family = Nemotron-Nano-9B-v2** (by the rule in the next row; Phi-4-mini ineligible) | Only eligible candidate; closest stated cutoff (Sep 2024) and size (8.9B) to OLMo; 5.3 points from OLMo's accuracy on the screening items | — |
| 2026-10-02 | **Third-family selection rule, fixed before screening:** candidates with a *stated* training cutoff near OLMo's (Dec 2024) and comparable size — Nemotron-Nano-9B-v2 (NVIDIA, 8.9B, Sep 2024) and Phi-4-mini (Microsoft, 3.8B, Jun 2024) — run on the same 60-item `cep_v2` slice (K = 3, twice). Eligible if ≥ 95% readable and final answers stable; choose the eligible one closest to OLMo's accuracy on those items; tie (< 2 points) → closer cutoff. *Note: this row was meant to be added before screening, but the edit did not apply on this branch (wrong text anchor). The rule was nevertheless fixed before any result, in commit `d83a899`'s message and in `experiments/screen_*.json`.* | Shibaditya asked for comparable cutoff, size and task ability; public benchmark tables use incompatible setups, so ability is measured on our own items (the guide's "matched capability") | SmolLM3, Ministral-3, Granite-4, Falcon-H1, InternLM3 (no stated cutoff) |
| 2026-10-02 | Syllogisms: "unanswerable" stays a wrong, distinct answer (original scoring kept) | Valid answers are Yes/No; "unanswerable" is a different response from "No", so merging them would change what counts as agreement; keeps the pre-registered scoring with no post-hoc change | Score it as "No" (PR #3, closed); count it correct but distinct |
| 2026-10-02 | Release `cep_v2` on Hugging Face as `copy-or-coincidence`, CC-BY-4.0, public, with a canary string on every row; **upload deferred to the end of the project** (Shibaditya) | Citable, reproducible; canary lets model trainers exclude it. Deferring lets late tweaks go into the released version | Upload now; gated access; CC-BY-NC |
| 2026-10-02 | **OLMo-3-7B is the main model; Gemma-4-E4B the second family** (agreed with Shibaditya) | OLMo runs reliably on T4, has public training data (strongest no-contamination evidence), and makes lure errors (9/60 in E0) — shared wrong answers are what we study | Gemma main (blocked on T4 attention kernel); Qwen3.5 (no stated cutoff, 98% accurate → few errors) |
| 2026-10-02 | **Grow `cep_v2` to 600 items, 20 trick templates** | Guide's power table: 300 items × 5 runs detects a 10-point residual reliably but a 5-point one only ~80%; 400+ items for 90%. More templates guard against "the result is about 10 riddles" and support a template random effect | Keep 300 (underpowered for small effects) |
| 2026-10-02 | ~~Switch main model to Gemma-4-E4B; OLMo-3-7B as second family~~ (superseded same day) | Both state a training cutoff (Jan 2025 / Dec 2024); OLMo publishes its training data; Qwen3.5 states no cutoff | Keep Qwen3.5; Phi-4-mini (cutoff Jun 2024, weaker) |
| 2026-10-02 | **Generated-only item set `cep_v2`** | A freshly generated item cannot be in any training set, for any model, past or future; stronger than "dataset newer than cutoff" | Datasets released after the cutoff (LiveBench stopped updating Apr 2025; MathArena AIME/HMMT 2026: 30 items, too hard, non-commercial) |
| 2026-10-02 | Own math generator instead of Reasoning Gym `gsm_symbolic` | In 4 sampled RG items: 1 had a wrong answer key (mixed €/cents, 574 pretzels), 1 contained an unused number; a missing-premise transform on such items could leave them answerable | Use RG math and audit by hand |
| 2026-10-02 | Missing-premise math items have **no lure** | The hidden number is random, so no single wrong answer tempts; the error that matters is answering at all (`unanswerable_answered`) | Lure = answer with the hidden number (meaningless here) |
| 2026-10-02 | Drop "Yes" syllogisms with a "Some…" conclusion | Valid only under Aristotelian existential import; modern logic says "No", so the key would be convention-dependent | Keep and accept ambiguous keys |
| 2026-10-01 | Structured JSON decoding on for all agents (`structured_output: true`) | E0: 100% valid JSON vs 98%, same accuracy; removes a failure mode that could differ across question types | Free decoding + backup reader |
| 2026-10-01 | Prefix caching off in vLLM | Suspected source of rerun drift; costs little because each prompt is short | Leave on, accept drift |
| 2026-10-01 | vLLM on T4 runs Qwen3.5 in float16 (T4 has no bfloat16) | Hardware limit; vLLM casts automatically. Mac-vs-Kaggle accuracy in E0 checks it does no harm | Could not use bf16 |
| 2026-10-01 | Test constrained JSON decoding before adopting it | It removes format failures but may change what the model writes; compare accuracy and lure rates with/without on the same items first | Adopt blindly; change prompt instead |
| 2026-10-01 | Thinking mode off | 5–10× more tokens otherwise; our JSON format already asks for written steps; matches the guide's ~400-token budget | Thinking on (could study later as its own factor) |
| 2026-10-01 | Mac = 4-bit dev copy only; all reported numbers from Kaggle fp16 | Guide: never mix quantisations for one agent within an experiment | Running everything on the Mac (too slow: ~5 s per answer) |
| 2026-10-01 | Mixed item set: datasets where they give answers + lures, generated items where famous versions are memorised | Saves ~⅔ of the building work; keeps uncontaminated trick questions with exact lures | All generated (guide default); all datasets (memorised trick questions, no lures) |
| 2026-10-01 | Missing-premise lure = the original problem's answer | A model that invents the deleted fact reproduces it exactly | No lure for these items |
| 2026-10-01 | Stairs/clock items only with whole-number lures | A lure like 60.75 is almost never produced exactly, so it would under-count lure hits | Keep fractional lures |
| 2026-10-01 | Several different numbers in an answer → unreadable, not "pick the last one" | A guessed merge could manufacture "same answer" agreement | Take the last number |
| 2026-10-01 | GitHub repo public | Chosen by Shibaditya; secret scan before every push | Private until paper |

## 4b. Publication validity plan

What a conference reviewer will test, and how this project answers it. Each row must be ✅ before writing.

| Threat / reviewer question | Our answer | Status |
|---|---|---|
| Wrong baseline (difficulty confound) | Item-conditioned null; **Experiment 1 must give residual ≈ 0** for non-interacting agents | ✅ PASS (all 15 applicable tests) |
| Training-data contamination | All 600 items generated fresh (`cep_v2`); main model's training data (Dolma 3) is public → search it for item text | ✅ items / ⏳ search |
| Answer keys wrong or ambiguous | Independent second solver re-derives all 600 keys (`analysis/verify_keys.py`, run in the test suite) + LLM wording review + human spot-check with a pre-stated exclusion rule | ✅ solver + review + human 30/30 |
| Grading wrong | Code-only grading; validate on 150 human-labelled answers (≥95% correct/incorrect, ≥85% error class); checker frozen and hashed | ⏳ |
| Underpowered | 600 items; simulate power from real Layer-0 distributions before fixing R for Exp 7 | ⏳ |
| Result specific to one model | Replicate on a second family (Gemma-4-E4B) and report sign + magnitude | ⏳ |
| Result specific to one task style | 20 trick templates, 25 false-world cases, syllogisms, 10 math templates; template as random effect | ✅ |
| Analysis chosen after seeing data | Pre-register ≤ 5 primary hypotheses per experiment as a git-timestamped file before running it; Holm correction; everything else labelled exploratory | ✅ Exp 1 and Exp 7 pre-registered |
| Statistics overstate precision | Item is the unit: item-bootstrap CIs, within-item permutation tests, mixed models with item + template random effects | ⏳ |
| Interaction effect is just a longer prompt / formatting copy | Random-answer control (Condition C) ✅; redacted control (E) ⏳ | 🔄 |
| Reproducibility | Public repo, pinned model/dataset/package versions, byte-identical item rebuilds, append-only logs with seeds, released raw outputs | ✅ |
| Non-determinism | Final answers identical on rerun (E0); residual text drift documented; prefix caching off | ✅ |
| Same model as both agents | Stated as an MVP limitation; cross-family pair in replication | ⏳ |

## 5. Findings

### 2026-10-02: Third-family screening, round 1 (60 `cep_v2` items × 3, run twice)
- **Phi-4-mini: ineligible.** Accuracy 58.3% (rerun 57.8%) vs OLMo 93.0% on the same items (gap 34.7 points);
  readable answers 88.3% (< 95% rule); 5.6% truncated. By family: logic 100%, trick 60%, math 44% (OLMo 100 / 90 / 100).
- **Nemotron-Nano-9B-v2: eligible and selected.** After fixing a runner bug on this branch (engine-argument
  pass-through missing, so `trust_remote_code` was rejected), rerun: accuracy 87.8% (rerun 87.2%) vs OLMo
  93.0% (gap 5.3 points); readable 100%; final answers stable 99.4%; truncated 3.3%; median 106 tokens; no
  thinking text in any reply (`/no_think` works). By family: logic 100%, trick 88%, math 83%.
- **Decision by the pre-stated rule: Nemotron-Nano-9B-v2 is the third family.**

### 2026-10-02: Experiment 7, sequential exposure — **H1–H5 all supported** (pre-registered in `prereg/exp7_sequential_exposure.md`)
OLMo-3-7B, 600 `cep_v2` items × R = 5 per condition (12,000 receiver answers, 2.1 GPU-h). Receiver sees a
sender's Layer 0 sample 10–14 (or a uniformly random candidate answer); nulls from Layer 0 samples 0–9.
Residual = observed − item-conditioned expectation; 95% item-bootstrap CI; one-sided within-item permutation
p (2,000 shuffles, so p = 0.0005 is the floor); Holm across the five.

| Hypothesis | Residual | 95% CI | p (Holm) | Verdict |
|---|---|---|---|---|
| H1 `seq_steps` same answer | **+0.0874** | [+0.0739, +0.1016] | 0.0025 | supported |
| H2 steps − answer-only, same answer | **+0.0200** | [+0.0130, +0.0277] | 0.0025 | supported |
| H3 `random_answer` same answer | **+0.1784** | [+0.1584, +0.1989] | 0.0025 | supported |
| H4 `seq_steps` joint error | **+0.0398** | [+0.0308, +0.0493] | 0.0025 | supported |
| H5 `seq_steps` both on lure (lure items) | **+0.0202** | [+0.0102, +0.0314] | 0.0025 | supported |

**Decomposition (the project's headline quantity).** With steps shown, observed joint error 0.121 = 0.081
predicted by the agents' own per-item behaviour + **0.040 created by interaction (33%)**. Answer only: 0.110 =
0.081 + 0.028 (26%). Random answer: 0.217 = 0.076 + 0.141 (65%).

Condition summaries:

| Condition | Receiver accuracy | Gives shown answer | Same-answer residual | Joint-error residual | Lure residual |
|---|---|---|---|---|---|
| Layer 0 (alone) | 0.873 | — | — | — | — |
| `seq_steps` (B sees A, steps) | 0.874 | 0.984 | +0.087 | +0.040 | +0.020 |
| `seq_answer` (B sees A, answer) | 0.879 | 0.964 | +0.067 | +0.029 | +0.012 |
| `random_answer` (C) | **0.767** | 0.764 | +0.178 | +0.141 | +0.129 |
| `seq_steps_rev` (A sees B, steps) | 0.874 | 0.981 | +0.084 | +0.040 | +0.014 |

Exploratory (not pre-registered):
- **Adoption of wrong answers** vs the receiver's own rate for that same answer (Layer 0 samples 0–9):
  steps 96.2% vs 55.6%; answer only 84.9% vs 55.6%; **random 47.5% vs 11.3% (≈4×)**; reversed 93.3% vs 55.1%.
- Accuracy is unchanged under real-peer exposure (0.874 vs 0.873): the receiver converges on the sender, who is
  as accurate as itself, so agreement rises without correction (consistent with the martingale account of
  debate, Choi et al. 2025). A content-free peer answer lowers accuracy by 10.6 points.
- Order: `seq_steps_rev` reproduces `seq_steps` (same-answer +0.084 vs +0.087), as expected for two agents with
  identical weights; not a test of cascades.
- By family (same-answer residual, steps): trick +0.108, logic +0.086, math +0.068.

**Limitations to carry into the paper:** one model playing both roles (replicate on Gemma-4-E4B); one message
framing ("Another agent solved this problem independently."); no redacted-reasoning (E) or flipped-conclusion
(F) controls yet, so "follows the conclusion vs the argument" is not yet separated.

### 2026-10-02: Experiment 1, independent duplicates — **PASS** (pre-registered in `prereg/exp1_independent_duplicates.md`)
OLMo-3-7B agents A and B (same weights, different seeds, no interaction), 600 `cep_v2` items; samples
0–9 estimate each agent's per-item distribution, samples 10–19 form 10 observed A/B pairs per item.

| Scope | Joint error residual [95% CI] | Same answer | Same wrong answer | Both on lure | Naive global "excess" |
|---|---|---|---|---|---|
| Overall (600) | +0.0003 [−0.0041, +0.0045] | −0.0051 [−0.0131, +0.0029] | −0.0019 [−0.0061, +0.0022] | −0.0018 [−0.0062, +0.0028] | **+0.0651** |
| Trick questions | −0.0008 [−0.0086, +0.0071] | −0.0010 [−0.0153, +0.0131] | −0.0037 [−0.0108, +0.0036] | −0.0027 [−0.0092, +0.0041] | +0.0478 |
| Logic | +0.0025 [−0.0046, +0.0093] | −0.0092 [−0.0236, +0.0056] | +0.0003 [−0.0086, +0.0094] | 0.0000 | +0.0962 |
| Math | −0.0007 [−0.0067, +0.0055] | −0.0052 [−0.0194, +0.0074] | −0.0025 [−0.0087, +0.0035] | n/a (no lures) | +0.0480 |

- Every applicable residual has a CI containing 0 and |residual| < 0.005 → **pre-registered pass rule met**.
- The naive global baseline reports +4.8 to +9.6 points of spurious "excess joint error" for agents that
  never interacted: the difficulty confound, measured on real LLM data.
- One permutation p below 0.05 (logic joint error, p = 0.028) among 15 tests; ~0.75 expected by chance,
  and its CI contains 0. The pass rule was defined on CI and magnitude, not p.
- **Analysis-script bug, fixed (not a change to the rule):** `exp1.py` first reported FAIL because
  "both on lure" within math has zero items (cep_v2 math has no lures) and produced NaN. The
  pre-registration defines that metric on lure items only; it is now reported as n/a.

### 2026-10-02: Layer 0 descriptives (OLMo-3-7B, 24,000 answers)
- Valid JSON 99.5%, unreadable 0.6%, truncated 0.5%, median 116 output tokens. Agents A and B both 87.3%.
- Accuracy: false-world 99.3%; math complete 99.4%; trick questions 88.4% (lure 7.7% of answers);
  missing-premise 81.8% (answered with a number 17%); syllogisms 66.5% (see below).
- 53% of items always right, 1.7% always wrong, **45% mixed**: enough within-item variability for the null.
- **Syllogism "unanswerable" replies (decided: scored as wrong):** on invalid syllogisms (key No) the model
  answered "unanswerable" 1,042/2,000 times, often after reasoning "the conclusion does not follow"; it did so
  88/2,000 times on valid ones. Likely trigger: the solver prompt's rule "if the question cannot be answered …
  give unanswerable" next to "Does it logically follow?". Read as "does not follow", syllogism accuracy would
  be 92.6% instead of 66.5%.
  **Decision (Shibaditya, 2026-10-02): "unanswerable" is a distinct answer. The valid answers are Yes/No, so it
  is scored wrong and is never the same answer as "No".** This is the original, pre-registered scoring
  (checker `f7805da13b9b`); nothing is re-graded. Two agents both answering "unanswerable" count as the same
  wrong answer, which they are. A re-grade treating it as "No" was prepared and rejected (PR #3, closed);
  Experiment 1 passed under that alternative too. Report syllogism accuracy with this caveat.

### 2026-10-02: Null-model code validated on simulated data (`coc/tests/test_nulls.py`)
400 simulated items with strong difficulty heterogeneity (difficulty ~ Beta(0.6, 0.6)), 4 answer options
incl. a lure; distributions estimated on 10 held-out samples per agent, 10 paired runs per item; B copies
A's answer with known probability c.

| True copy rate c | Naive global "excess" (both wrong) | Item-conditioned residual, same answer [95% CI] | Permutation p | True residual c·(1 − E[same]) |
|---|---|---|---|---|
| 0% | **+0.116** (spurious) | **−0.003** [−0.020, +0.015] | 0.256 | 0.000 |
| 5% | +0.123 | +0.021 [+0.004, +0.038] | 0.003 | +0.023 |
| 10% | +0.129 | +0.043 [+0.026, +0.061] | 0.003 | +0.046 |
| 20% | +0.142 | +0.088 [+0.070, +0.106] | 0.003 | +0.091 |

- The naive baseline reports a large "excess" with **no** dependence, and barely moves as real copying
  goes from 0% to 20%: it measures difficulty, not interaction.
- The item-conditioned residual is ≈ 0 without copying and recovers the true effect within ~0.003.
- Passes the guide's month-2 gate ("nulls.py recovers known c").

### 2026-10-02: Item audit of `cep_v2` (before any model sees it)
**How (report this in the paper's Methods):**
1. *Independent solver, all 600 items* (`analysis/verify_keys.py`), written separately from the generators:
   syllogisms by enumerating all 256 set-models over three terms, under both modern and Aristotelian
   (existential-import) semantics, so a convention-dependent key is caught; false-world items by forward
   chaining over the stated rules; trick questions by simulation from stored parameters (count
   handshakes, step the snail, etc.); math by separately written formulas.
2. *LLM wording review* (Claude) of the 30-item audit sample, for ambiguity the solver cannot see.
3. *Human audit* by Shibaditya Deb, 2026-10-02: **30/30 sampled items agree with the key, 0 flagged as unclear** (`datasets/cep_v2/human_audit.csv`, 10 per family, answered independently). **Pre-stated exclusion rule:** any item a human finds
   wrong or ambiguous after Layer 0 is excluded from all analyses (not re-run), and the exclusion is reported.

**Found and fixed:**
- Solver: 1 of 600 disagreed. `savings` floored a non-whole weekly saving ($250 × 25% = $62.50 → $62).
  Here it only touched a missing-premise item (key still correct), but a complete item with those
  numbers would have had a wrong key. Generator now rejects non-whole savings; solver added to tests.
- Review: negated false-world rules read "Every animal is not finned", which can also mean "not every
  animal is finned" (scope ambiguity) → now "No animal is finned." (50 items).
- Review: the distractor fact sometimes named the queried property ("Every dolphin is air-breathing" in a
  question about air-breathing), cueing the lure in some items only → distractor now always about a
  different property.
- Result: **600/600 keys confirmed** after fixes. 28/30 sampled items had no wording issue.

### 2026-10-02: Experiment 0 for OLMo-3-7B-Instruct (20 `cep_v1` items × 3, vLLM fp16, 2× T4)
- Accuracy 82%; **9 of 60 answers hit the lure** (siblings 5/6, overtaking 4/6), vs 1/60 for Qwen3.5-4B.
  For this project that is useful: shared *wrong* answers are what we measure, and a 98%-accurate model
  leaves almost none.
- 100% valid JSON (structured decoding), no truncation, median 133 output tokens, ~0.9 s per answer.
- Rerun: final answers 60/60 identical, text 58/60 identical (prefix caching off; better than Qwen's 50/60).
- Gemma-4-E4B retry did not actually test FlexAttention: vLLM 0.30 ignored the `VLLM_ATTENTION_BACKEND`
  environment variable and used Triton again, failing the same way.

### 2026-10-01: Experiment 0 on Kaggle (20 items × 3, vLLM 0.30.0, fp16, 1× T4)
| | Free decoding | Structured JSON decoding |
|---|---|---|
| Accuracy | 98% (59/60) | 98% (59/60) |
| Valid JSON | 98% (1 needed the backup reader) | **100%** |
| Truncated | 0 | 0 |
| Output tokens, median / max | 178 / 537 | 159 / 828 |
| Rerun: identical text | 57/60 | 50/60 |
| Rerun: identical **final answer** | **60/60** | **60/60** |
| Errors | 1 lure (overtaking) | 1 invented number on a missing-premise item |

- **Full precision on Kaggle behaves far better than the 4-bit Mac copy:** 98% vs 87% accuracy and
  98–100% vs 80% valid JSON, no looping. The Mac copy's format problems were mostly a 4-bit artefact.
  Confirms the rule that Mac numbers are development-only.
- **Structured decoding** removes format failures entirely without changing accuracy on this slice →
  adopted for all agents.
- **Rerun drift:** with identical seeds, 3–10 of 60 explanations diverge partway through (first
  differing character between 1 and 625) but **no final answer changed**. Classic GPU floating-point
  non-determinism; most likely amplified by prefix caching (the second run reused the first run's
  cached prompt computations). Prefix caching is now off; determinism is re-checked at the start of
  the next Kaggle job. If drift remains, it is equivalent to extra sampling noise *within* one agent and
  cannot couple two agents, so it does not bias the null model; it only weakens exact reproducibility.
- Speed: ~1.1 s per answer amortised at batch 60, after ~12 min of vLLM start-up.

### 2026-10-01: Experiment 0 on the Mac, round 1 (20 items × 3, 4-bit; development only)
- 87% correct overall; most of this slice is easy for the model.
- **Format is the main problem:** only 80% of replies were valid JSON. 5 of 60 had no readable
  answer at all (3 looped until the 1,024-token limit, 2 put the answer outside the `final` field).
  **5 of the 8 "wrong" answers were formatting failures, not reasoning errors.**
- Real errors seen: lure hits on the siblings question (2), one missing-premise item answered with a
  made-up number; missing-premise items are the hardest (1 of 3 correct).
- The model often writes a full prose solution *and then* the JSON, roughly doubling output length.
- Speed: median 148 output tokens, ~5 s per answer on the Mac.
- **Rerun determinism: 60/60 answers byte-identical** across two runs with the same seeds. Per-trial
  seeding works on the Mac.
- Kaggle comparison: first attempt crashed during vLLM start-up (see Problems); rerun pending.

## 6. Problems hit and fixes

| Date | Problem | Fix |
|---|---|---|
| 2026-10-03 | Kaggle changed its default image overnight (`…37c64f7d` → `…2757e0c7`: Python 3.12 → 3.13, CUDA 12.8 → 13). The unpinned `pip install vllm` then crashed both Experiment 7 replication jobs (PyTorch/TorchAudio CUDA mismatch) before any answer was generated; ~1 GPU-minute lost, no data affected | `kaggle/env.json` pins the 2026-10-02 image and `vllm==0.30.0`; jobs drop the unused torchaudio, print Python/torch/vLLM versions, and **stop** if Python or vLLM differ, so no data can come from a different stack than Layer 0. Replication Exp 7 jobs relaunched |
| 2026-10-02 | Gemma retry used the wrong switch: vLLM 0.30 ignores the `VLLM_ATTENTION_BACKEND` env var | Must pass the backend through the engine arguments instead; untested so far |
| 2026-10-02 | Gemma-4-E4B would not start on T4 (`exp0_gemma` v1): vLLM's Triton attention kernel needs 96 KB of on-chip shared memory for Gemma-4's large attention heads; the T4 has 64 KB. Not a float16 problem | Retrying with vLLM's FlexAttention backend; OLMo-3-7B tested in the same Kaggle job as the fallback. Jobs can now run several experiments, each in its own process |
| 2026-10-02 | Reasoning Gym math generator: wrong answer keys and unused numbers | Wrote `math_word.py`: 10 templates, every quantity used, exact integer answers; a test perturbs each hidden quantity and checks the answer changes |
| 2026-10-02 | Reasoning Gym syllogisms: 71% "Yes" and some keys depend on existential import | Balanced 25/25; dropped "Yes" + "Some…" conclusions; test enforces it |
| 2026-10-01 | A crash mid-write would glue the next row onto a half-written line, losing it | `repair_tail()` trims a torn last line before resuming; covered by a test |
| 2026-10-01 | Model download stalled at 2.4/3 GB | Restarted; download resumes |
| 2026-10-01 | `kaggle/push.py` wrongly said the commit wasn't on GitHub | Fixed the check |
| 2026-10-01 | 20% of replies not valid JSON (see Findings) | Added optional JSON-schema-constrained decoding (vLLM structured outputs, `structured_output: true` in the agent config); being compared against free decoding in E0 on Kaggle |
| 2026-10-01 | Kaggle E0 crashed: vLLM 0.30.0 refused to start Qwen3.5 with 256 concurrent sequences (its hybrid attention layers allow only 153 on a 15 GB T4) | `max_num_seqs = 128` in the agent configs |
| 2026-10-01 | vLLM takes ~12 min to start on a T4 (torch.compile ~40 s, CUDA-graph capture and profiling the rest), billed to GPU quota | Do several runs/agents inside one Kaggle job (`--run-id run1,run2`) |

## 7. Experiment notebook

Entries follow the guide's template (§15): fields above the line are written **before** running.

### E0: Experiment 0, pipeline sanity
- **Question:** is the pipeline stable enough to trust? (not a research question)
- **Setup:** 20 items (round-robin over all 14 templates), K = 3, agent `qwen35-4b-A`, run twice with
  identical seeds; Mac (mlx, 4-bit) and Kaggle (vLLM, fp16)
- **Pass criteria:** parse rate high and similar across question types; rerun byte-identical; nothing
  truncated systematically
- --- after ---
- **Observed (Mac):** parse rate 80% JSON / 92% any answer; 5% truncated; rerun 60/60 identical.
  **Fails** the parse-rate criterion → format fix.
- **Observed (Kaggle):** see Findings table. Parse 100% with structured decoding; no truncation;
  final answers 60/60 identical on rerun, text 50–57/60 identical.
- **Verdict:** pass, except exact text reproducibility; re-checked with prefix caching off.
- **Alternatives considered:** (1) drift from prefix caching; (2) from GPU kernel non-determinism in
  Qwen3.5's linear-attention (Triton fallback path on T4). Test (1) next job; (2) would remain.
- **What changed in my understanding:** output format failures are frequent enough to bias "same
  wrong answer" counts, so they must be fixed before Layer 0.

## 8. Next steps

*(2026-10-02, after Experiment 7)*
1. **Shibaditya:** label the 150 replies in `validation/checker_label_sheet.md` (checker validation).
2. Replicate Experiment 7 on a second model family (Gemma-4-E4B; first get it running on T4 via vLLM
   engine-argument FlexAttention, or a transformers backend).
3. Mechanism controls (guide §8): E redacted reasoning, F flipped conclusion, G displayed confidence.
4. Robustness: a second message framing; original vs alternative syllogism scoring.
5. Search OLMo's public training data (Dolma 3) for item text; HF release at the very end.

*(earlier)*
1. **Shibaditya:** hand-audit the 30 items in `datasets/cep_v2/audit_sample.md` (items must be final
   before Layer 0, because changing them later invalidates it).
2. Layer 0 on Kaggle with OLMo-3-7B: agents A and B, 600 `cep_v2` items × K = 20 each (24,000 answers,
   ~4–5 GPU hours).
3. Checker validation: hand-label 150 answers from Layer 0 (target ≥ 95% on right/wrong, ≥ 85% on
   error class).
4. Null-model code (`nulls.py`) + Experiment 1.

## 9. Gap analysis against the field guide (2026-10-02)

Re-read of `Excess_Error_Correlation_Field_Guide_1.pdf` after Experiment 7, to find what the project still lacks.
The checklist version of this lives in `docs/PROJECT_PLAN.md` §5 (D–G).

**Covered well:** item-conditioned nulls N2/N3 (validated, Experiment 1 PASS); disjoint samples for expected vs
observed; within-item permutation; item bootstrap; Holm; pre-registration (≤ 5 hypotheses); Experiment 7 with
steps vs answer-only and the random-answer control (C); programmatic, frozen, hashed checker with no LLM labels
in residuals; checker validation (blind reader; human adjudication pending); fresh, verified items;
replication on other families (in progress); reproducibility (pinned versions, CI, append-only logs).

**🔴 Critical gaps** (central in the guide; reviewers will ask)
| # | Gap | Guide | Why it matters | GPU |
|---|---|---|---|---|
| 1 | N4 mode-finding null on contested items (joint-mode mass < 0.7) | §5, §6, §15 | Formal test of "tipping": residual explained by N4 = interaction reveals a shared prior; residual N4 cannot explain = cascades, sycophancy, persuasion | no |
| 2 | Helpful vs harmful flips (h, g) and content-blind flip | §4, §11, §15 | Copying vs evaluating; needs an answer-first-then-revise protocol | yes |
| 3 | Three-way error decomposition: shared / interaction-created (g in B minus C) / interaction-amplified (lure beyond N4) | §8 | Our split is two-way only | partly |
| 4 | Mixed-effects logistic model (condition × family × error type; item + template random effects); paired McNemar | §10, §12 | Required factor-effect statistics | no |
| 5 | Kim et al. / Goel et al. (CAPA) metrics computed on our data | §1.3, §15 | Named open question: how much population-level correlation survives item-conditioning | no |

**🟠 Important gaps**
| # | Gap | Guide | GPU |
|---|---|---|---|
| 6 | Q1 similarity across families at matched accuracy (JSD, error identity vs item baseline) | §1.2, Exp 4 | no (after all Layer 0 runs) |
| 7 | Mechanism controls E (answer redacted), F (conclusion flipped, N10), G (displayed confidence), D (other-model answer) | §8 | yes |
| 8 | Alternative explanations for Δ: formatting convergence; message restating the item | §6, §11 | partly |
| 9 | Empirical power analysis from Layer 0 distributions | §10 | no |
| 10 | Error identity P(same wrong \| both wrong) vs its item baseline; conditional mutual information | §4 | no |
| 11 | Theory: relate the residual to Tumer–Ghosh ρ and Condorcet; implications for majority voting | §2, §12 L7 | no |
| 12 | One intervention that moves the residual (answer-first, forced dissent "ally", missing-info warning) | §12 L5, §15 | yes |

**🟡 Secondary / postponed:** 4th item family (constraint/planning); step-level signatures (N6, J_sig);
debate rounds, chains of 3–4 agents (cascades), verifier lineage × error type (Exp 9); size ladder, prompt
diversity, shared evidence (Exp 2, 5, 6); Layer 0 session-stability check (< 2 points); the three reasons an
error survives (undetectable / talked out of it / detected but not repaired, §1.1).

**Link to the "why" plan.** The guide's own definition of a contribution (§15) asks for a residual decomposed
"by direction and flip asymmetry", evidence on how much interaction failure is predictable from independent
distributions (N4), a mechanism with a pre-registered prediction surviving a randomised control, and an
intervention that moves the residual. These map onto the four "why" depths in `docs/PROJECT_PLAN.md` §1;
the OLMo-3 training-stage comparison answers the guide's open question on whether post-training changes which
errors are shared.

**Order agreed:** no-GPU items first (1, 3, 4, 5, 6, 9, 10, 11), then pre-registered new runs (2, 7, 12, and
the training-stage comparison).
