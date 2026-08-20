# Handoff — 2026-08-20

## ⚡ In-flight work

**Clean stop.** No task mid-execution.

This session started by re-reading the old (2026-06-16) STATUS.md/HANDOFF.md,
which described a CLI-only, Claude-API tool that was "not yet smoke-tested."
That was badly stale — real git history showed extensive work happened
June 17-18 (Flask dashboard, Claude→Gemini swap, ATS autofill, GitHub Actions
daily automation) that was never reflected in the docs, and local `main` was
2 months behind `origin/main` even though nothing looked obviously wrong
locally (see new gotcha below).

**What actually happened this session:**
1. Synced local `main` to `origin/main` (was 2 months behind — CI had been
   committing fresh `data/jobs.json` updates every weekday the whole time).
2. Confirmed `dashboard.py` runs cleanly locally (real Flask app, port 5056).
3. Confirmed via `gh run list` that the daily GitHub Actions search has been
   running successfully essentially every weekday since June 18.
4. Found a real bug while checking data quality: recent job results included
   things like "Head of Marketing & Communications" and "Sales Jedi" —
   nothing to do with TPM roles. Root-caused it to `bot/score.py`:
   `score_job()` computed a title-relevance score but never used it to gate
   `should_skip` — the skip decision was purely salary/mega-cap based, so
   any unrelated role with a disclosed salary above the floor (or a
   dollar-figure false match in the JD text) passed straight through.
5. Fixed it (title-relevance check now runs first, hard-skips on zero
   match), added `tests/test_score.py` (8 tests, including the two real
   garbage examples as regression cases), shipped via
   branch → commit → push → PR → merge (PR #13, merged to `main`).
6. Manually triggered the daily search workflow to verify live. It worked
   correctly — 17 fresh listings collected, 0 passed the filter, and a
   local re-run with per-listing visibility confirmed all 17 were
   genuinely irrelevant (Patient Care Specialist, AI Engineer, Copywriter,
   etc.), not a false-negative problem.
7. That verification surfaced a **deeper, unfixed problem**: the job
   *sources* (Remotive API, Jobicy RSS) essentially never return real TPM
   postings even when queried directly for "technical program manager" /
   "staff TPM" / etc. This is why only 16 jobs total got saved across 2
   months of daily runs. Not fixed this session — it's an architecture
   decision (which job source(s) to use), not a bug fix, and the global
   CLAUDE.md convention says to evaluate alternatives and get confirmation
   before building, not guess at a new data source unilaterally.
8. Rewrote STATUS.md from scratch against the real code + git history +
   live GitHub Actions run history, since the old version was actively
   misleading (wrong AI provider, wrong primary interface, wrong "not yet
   tested" status).

**Next concrete step:** decide on a job-source strategy. Candidates worth
evaluating (not yet researched in depth): Adzuna API, Arbeitnow, We Work
Remotely's RSS, direct career-page scraping for a curated target-company
list, or Playwright-via-proxy for LinkedIn/Indeed even in CI. Whoever picks
this up should do a quick evaluation pass (what's free, what actually
returns TPM-relevant results for a test query, reliability) before building
against any of them — same standard just applied to the Michigan/Oklahoma
tax-lien-guide collectors this same session (verify data quality against
the real source before committing to build on it).

---

## ❓ Open decisions

- **Job-source strategy** (see above) — needs a real evaluation, not a
  unilateral pick.
- Remote/hybrid/onsite preference — not filled in yet (same as June)
- Company size preference — not filled in yet (same as June)
- Companies to target or avoid — not filled in yet (same as June)
- LinkedIn scraping for local runs: does Julia have a LinkedIn session to
  export as a cookie/storage_state file? (same open question as June,
  still unresolved, lower priority than the source-strategy question above)

---

## 🆕 New gotchas this session

- **A repo can look "fine" locally while being badly out of sync with what
  automation has actually been doing.** Local `main` was 2 months behind
  `origin/main`, `git status` showed no scary conflicts, and the local
  `data/jobs.json` just looked like old-but-plausible data rather than
  obviously stale. Always `git pull origin main` and check `gh run list`
  for the relevant workflow before trusting local state on a repo with
  CI-driven automated commits — the cron job, not the local checkout, is
  the source of truth here.
- **A workflow reporting `success` doesn't mean it's producing anything
  useful.** `daily_search.yml` had a 100% success rate for 2 months while
  the underlying job sources were returning almost entirely irrelevant
  postings. "Green CI" here only meant "the script didn't crash," not
  "the feature works" — same lesson as this session's global instructions
  already state about test suites vs. feature correctness, just showing up
  in a different shape (a cron job instead of a test suite).

---

## 📁 Project path

`C:\Users\jules\job-search-bot`

Note: `C:\Users\jules\Usersjulesjob-search-bot` also exists — looks like a
stray/duplicate clone from an earlier `git clone` mistake (bad path,
outdated content, no STATUS.md/HANDOFF.md). Not touched this session; flag
to Julia before deleting it, in case it holds something not in the real repo.

---

## 📜 Transcript path

Not recorded for this session (see the harness's own session log if exact
wording is ever needed — no dedicated transcript file path was available
in this environment the way earlier handoffs describe).
