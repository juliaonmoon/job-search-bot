"""RSS-based job search — reliable from cloud runners (no Playwright needed).

Indeed has a public RSS feed. This is used by GitHub Actions daily cron
so LinkedIn/Indeed don't block cloud IPs hitting a headless browser.
"""
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date

from bot.score import _extract_salary_hint as _sal_hint  # reuse regex


def _extract_salary_hint(text: str) -> str:
    patterns = [
        r'\$\s*\d{1,3},\d{3}\s*[-–]\s*\$?\s*\d{1,3},\d{3}',
        r'\$\s*\d{2,3}[kK]\s*[-–]\s*\$?\s*\d{2,3}[kK]',
        r'\$\s*\d{2,3}[kK]',
        r'\$\s*\d{1,3},\d{3}',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return ""


def _strip_html(s: str) -> str:
    return re.sub(r'<[^>]+>', ' ', s or "").strip()


def search_indeed_rss(keywords: str, location: str = "Seattle, WA",
                      days: int = 7, limit: int = 25) -> list[dict]:
    """Fetch Indeed RSS feed — no browser, works from any IP."""
    q = urllib.parse.quote_plus(keywords)
    l = urllib.parse.quote_plus(location)
    url = f"https://www.indeed.com/rss?q={q}&l={l}&fromage={days}&sort=date"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_bytes = resp.read()
    except Exception as e:
        print(f"    [rss warn] {keywords}/{location}: {e}")
        return []

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []

    results = []
    for item in root.findall(".//item")[:limit]:
        title   = _strip_html(item.findtext("title", ""))
        company_raw = item.findtext("{com.indeed}company", "") or ""
        company = _strip_html(company_raw)
        loc_raw = item.findtext("{com.indeed}city", "") or item.findtext("{com.indeed}state", "")
        loc     = _strip_html(loc_raw) or location
        link    = item.findtext("link", "")
        desc    = _strip_html(item.findtext("description", ""))
        salary  = _extract_salary_hint(desc + " " + title)

        if title and link:
            results.append({
                "title":       title,
                "company":     company or "Unknown",
                "location":    loc,
                "url":         link,
                "source":      "indeed",
                "salary_text": salary,
                "jd_snippet":  desc[:800],
            })

    return results


# namespace shim for urllib.parse used inside the function above
import urllib.parse  # noqa: E402 (already imported transitively but explicit is fine)


SEARCH_QUERIES = [
    ("Technical Program Manager",        "Seattle, WA"),
    ("Technical Program Manager",        "Bellevue, WA"),
    ("Staff TPM",                        "Seattle, WA"),
    ("Senior Technical Program Manager", "Remote"),
    ("Staff Program Manager cloud",      "Remote"),
    ("TPM AI platform",                  "Remote"),
    ("Principal Program Manager",        "Seattle, WA"),
]


def run_feed_search() -> list[dict]:
    """Run all RSS queries; deduplicate by URL."""
    seen: set[str] = set()
    all_jobs: list[dict] = []

    for query, location in SEARCH_QUERIES:
        print(f"  RSS: '{query}' in {location} …")
        for j in search_indeed_rss(query, location):
            if j["url"] and j["url"] not in seen:
                seen.add(j["url"])
                all_jobs.append(j)

    return all_jobs
