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
| 2 | Model runner (Mac + Kaggle), Experiment 0 sanity | 🔄 in progress |
| 2a | Hand-audit 30 items (`datasets/cep_v1/audit_sample.md`) | ⏳ waiting on Shibaditya |
| 3 | Layer 0: each agent answers all 300 items × 20 alone (Kaggle) | ⏳ |
| 4 | Checker validation vs 150 hand-labelled answers (target ≥95% / ≥85%) | ⏳ |
| 5 | Null-model code + Experiment 1 (independent agents must give residual ≈ 0) | ⏳ |
| 6 | Experiment 7: A→B, B→A, random-answer control | ⏳ |
| 7 | Analysis + write-up | ⏳ |

## 3. What we are using

### Models
| Role | Model | Exact version | Where | Notes |
|---|---|---|---|---|
| Agents A and B (MVP) | `Qwen/Qwen3.5-4B` | rev `851bf6e8` | Kaggle, vLLM, fp16 | Every reported number comes from here |
| Mac development copy | `mlx-community/Qwen3.5-4B-4bit` | rev `0e7ffd5c` | Mac, mlx-lm, 4-bit | Dev only, never reported (different precision) |
| Later: different family | Gemma-4-E4B (planned) | — | Kaggle | For same- vs different-family comparison |

Agent settings (`configs/agents/qwen35_4b_*.json`): temperature 0.7, top-p 0.95, max 1024 output
tokens, thinking mode **off**, prompt `prompts/solver_v1.txt`, one fixed seed per answer derived from
(agent, item, protocol, sample number).

### Datasets
| Dataset | Hugging Face id + revision | Licence | What we took |
|---|---|---|---|
| GSM-Plus | `qintongli/GSM-Plus` @ `3b708db5` | CC-BY-SA-4.0 | 50 missing-premise + 50 distractor math items |
| ProntoQA | `renma/ProntoQA` @ `6f3e0386` | MIT | 50 fictional-word logic items |
| (generated) | `cep/generators/crt.py` | ours | 100 trick questions, 10 templates, fresh numbers |
| (generated) | `cep/generators/false_ontology.py` | ours | 50 false-world logic items |

Item set `cep_v1`: 300 items, 200 with a pre-specified lure, items hash in `datasets/cep_v1/manifest.json`.

### Tools and infrastructure
| What | Version / detail |
|---|---|
| Python (Mac) | 3.11 in `.venv` (uv) |
| Mac | Apple M3, 8 GB RAM; mlx-lm 0.32.0, mlx 0.32.3; ~32 tokens/s |
| Kaggle | 2× Tesla T4 (15 GB each), 30 GPU-h/week; Python 3.12, torch 2.10+cu128; vLLM installed per job |
| Kaggle access | Kaggle CLI 2.2.4, account `debshibaditya`, jobs pushed by `kaggle/push.py` (clones a pinned git commit) |
| Grading | `cep/parse.py` → `cep/normalize.py` → `cep/checker.py`; checker version `f7805da13b9b`; no LLM judge |
| Logs | one JSONL row per answer (`coc/schema.py`, ~50 fields), append-only, resumable |

## 4. Decisions (and why)

| Date | Decision | Why | Alternatives considered |
|---|---|---|---|
| 2026-10-01 | Thinking mode off | 5–10× more tokens otherwise; our JSON format already asks for written steps; matches the guide's ~400-token budget | Thinking on (could study later as its own factor) |
| 2026-10-01 | Mac = 4-bit dev copy only; all reported numbers from Kaggle fp16 | Guide: never mix quantisations for one agent within an experiment | Running everything on the Mac (too slow: ~5 s per answer) |
| 2026-10-01 | Mixed item set: datasets where they give answers + lures, generated items where famous versions are memorised | Saves ~⅔ of the building work; keeps uncontaminated trick questions with exact lures | All generated (guide default); all datasets (memorised trick questions, no lures) |
| 2026-10-01 | Missing-premise lure = the original problem's answer | A model that invents the deleted fact reproduces it exactly | No lure for these items |
| 2026-10-01 | Stairs/clock items only with whole-number lures | A lure like 60.75 is almost never produced exactly, so it would under-count lure hits | Keep fractional lures |
| 2026-10-01 | Several different numbers in an answer → unreadable, not "pick the last one" | A guessed merge could manufacture "same answer" agreement | Take the last number |
| 2026-10-01 | GitHub repo public | Chosen by Shibaditya; secret scan before every push | Private until paper |

## 5. Findings

### 2026-10-01: Experiment 0 on the Mac, round 1 (20 items × 3, 4-bit; development only)
- 87% correct overall; most of this slice is easy for the model.
- **Format is the main problem:** only 80% of replies were valid JSON. 5 of 60 had no readable
  answer at all (3 looped until the 1,024-token limit, 2 put the answer outside the `final` field).
  **5 of the 8 "wrong" answers were formatting failures, not reasoning errors.**
- Real errors seen: lure hits on the siblings question (2), one missing-premise item answered with a
  made-up number; missing-premise items are the hardest (1 of 3 correct).
- The model often writes a full prose solution *and then* the JSON, roughly doubling output length.
- Speed: median 148 output tokens, ~5 s per answer on the Mac.
- Rerun determinism (round 2) and the Kaggle comparison: pending.

## 6. Problems hit and fixes

| Date | Problem | Fix |
|---|---|---|
| 2026-10-01 | A crash mid-write would glue the next row onto a half-written line, losing it | `repair_tail()` trims a torn last line before resuming; covered by a test |
| 2026-10-01 | Model download stalled at 2.4/3 GB | Restarted; download resumes |
| 2026-10-01 | `kaggle/push.py` wrongly said the commit wasn't on GitHub | Fixed the check |
| 2026-10-01 | 20% of replies not valid JSON (see Findings) | 🔄 Planned: force valid JSON with vLLM structured output |

## 7. Experiment notebook

Entries follow the guide's template (§15): fields above the line are written **before** running.

### E0: Experiment 0, pipeline sanity
- **Question:** is the pipeline stable enough to trust? (not a research question)
- **Setup:** 20 items (round-robin over all 14 templates), K = 3, agent `qwen35-4b-A`, run twice with
  identical seeds; Mac (mlx, 4-bit) and Kaggle (vLLM, fp16)
- **Pass criteria:** parse rate high and similar across question types; rerun byte-identical; nothing
  truncated systematically
- --- after ---
- **Observed:** Mac round 1, see Findings. Rerun and Kaggle: pending.
- **What changed in my understanding:** output format failures are frequent enough to bias "same
  wrong answer" counts, so they must be fixed before Layer 0.

## 8. Next steps
1. Finish E0: Mac rerun determinism; Kaggle speed, parse rate, determinism.
2. Fix the output format (structured JSON), rerun E0 on Kaggle.
3. Hand-audit the 30 items.
4. Layer 0 on Kaggle (300 items × 20 samples).
