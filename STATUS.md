# Job Search Bot — Project Bible

> Julia's personal job search assistant. A Flask dashboard (local desktop
> app, autostarts at login) shows jobs found by a daily automated search
> that runs on GitHub Actions (weekdays 8am PT), scored against her TPM
> job-search criteria, with Gemini-powered resume tailoring and cover
> letters, and Playwright-based ATS autofill for applying.
>
> **This doc was badly out of date until 2026-08-20** — it previously
> described a CLI-only, Claude-API, "not yet smoke-tested" tool. All of
> that changed June 17-18, 2026 (dashboard added, Claude swapped for
> Gemini, GitHub Actions automation added) but the docs were never
> updated. Rewritten from the real code + git history + live GitHub
> Actions run history on 2026-08-20 — verify against the repo if anything
> here looks stale again.

---

## Stack & Services

| Component | Detail |
|-----------|--------|
| Language | Python 3.12 |
| Dashboard | Flask (`dashboard.py`), local desktop app on `http://localhost:5056` |
| Autostart | `start_dashboard.vbs` in Windows Startup folder — launches `dashboard.py` at login if not already running |
| Daily search | GitHub Actions (`.github/workflows/daily_search.yml`), cron `0 15 * * 1-5` (8am PT weekdays) + manual `workflow_dispatch` |
| Job sources | **Local runs:** Playwright scraping LinkedIn/Indeed (`bot/search.py`). **Cloud/CI runs:** Remotive API + Jobicy RSS (`bot/feed_search.py`) — no Playwright, avoids cloud-IP blocks. `daily_run.py` auto-picks RSS mode when `GITHUB_TOKEN` is set or `USE_RSS=true`. |
| Data store | `data/jobs.json` — **not gitignored, committed to the repo.** CI runs commit fresh results back to `main` directly (`permissions: contents: write` in the workflow). `jobs.db` (SQLite) also exists from an earlier design but is not the active store — `bot/store.py` reads/writes the JSON file. |
| AI | Google Gemini (`gemini-2.5-flash`, free tier) via `google-generativeai` SDK — swapped from Anthropic Claude 2026-06-18 (`bot/tailor.py`) |
| ATS autofill | Playwright (non-headless, `bot/autofill.py` + `bot/autofill_runner.py`) — leaves browser open for human review before submit |

**To run the dashboard locally:**
```
pip install -r requirements.txt
playwright install chromium
python dashboard.py          # http://localhost:5056
```

**Required env vars** (`.env`, gitignored): `GEMINI_API_KEY`, `WEB_PASSWORD`, `WEB_SECRET`. CI additionally needs `GITHUB_TOKEN` (auto-provided) — no Gemini key needed for the search-only cron job, only for tailoring/cover-letter features run from the dashboard.

---

## File Map

| Path | Purpose |
|------|---------|
| `julia_profile.md` | Master career profile — resume content, persona map, Drive file IDs, job search preferences |
| `dashboard.py` | Flask app — the actual daily-use interface (review jobs, tailor, apply) |
| `daily_run.py` | Search orchestrator — RSS (cloud) or Playwright (local), scores + salary-filters + saves top 10 |
| `cli.py` | Original CLI entry point (search/list/status/tailor/cover/apply) — still works, but the dashboard is the primary interface now |
| `bot/feed_search.py` | Cloud-safe search: Remotive API + Jobicy RSS, no auth needed |
| `bot/search.py` | Playwright scrapers for LinkedIn/Indeed — local-only, LinkedIn blocks headless/cloud |
| `bot/score.py` | Scores + filters jobs against Julia's criteria — title-relevance gate (fixed 2026-08-20, see Hard-Won Gotchas), domain keywords, salary floor |
| `bot/store.py` | Unified job store — local file I/O or GitHub API depending on environment |
| `bot/tailor.py` | Gemini-powered resume tailoring, cover letters, persona auto-picker |
| `bot/autofill.py` / `autofill_runner.py` | ATS form filler — Greenhouse, Lever, Workday, LinkedIn Easy Apply |
| `data/jobs.json` | **The live dataset.** Committed to git, updated daily by CI. |
| `tests/test_score.py` | Regression tests for the title-relevance gate (added 2026-08-20) |
| `.github/workflows/daily_search.yml` | The actual daily automation — check `gh run list --workflow "Daily Job Search"` for real run history, don't assume from local file dates |

---

## What Works (Verified 2026-08-20)

- Dashboard runs cleanly (`python dashboard.py` → real Flask app on :5056, confirmed by direct local run)
- GitHub Actions daily search has been running successfully every weekday since ~June 18 with zero failures except one (2026-08-06) — confirmed via `gh run list`
- Title-relevance gate in `bot/score.py` now correctly filters: verified live against a real fresh Remotive/Jobicy pull (17 listings, 0 false positives, 0 false negatives among genuinely-irrelevant roles)
- ATS autofill, dedup, Apply-button fixes all merged and presumably working (not re-verified this session — no smoke test performed on autofill specifically)

