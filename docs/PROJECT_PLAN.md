# Project plan: copy-or-coincidence

**Read this first, every session.** It is the single map of the project: the goal, the rules, where everything
lives, and one checklist of what is done and what is left. Update it whenever anything changes (mark items,
add new ones, record new paths). Details, numbers and reasoning live in [`RESEARCH_LOG.md`](RESEARCH_LOG.md).

Last updated: 2026-10-03

---

## 1. The motto

> **When AI agents give the same wrong answer, how much is coincidence and how much is copying, and *why*
> do they copy?**

We are writing a **deep, conference-grade paper that explains *why***, not a list of experiment results.
Every experiment exists to answer a "why" question, and every claim needs converging evidence.

**Working title:** *Copy or Coincidence? Why Language-Model Agents Converge on the Same Wrong Answers*

**The thesis so far:** across three model families, most shared errors would happen anyway (hard questions,
shared blind spots), and **20–42% is created by interaction** (OLMo 31%, Qwen 20%, Nemotron 42%). The interaction
part is **transmission, not revealed shared priors**: receivers take the specific answer shown, not the agents'
shared favourite (N4 rejected), and behave as if they put a fixed **deference weight** α on the peer
(≈ 0.86–0.91 with reasoning shown for OLMo/Nemotron, 0.53 for Qwen; lower for bare or random answers). Copying looks mostly like *tipping* (the peer decides
between answers the agent already half-believes), plus *persuasion* by shown reasoning, and it is silent.

