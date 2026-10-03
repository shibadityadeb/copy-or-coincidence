# copy-or-coincidence

Research project: when LLM agents give the same wrong answer, how much is coincidence and how much is
copying, and why. Goal: a deep, conference-grade paper that explains *why*.

**Start every session by reading `docs/PROJECT_PLAN.md`** (goal, rules, paths, master checklist), then the
latest entries in `docs/RESEARCH_LOG.md`. Keep both updated at the end of every step.

Non-negotiables (details in the plan):
- Explain first, then execute, in plain non-mathematical language; big choices are Shibaditya's.
- Never commit to `main`: branch → PR → green CI → ask before merging.
- Pre-register every experiment in `prereg/` before running it; label anything post-hoc.
- No LLM labels in anything that feeds a residual; grading is `cep/checker.py`.
- Files for Shibaditya to fill in go in `labels/` (untracked).
- Hugging Face dataset upload only at the very end.
