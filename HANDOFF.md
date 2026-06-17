# Handoff — 2026-06-16

## ⚡ In-flight work

Clean stop. No task was mid-execution.

**Last actions this session:**
1. Confirmed full codebase already committed to GitHub (all 5 modules present)
2. Populated `julia_profile.md` Job Search Preferences section with salary floors, target domains, and salary-filter rule

**Next concrete step:**
```
cd C:\Users\jules\job-search-bot
pip install -r requirements.txt
playwright install chromium
python cli.py list          # smoke test: verifies DB init
python cli.py tailor 1      # smoke test: verifies Claude API call (needs ANTHROPIC_API_KEY set)
```

---

## ❓ Open decisions

- Remote/hybrid/onsite preference — not filled in yet
- Company size preference — not filled in yet
- Companies to target or avoid — not filled in yet
- LinkedIn scraping: does Julia have a LinkedIn session we can export as a cookie/storage_state file, or should we skip LinkedIn and focus on Indeed + direct company careers pages?

---

## 🆕 New gotchas this session

None beyond what's already in STATUS.md.

---

## 📁 Project path

`C:\Users\jules\job-search-bot`

Claude project dir: `C:\Users\jules\.claude\projects\C--Users-jules\`

---

## 📜 Transcript path

`C:\Users\jules\.claude\projects\C--Users-jules\dee05438-dfb3-44ba-97b0-4a307929730d.jsonl`

Grep only on demand — do not read eagerly.