**The four depths of "why"** (the paper's spine):
1. **Triggers**: what makes an agent follow (plausibility, own certainty, shown reasoning, question type)?
2. **Theory**: which model of deference fits: blind copying, tipping (N4), rational evaluation, or persuasion?
3. **Origin**: which training stage creates deference (OLMo-3 base → SFT → DPO → final checkpoints)?
4. **Mechanism**: what happens inside the network (layers, attention, a "deference direction" that can be switched off)?
   Plus: **what reduces it** (an intervention that moves the residual).

## 2. Ground rules (non-negotiable)

**Science**
- Compare against the **item-conditioned null** (each agent's own per-question behaviour), never a global average.
- Expected and observed rates never come from the same samples (Layer 0 samples 0–9 = nulls).
- **Pre-register** every experiment (≤ 5 hypotheses, git-timestamped in `prereg/`) **before** it runs.
  Anything decided after seeing data is labelled exploratory or post-hoc, and reported as such.
- **No LLM labels** in anything that feeds a residual. Grading is code (`cep/checker.py`), frozen and hashed.
- Same pipeline for every model (thinking off, structured JSON, T = 0.7, top-p 0.95, prompt `solver_v1`).
- Be transparent about every mistake, deviation and fix in the research log.

**Working with Shibaditya**
- **Explain first, then execute**, in simple, non-mathematical language.
- Big choices (models, scoring rules, scope) are his: ask with clear options and a recommendation.
- Update `RESEARCH_LOG.md` **and this file** at the end of every step.
- Git: **never commit to `main`**. One branch per step → push → PR → CI green → **ask before merging**.
- Kaggle runs only from pushed commits (`kaggle/push.py` checks this).
- **Hugging Face upload only at the very end** (prepared in `release/`).
- Files Shibaditya must edit go in `labels/` (untracked, so branch switches don't hide them).
- Scratch explainers/roadmaps for him: publish as private artifacts, not in the repo, unless he asks.

## 3. Where everything lives

| What | Path |
|---|---|
| Project folder | `~/Desktop/correlation error` |
| GitHub | https://github.com/shibadityadeb/copy-or-coincidence (public; CI in `.github/workflows/ci.yml`) |
| Field guide (the original plan) | `~/Desktop/Excess_Error_Correlation_Field_Guide_1.pdf` |
| Research log (all details) | `docs/RESEARCH_LOG.md` |
| Pre-registrations | `prereg/` |
| Item generators, normaliser, parser, checker | `cep/` (`cep/generators/`, `cep/sources/`, `cep/checker.py`) |
| Item sets | `datasets/cep_v2/` (current, 600 items) · `datasets/cep_v1/` (frozen, Exp 0 only) |
| Runner, backends, null models, Exp 7 conditions | `coc/` (`runner.py`, `backends.py`, `nulls.py`, `sequential.py`) |
| Agent configs (one per model × agent) | `configs/agents/` |
| Experiment configs | `experiments/` |
| Prompts | `prompts/solver_v1.txt`, `prompts/peer_v1.txt` |
| Analyses | `analysis/` (`exp1.py`, `exp7.py`, `verify_keys.py`, `checker_agreement.py`, `why_follow.py`, `regrade.py`) |
| Raw outputs (append-only JSONL) | `outputs/<experiment>/` |
| Kaggle job helper / downloaded jobs | `kaggle/push.py` · `kaggle/jobs/` (git-ignored) |
| Checker validation | `validation/` (key file git-ignored until labelling ends) |
| Files for Shibaditya to fill in | `labels/` (untracked) |
| HF release recipe | `release/make_hf_release.py`, `release/dataset_card.md` |

**Environment**
- Python venv: `.venv` (Python 3.11, uv). Install: `uv pip install --python .venv/bin/python -e .`
- Kaggle CLI: `~/.local/bin/kaggle`, token in `~/.kaggle/access_token`, user `debshibaditya`.
  2× T4 (15 GB each), **30 GPU-h/week**, resets weekly. `kaggle quota` to check.
- vLLM 0.30 on T4: `max_num_seqs` ≤ 128 for Qwen3.5; prefix caching off; Gemma-4 cannot run (see log).

**Key commands**
```bash
.venv/bin/python -m pytest -q                                   # all tests
.venv/bin/python analysis/verify_keys.py datasets/cep_v2/items.jsonl   # independent key check
.venv/bin/python -m cep.build --version cep_v2                  # rebuild items (must be byte-identical)
.venv/bin/python kaggle/push.py experiments/<exp>.json --run-id run1 --no-wait   # run on Kaggle
.venv/bin/python analysis/exp1.py <layer0 A.jsonl> <layer0 B.jsonl>
.venv/bin/python analysis/exp7.py outputs/<exp7 dir> experiments/<exp7>.json
```

## 4. Models

| Role | Model | Status |
|---|---|---|
| Main | OLMo-3-7B-Instruct (Allen AI; cutoff Dec 2024; open data) | Layer 0, Exp 1, Exp 7 ✅ |
| 2nd family | Qwen3.5-4B (Alibaba) | Layer 0, Exp 1 PASS, Exp 7b ✅ (answer-only/random conditions invalid: Qwen judges the peer) |
| 3rd family | Nemotron-Nano-9B-v2 (NVIDIA; cutoff Sep 2024) | Layer 0, Exp 1 PASS, Exp 7 + 7b ✅ (all H1–H5) |
| Rejected | Gemma-4-E4B (won't run on T4), Phi-4-mini (58% vs OLMo 93%) | — |

## 5. Master checklist

Legend: ✅ done · 🔄 in progress · ⬜ to do · ⏸ postponed (with reason)

### A. Foundations
- ✅ Read guide; plain-language explainer (artifact)
- ✅ Item set `cep_v2`: 600 freshly generated items, 300 with lures
- ✅ Keys: independent solver 600/600; LLM wording review; human audit 30/30
- ✅ Runner, backends, Kaggle pipeline, CI, branch + PR workflow
- ✅ Experiment 0 (pipeline sanity); structured JSON adopted; prefix caching off
- ✅ Null-model code validated on simulated copying
- 🔄 Checker validation: blind LLM reader done (100% on normal replies); **human adjudication of 17 + 15 spot checks pending** (`labels/human_adjudication.md`)

### B. Main results (OLMo)
- ✅ Layer 0 (24,000 answers)
- ✅ Experiment 1 PASS (residual ≈ 0 for non-interacting agents)
- ✅ Experiment 7: H1–H5 all supported; interaction creates ~1/3 of joint error
- ✅ Syllogism "unanswerable" scoring decided (stays a distinct, wrong answer)
- 🔄 Exploratory "why follow" analysis (`analysis/why_follow.py`, not yet committed): plausibility modulates adoption,
  persuasion by steps, fabrication contagion on missing-premise items, silent conformity (its "tipping" reading was
  corrected by the formal N4 test)

### C. Replication across families
- ✅ Qwen3.5-4B: Layer 0, Exp 1 PASS, Exp 7 (misread protocol), Exp 7b (H1, H4, H5 supported; H2/H3 invalid)
- ✅ Nemotron-Nano-9B-v2: Layer 0, Exp 1 PASS, Exp 7 and Exp 7b (H1–H5 supported in both)
- ✅ Experiment 7b (clarified message, all three families): replication criterion met; framing robustness ✅
- ✅ Three-family comparison (`analysis/compare_families.py`)
- ✅ Kaggle environment pinned after Kaggle's image change (`kaggle/env.json`)

### D. Gaps from the field guide: 🔴 critical
- ✅ **N4 mode-finding null**: rejected — receivers follow the shown answer (97–100%), not the joint mode (0–3%); few contested items
- ⬜ **Helpful vs harmful flips (h vs g)** and content-blind flip: answer-first-then-revise protocol (GPU)
- ✅ **Three-way error decomposition**: shared 37–69%, interaction-created 28–57% of post-exposure errors; amplification beyond N4 not estimable (too few contested lure items)
- ⬜ **Mixed-effects model** (condition × family × error type; item + template random effects) + paired McNemar
- ⬜ **Comparison with prior work**: Kim et al. / Goel et al. (CAPA) metrics on our data; how much survives item-conditioning

### E. Gaps from the field guide: 🟠 important
- ⬜ **Q1 similarity**: cross-family solo error similarity at matched accuracy (JSD, error identity vs item baseline)
- ⬜ Mechanism controls **E** (answer hidden), **F** (conclusion flipped, N10), **G** (displayed confidence), **D** (other-model answer)
- ⬜ Alternative-explanation checks: formatting convergence; A restating the question
- ⬜ Empirical power analysis from Layer 0 distributions
- ⬜ Error identity P(same wrong | both wrong) vs item baseline; conditional mutual information
- ⬜ Theory section: residual ↔ Tumer–Ghosh ρ / Condorcet; implications for majority voting
- ⬜ One intervention that moves the residual (answer-first, forced dissent "ally", missing-info warning)

### F. The "why" depths
- 🔄 Depth 2 theory: deference-weight model beats N3, mixture, N4 and pure copy everywhere; α per model × condition ✅. Still to do: rational-evaluator model (does α differ for right vs wrong shown answers?) and plausibility-dependent α
- ⬜ Depth 3 origin: same Exp 7 on OLMo-3 base, SFT, DPO, final checkpoints
- ⬜ Depth 4 mechanism: logit lens, attention to peer answer vs steps, "deference direction" + ablation
- ⬜ Optional: thinking on vs off (OLMo-3-7B-Think vs Instruct)

### G. 🟡 Secondary / postponed
- ⏸ 4th item family (constraint/planning: ZebraLogic, Game of 24)
- ⏸ Step-level error signatures (N6); debate rounds; chains of 3–4 agents; verifier lineage (Exp 9)
- ⏸ Size ladder, prompt diversity, shared evidence (Exp 2, 5, 6)
- ⬜ Session-stability check: Layer 0 accuracy within 2 points across two sessions
- ⬜ Search OLMo's public training data (Dolma 3) for item text

### H. Paper and release
- ⬜ Combined statistics and figures across families
- ⬜ Paper draft (workshop first, then main conference with Depth 3–4)
- ⬜ Validity plan: every row ✅ (see research log §4b)
- ⬜ Hugging Face release of `cep_v2` (only at the end)

## 6. Open branches and pull requests (update when they change)

| Branch | Content | PR |
|---|---|---|
| `why/n4-tipping` | N4 test, deference models, error decomposition (plan + results) | to open |
| `gemma/flex-attention` | Gemma attempts, log of the T4 failure | not opened (log entries only) |
| `validation/checker-labels` | Label sheet, agreement script, blind-reader result | not opened yet (waiting on human adjudication) |
| `analysis/why-follow` | (local) exploratory why-follow analysis, uncommitted | — |
| `replication/qwen` | superseded: fully contained in `exp7b/peer-v2` | — |

## 7. Session start routine (for Claude)

1. Read this file, then the latest sections of `RESEARCH_LOG.md`.
2. `git status`, `git branch`, `gh pr list` — reconcile with section 6.
3. Check running Kaggle jobs (`kaggle kernels status debshibaditya/<slug>`) and `kaggle quota`.
4. Check `labels/` for anything Shibaditya has filled in.
5. Tell him where things stand in plain words before doing anything new.
