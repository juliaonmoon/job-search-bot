#!/usr/bin/env python3
"""Daily job search orchestrator.

Cloud (GitHub Actions): uses RSS feed search — no Playwright, no IP blocks.
Local:                  uses Playwright scrapers for richer results.

Saves top 10 scored, salary-filtered jobs to the store.
"""
import asyncio
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bot.score import score_job
from bot.store import add_job, init_db

BATCH = date.today().isoformat()
TOP_N = 10
USE_RSS = os.getenv("USE_RSS", "").lower() in ("1", "true", "yes") or bool(os.getenv("GITHUB_TOKEN"))


def collect_rss() -> list[dict]:
    from bot.feed_search import run_feed_search
    return run_feed_search()


async def collect_playwright() -> list[dict]:
    from bot.search import search_linkedin, search_indeed

    QUERIES = [
        ("Technical Program Manager",        "Seattle, WA"),
        ("Technical Program Manager",        "Bellevue, WA"),
        ("Staff TPM",                        "Seattle, WA"),
        ("Senior Technical Program Manager", "Remote"),
        ("Staff Program Manager cloud",      "Remote"),
        ("TPM AI platform",                  "Remote"),
        ("Principal Program Manager",        "Seattle, WA"),
    ]

    seen: set[str] = set()
    jobs: list[dict] = []
    for query, location in QUERIES:
        print(f"  Scraping '{query}' in {location} …")
        try:
            for j in await search_linkedin(query, location, limit=15) + await search_indeed(query, location, limit=15):
                if j.get("url") and j["url"] not in seen:
                    seen.add(j["url"])
                    jobs.append(j)
        except Exception as e:
            print(f"    [warn] {e}")
    return jobs


def run():
    init_db()
    print(f"\n=== Daily Job Search — {BATCH} ===")
    print(f"Mode: {'RSS (cloud)' if USE_RSS else 'Playwright (local)'}\n")

    if USE_RSS:
        all_jobs = collect_rss()
    else:
        all_jobs = asyncio.run(collect_playwright())

    print(f"\nCollected {len(all_jobs)} unique listings. Scoring …\n")

    scored = []
    for j in all_jobs:
        jd = j.get("jd_full", "") or j.get("jd_snippet", "") or ""
        sc, skip = score_job(j["title"], j["company"], jd, j.get("salary_text", ""))
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
        print(f"  [{tag}] {j['score']:>3}pts  {j['company']:<28} {j['title']}")

    print(f"\nDone. {saved} new job(s) added.")
    if not os.getenv("GITHUB_TOKEN"):
        print("Open http://localhost:5056 to review.\n")


if __name__ == "__main__":
    run()