**Known gap, not yet fixed:** the job *sources* themselves (Remotive API, Jobicy RSS) rarely surface genuinely relevant TPM/Staff-Program-Manager postings even when queried with on-target search terms — see Pending/Blocked.

---

## Job Search Preferences (from julia_profile.md)

- **Role:** Senior / Staff TPM
- **Domains (priority):** Cloud infra/DevSecOps → AI/ML platform → Data & Analytics → Network/security
- **US salary floor:** ~$150K USD base
- **CA salary floor:** $130K CAD base
- **Salary rule:** Skip postings with no salary unless mega-cap (Google, Microsoft, Amazon, Meta, Apple, Nvidia, Salesforce, Adobe, EA, etc. — full list in `bot/score.py:MEGA_CAPS`)
- **Location:** Bellevue/Seattle WA (hybrid/remote) + Europe (remote preferred)
- **Still TBD:** remote/hybrid pref, company size, target/avoid list (same open questions as June, never resolved)

---

## Hard-Won Gotchas

- **LinkedIn blocks anon/cloud scraping** — this is why `daily_run.py` has two paths: Playwright locally, RSS/API-based (`bot/feed_search.py`) on GitHub Actions. Never assume the CI run and a local run collect from the same sources.
- **`bot/score.py`'s skip logic used to ignore title relevance entirely (fixed 2026-08-20).** `score_job()` computed a title-match score but never used it to gate `should_skip` — only salary/mega-cap status did. A completely unrelated role (e.g. "Head of Marketing & Communications" at $150k-$230k) passed straight through. Confirmed two real examples live in `data/jobs.json` history (ids 24, 26) before the fix. Now the title-relevance check runs first and skips immediately on zero match. Regression tests in `tests/test_score.py`.
- **Local checkout can silently drift from what CI has been doing.** Found this session: local `main` was 2 months behind `origin/main` even though `git status` showed no conflicting local changes — CI had been committing fresh `data/jobs.json` updates every weekday the whole time. Always `git pull origin main` before trusting local file dates/content for this repo; the daily cron is the source of truth, not whatever's on disk locally.
- **`jobs.db` (SQLite) is a red herring** — it exists from an earlier design (see old STATUS.md history) but `bot/store.py` actually reads/writes `data/jobs.json`. Don't debug against `jobs.db`.
- **Autostart VBS depends on a reboot/login to trigger** — it doesn't retroactively start the dashboard if it's not already running. If the dashboard seems down, just run `python dashboard.py` directly rather than waiting for a relogin.

---

## Pending / Blocked

- **Job-source relevance (found 2026-08-20, not yet fixed).** After fixing the title-relevance gate, a live test pull from Remotive + Jobicy returned 17 listings for TPM-targeted search terms — **zero** were genuinely TPM/program-management roles (Patient Care Specialist, AI Engineer, Sales rep, Copywriter, etc.). This explains why only 16 jobs total were saved across 2 months of daily runs: it's not (only) a filtering problem, the sources themselves aren't surfacing relevant postings even when queried directly for "technical program manager" / "staff TPM" / etc. This is an **architecture decision, not a quick fix** — per this repo's standing convention (see global CLAUDE.md), evaluate alternatives before building: other free/no-auth-friendly job APIs (Adzuna, USAJobs for gov roles, Arbeitnow, We Work Remotely's RSS, Greenhouse/Lever job-board aggregation by company), a curated target-company list scraped directly (career pages tend to be more reliable than aggregators), or accepting Playwright-via-residential-proxy for LinkedIn/Indeed even in CI. Needs a real evaluation pass, not a guess.
- Salary filter logic — now real (title gate + salary floor both enforced in `bot/score.py`), but still worth revisiting once source relevance is fixed and real volume goes up.
- LinkedIn logged-in session for local Playwright runs — never set up; local runs may still be unreliable for LinkedIn specifically.
- Remote/hybrid/onsite preference, company size preference, target/avoid company list — still not filled in in `julia_profile.md` (same as June).

---

## Conventions

- Persona keys: `pgm`, `biz`, `cx`, `apac`, `network`, `usa`, `bsa` — defined in `bot/tailor.py:PERSONA_HINTS`
- Default personal info (email, phone, LinkedIn URL) lives in `bot/autofill.py:DEFAULTS`
- Job statuses: `found → applied → interviewing → offer / rejected / skipped`
- Never commit `.env` — `data/jobs.json` **is** meant to be committed (that's how CI publishes results), don't gitignore it
- Commit style: clear sentence describing what + why (no "fix" or "changes")
- Branch → commit → push → PR → merge, same as every other project (global CLAUDE.md convention) — this repo has no PR-triggered CI to wait for, verify locally before merging
