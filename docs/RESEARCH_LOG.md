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
| 6 | Experiment 7: A→B, B→A, random-answer control | ⏳ |
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
| Analysis chosen after seeing data | Pre-register ≤ 5 primary hypotheses per experiment as a git-timestamped file before running it; Holm correction; everything else labelled exploratory | ⏳ |
| Statistics overstate precision | Item is the unit: item-bootstrap CIs, within-item permutation tests, mixed models with item + template random effects | ⏳ |
| Interaction effect is just a longer prompt / formatting copy | Random-answer control (Condition C), redacted control (E) | ⏳ |
| Reproducibility | Public repo, pinned model/dataset/package versions, byte-identical item rebuilds, append-only logs with seeds, released raw outputs | ✅ |
| Non-determinism | Final answers identical on rerun (E0); residual text drift documented; prefix caching off | ✅ |
| Same model as both agents | Stated as an MVP limitation; cross-family pair in replication | ⏳ |

## 5. Findings

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
- **Syllogism scoring issue (open, decision pending):** on invalid syllogisms (key No) the model answered
  "unanswerable" 1,042/2,000 times, usually after correctly reasoning "the conclusion does not follow".
  The solver prompt's rule ("if the question cannot be answered … give unanswerable") collides with
  "Does it logically follow?". Read as "does not follow", syllogism accuracy is 92.6% instead of 66.5%.
  Unaffected: Experiment 1. Affected if left as is: "same wrong answer" in later experiments would count
  two "unanswerable" replies on an invalid syllogism as a shared error.

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
1. **Shibaditya:** hand-audit the 30 items in `datasets/cep_v2/audit_sample.md` (items must be final
   before Layer 0, because changing them later invalidates it).
2. Layer 0 on Kaggle with OLMo-3-7B: agents A and B, 600 `cep_v2` items × K = 20 each (24,000 answers,
   ~4–5 GPU hours).
3. Checker validation: hand-label 150 answers from Layer 0 (target ≥ 95% on right/wrong, ≥ 85% on
   error class).
4. Null-model code (`nulls.py`) + Experiment 1.
