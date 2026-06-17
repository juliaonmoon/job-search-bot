# Job Search Bot — Project Bible

> Julia's personal job search assistant: scrapes LinkedIn/Indeed, tracks applications in SQLite, uses Claude to tailor resumes and cover letters per persona, and auto-fills ATS forms.

---

## Stack & Services

| Component | Detail |
|-----------|--------|
| Language | Python 3.11+ |
| CLI entry | `python cli.py <command>` |
| Database | SQLite — `jobs.db` (auto-created on first run via `init_db()`) |
| Scrapers | Playwright (Chromium, headless) |
| AI | Claude API via `anthropic` SDK (`claude-sonnet-4-6`) |
| ATS autofill | Playwright (non-headless, leaves browser open for human review) |

**To install:**
```
pip install -r requirements.txt
playwright install chromium
```

**Required env var:** `ANTHROPIC_API_KEY`

---

## File Map

| Path | Purpose |
|------|---------|
| `C:\Users\jules\job-search-bot\julia_profile.md` | Master career profile — source of truth for all resume content, persona map, Google Drive file IDs, job search preferences |
| `cli.py` | CLI entry point — commands: search, list, status, tailor, cover, apply |
| `bot/db.py` | SQLite schema + CRUD (add_job, update_status, list_jobs, get_job) |
| `bot/search.py` | Playwright scrapers for LinkedIn and Indeed (past-week filter); `scrape_careers_page()` for direct company pages |
| `bot/tailor.py` | Claude-powered resume tailoring, cover letter generation, persona auto-picker |
| `bot/autofill.py` | ATS form filler — Greenhouse, Lever, Workday, LinkedIn Easy Apply |
| `requirements.txt` | `anthropic>=0.30.0`, `playwright>=1.44.0` |
| `jobs.db` | SQLite DB (gitignored, created at runtime) |

---

## What Works (Verified)

- `julia_profile.md` — fully populated with career history, certs, achievements, persona map, Drive file IDs, and job search preferences
- All bot modules written and committed to GitHub (`juliaonmoon/job-search-bot`, private)
- CLI commands wired end-to-end: search → list → status → tailor → cover → apply

**Not yet smoke-tested** — install + first run pending.

---

## Job Search Preferences (from julia_profile.md)

- **Role:** Senior / Staff TPM
- **Domains (priority):** Cloud infra/DevSecOps → AI/ML platform → Data & Analytics → Network/security
- **US salary floor:** ~$150K USD base
- **CA salary floor:** $130K CAD base
- **Salary rule:** Skip postings with no salary unless mega-cap (Google, Microsoft, Amazon, Meta, Apple, Nvidia, Salesforce, Adobe, EA, etc.)
- **Location:** Bellevue/Seattle WA (hybrid/remote) + Europe (remote preferred)
- **Still TBD:** remote/hybrid pref, company size, target/avoid list

---

## Hard-Won Gotchas

- **LinkedIn blocks anon scraping** — `search.py` scrapes the public jobs page but LinkedIn aggressively blocks headless browsers. May need to inject a logged-in session cookie (`--cookies` flag or manual `storage_state` in Playwright) before LinkedIn searches work reliably.
- **ATS selectors drift** — Greenhouse/Lever/Workday update their DOM frequently. `autofill.py` selectors are best-effort; always leave browser open (`headless=False`) for human review before submit.
- **jobs.db is gitignored** — must be created fresh on each machine via `python cli.py list` (or any command that calls `init_db()`).

---

## Pending / Blocked

- Salary filter logic not enforced in code — only documented in `julia_profile.md`. Needs implementation in `bot/search.py` or as a post-filter in `cmd_search`.
- LinkedIn logged-in session: needs cookie/storage_state approach before scraper is reliable.

---

## Conventions

- Persona keys: `pgm`, `biz`, `cx`, `apac`, `network`, `usa`, `bsa` — defined in `bot/tailor.py:PERSONA_HINTS`
- Default personal info (email, phone, LinkedIn URL) lives in `bot/autofill.py:DEFAULTS`
- Job statuses: `found → applied → interviewing → offer / rejected / skipped`
- Never commit `jobs.db` or `.env` files
- Commit style: clear sentence describing what + why (no "fix" or "changes")
