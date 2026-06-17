#!/usr/bin/env python3
"""Daily job search orchestrator.

Searches LinkedIn + Indeed for TPM roles, scores each listing,
and saves the top 10 new matches to the database.

Run manually:  python daily_run.py
Task Scheduler: 8:00 AM Mon-Fri
"""
import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bot.db import init_db, add_job
from bot.score import score_job
from bot.search import search_linkedin, search_indeed

SEARCH_QUERIES = [
    ("Technical Program Manager", "Seattle, WA"),
    ("Technical Program Manager", "Bellevue, WA"),
    ("Staff TPM", "Seattle, WA"),
    ("Senior Technical Program Manager", "Remote"),
    ("Staff Program Manager cloud", "Remote"),
    ("TPM AI platform", "Remote"),
    ("Principal Program Manager", "Seattle, WA"),
]

TOP_N = 10
BATCH = date.today().isoformat()


async def _collect_all() -> list[dict]:
    """Collect raw listings from all queries; deduplicate by URL."""
    seen_urls: set[str] = set()
    all_jobs: list[dict] = []

    for query, location in SEARCH_QUERIES:
        print(f"  Searching '{query}' in {location} …")
        try:
            li_jobs = await search_linkedin(query, location, limit=15)
            in_jobs = await search_indeed(query, location, limit=15)
            for j in li_jobs + in_jobs:
                url = j.get("url") or ""
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_jobs.append(j)
        except Exception as e:
            print(f"    [warn] {query} / {location}: {e}")

    return all_jobs


def run():
    init_db()
    print(f"\n=== Daily Job Search — {BATCH} ===\n")

    all_jobs = asyncio.run(_collect_all())
    print(f"\nCollected {len(all_jobs)} unique listings. Scoring …\n")

    scored: list[dict] = []
    for j in all_jobs:
        jd_text  = j.get("jd_full", "") or j.get("jd_snippet", "") or ""
        sal_text = j.get("salary_text", "")
        sc, skip = score_job(j["title"], j["company"], jd_text, sal_text)
        if not skip:
            scored.append({**j, "score": sc})

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:TOP_N]

    print(f"After salary filter: {len(scored)} eligible. Saving top {TOP_N}:\n")

    saved = 0
    for j in top:
        ok = add_job(
            title=j["title"],
            company=j["company"],
            location=j.get("location", ""),
            url=j["url"],
            source=j["source"],
            jd_snippet=j.get("jd_snippet", ""),
            salary_text=j.get("salary_text", ""),
            score=j["score"],
            jd_full=j.get("jd_full", ""),
            daily_batch=BATCH,
        )
        tag = "NEW" if ok else "dup"
        if ok:
            saved += 1
        print(f"  [{tag}] {j['score']:>3}pts  {j['company']:<30} {j['title']}")

    print(f"\nDone. {saved} new job(s) added to DB.")
    print("Open http://localhost:5056 to review.\n")


if __name__ == "__main__":
    run()
