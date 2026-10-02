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
| 2b | Switch to contamination-proof setup: Gemma-4-E4B + generated-only item set `cep_v2` | 🔄 items built ✅; Gemma failed on T4 (shared memory), retry + OLMo fallback running |
| 2a | Hand-audit 30 items (`datasets/cep_v2/audit_sample.md`) | ⏳ waiting on Shibaditya |
| 3 | Layer 0: each agent answers all 300 items × 20 alone (Kaggle) | ⏳ |
| 4 | Checker validation vs 150 hand-labelled answers (target ≥95% / ≥85%) | ⏳ |
| 5 | Null-model code + Experiment 1 (independent agents must give residual ≈ 0) | ⏳ |
| 6 | Experiment 7: A→B, B→A, random-answer control | ⏳ |
| 7 | Analysis + write-up | ⏳ |

## 3. What we are using

### Models
| Role | Model | Exact version | Where | Notes |
|---|---|---|---|---|
| **Agents A and B (MVP)** | `google/gemma-4-E4B-it` (8B total, ~4B effective) | rev `ee0ef602`; **training cutoff Jan 2025** (model card) | Kaggle, vLLM, fp16, both T4s (tensor parallel 2) | Pending float16 feasibility test |
| **Second family (later)** | `allenai/Olmo-3-7B-Instruct` | **training cutoff Dec 2024**; training data public (Dolma 3) | Kaggle, both T4s | Lets us *prove* items were not in training data |
| Superseded | `Qwen/Qwen3.5-4B` | rev `851bf6e8`; training cutoff **not stated** | Kaggle | Used for Exp 0 only; dropped because its training data can't be dated |
| Mac development copy | `mlx-community/Qwen3.5-4B-4bit` | rev `0e7ffd5c` | Mac, mlx-lm, 4-bit | Dev only, never reported |

Agent settings (`configs/agents/qwen35_4b_*.json`): temperature 0.7, top-p 0.95, max 1024 output
tokens, thinking mode **off**, prompt `prompts/solver_v1.txt`, one fixed seed per answer derived from
(agent, item, protocol, sample number).

### Item set `cep_v2` (current): every item generated fresh, seed 1
| Group | Generator | n | Lure | Error cause |
|---|---|---|---|---|
| Trick questions | `cep/generators/crt.py` (10 templates) | 100 | intuitive answer | `intuitive_lure` |
| False-world logic | `cep/generators/false_ontology.py` | 50 | common-sense answer | `prior_override` |
| Syllogisms (Yes/No), 25 valid + 25 invalid | Reasoning Gym 0.1.25 `syllogism` (Apache-2.0, first released Feb 2025), filtered | 50 | none | `deduction_slip` |
| Math, complete | `cep/generators/math_word.py` (10 templates) | 50 | none | `multi_step` |
| Math, one quantity made vague | same | 50 | none | `missing_premise` |

300 items, 150 with a lure; hash in `datasets/cep_v2/manifest.json`. No item exists in any public dataset,
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
| 2026-10-02 | **Switch main model to Gemma-4-E4B; OLMo-3-7B as second family** | Both state a training cutoff (Jan 2025 / Dec 2024); OLMo publishes its training data; Qwen3.5 states no cutoff | Keep Qwen3.5; Phi-4-mini (cutoff Jun 2024, weaker) |
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

## 5. Findings

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
1. Gemma-4-E4B float16 feasibility (`exp0_gemma`, running). If it fails → OLMo-3-7B as the main model.
2. **Shibaditya:** hand-audit the 30 items in `datasets/cep_v2/audit_sample.md` (items must be final
   before Layer 0, because changing them later invalidates it).
3. Layer 0 on Kaggle: agents A and B, 300 `cep_v2` items × K = 20 each (12,000 answers); starts with a
   20-item determinism re-check (prefix caching off).
3. Checker validation: hand-label 150 answers from Layer 0 (target ≥ 95% on right/wrong, ≥ 85% on
   error class).
4. Null-model code (`nulls.py`) + Experiment 1.
