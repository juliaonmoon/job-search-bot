"""API-based job search for cloud runners (no Playwright, no API key needed).

Sources:
  - Remotive.com API: free, no auth, focused on remote tech jobs
  - Jobicy.com RSS: free, no auth, covers remote roles

Used by GitHub Actions daily cron where LinkedIn/Indeed block cloud IPs.
"""
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


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


# ---------------------------------------------------------------------------
# Source 1: Remotive (free API, no key, remote tech jobs)
# ---------------------------------------------------------------------------

REMOTIVE_SEARCHES = [
    "technical program manager",
    "staff TPM",
    "senior TPM",
    "principal program manager",
    "TPM cloud",
    "TPM AI",
]


def search_remotive(search_term: str, limit: int = 30) -> list[dict]:
    """Query Remotive's free public API."""
    q = urllib.parse.quote_plus(search_term)
    url = f"https://remotive.com/api/remote-jobs?search={q}&limit={limit}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"    [remotive warn] {search_term}: {e}")
        return []

    results = []
    for job in data.get("jobs", []):
        title   = job.get("title", "")
        company = job.get("company_name", "Unknown")
        loc     = job.get("candidate_required_location", "Remote")
        link    = job.get("url", "")
        salary  = job.get("salary", "") or ""
        desc    = _strip_html(job.get("description", ""))
        if not salary:
            salary = _extract_salary_hint(desc + " " + title)

        if title and link:
            results.append({
                "title":       title,
                "company":     company,
                "location":    loc or "Remote",
                "url":         link,
                "source":      "remotive",
                "salary_text": salary,
                "jd_snippet":  desc[:800],
            })
    return results


# ---------------------------------------------------------------------------
# Source 2: Jobicy (free RSS, no auth, remote jobs)
# ---------------------------------------------------------------------------

JOBICY_SEARCHES = [
    "technical-program-manager",
    "program-manager",
]


def search_jobicy_rss(tag: str, limit: int = 20) -> list[dict]:
    """Fetch Jobicy RSS feed filtered by job tag."""
    url = f"https://jobicy.com/?feed=job_feed&job_categories={tag}&job_types=full-time&search_region=usa"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_bytes = resp.read()
    except Exception as e:
        print(f"    [jobicy warn] {tag}: {e}")
        return []

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []

    ns = {"jobicy": "https://jobicy.com"}
    results = []
    for item in root.findall(".//item")[:limit]:
        title   = _strip_html(item.findtext("title", ""))
        company = _strip_html(item.findtext("jobicy:hiringOrganization", "", ns))
        loc     = _strip_html(item.findtext("jobicy:jobLocation", "Remote", ns)) or "Remote"
        link    = item.findtext("link", "")
        desc    = _strip_html(item.findtext("description", ""))
        salary  = _extract_salary_hint(desc + " " + title)

        if title and link:
            results.append({
                "title":       title,
                "company":     company or "Unknown",
                "location":    loc,
                "url":         link,
                "source":      "jobicy",
                "salary_text": salary,
                "jd_snippet":  desc[:800],
            })
    return results


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_feed_search() -> list[dict]:
    """Run all cloud-friendly searches; deduplicate by URL."""
    seen: set[str] = set()
    all_jobs: list[dict] = []

    for term in REMOTIVE_SEARCHES:
        print(f"  Remotive: '{term}' …")
        for j in search_remotive(term):
            if j["url"] and j["url"] not in seen:
                seen.add(j["url"])
                all_jobs.append(j)

    for tag in JOBICY_SEARCHES:
        print(f"  Jobicy RSS: '{tag}' …")
        for j in search_jobicy_rss(tag):
            if j["url"] and j["url"] not in seen:
                seen.add(j["url"])
                all_jobs.append(j)

    return all_jobs
