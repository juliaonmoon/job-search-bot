"""Job board scrapers using Playwright."""
import asyncio
import re
from datetime import date, timedelta
from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from bot.db import add_job


def _parse_relative_date(text: str) -> str:
    """'Posted 2 days ago' / 'Just posted' → YYYY-MM-DD, or empty string."""
    t = (text or "").lower()
    if "just posted" in t or "today" in t:
        return date.today().isoformat()
    m = re.search(r'(\d+)\s+hour', t)
    if m:
        return date.today().isoformat()
    m = re.search(r'(\d+)\s+day', t)
    if m:
        return (date.today() - timedelta(days=int(m.group(1)))).isoformat()
    m = re.search(r'(\d+)\s+week', t)
    if m:
        return (date.today() - timedelta(weeks=int(m.group(1)))).isoformat()
    return ""


# ── helpers ──────────────────────────────────────────────────────────────────

async def _new_browser(p, headless=True):
    return await p.chromium.launch(headless=headless)


def _extract_salary_hint(text: str) -> str:
    """Pull raw salary string from page text."""
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


async def _fetch_jd(page, url: str) -> tuple[str, str]:
    """Visit job detail page; return (jd_text[:6000], salary_hint)."""
    try:
        await page.goto(url, timeout=20000)
        await page.wait_for_timeout(1500)
        body = await page.inner_text("body")
        salary = _extract_salary_hint(body)
        return body[:6000], salary
    except Exception:
        return "", ""


# ── LinkedIn ──────────────────────────────────────────────────────────────────

async def search_linkedin(keywords: str, location: str = "Seattle, WA",
                          limit: int = 20) -> list[dict]:
    results = []
    async with async_playwright() as p:
        browser = await _new_browser(p)
        page = await browser.new_page()
        url = (
            "https://www.linkedin.com/jobs/search/"
            f"?keywords={keywords.replace(' ', '%20')}"
            f"&location={location.replace(' ', '%20').replace(',', '%2C')}"
            "&f_TPR=r604800"  # past week
        )
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(3000)

            cards = await page.query_selector_all(".jobs-search__results-list li")
            for card in cards[:limit]:
                try:
                    title_el   = await card.query_selector("h3")
                    company_el = await card.query_selector("h4")
                    loc_el     = await card.query_selector(".job-search-card__location")
                    link_el    = await card.query_selector("a.base-card__full-link")
                    sal_el     = await card.query_selector(".job-search-card__salary-info")
                    time_el    = await card.query_selector("time")

                    title   = (await title_el.inner_text()).strip()   if title_el   else ""
                    company = (await company_el.inner_text()).strip() if company_el else ""
                    loc     = (await loc_el.inner_text()).strip()     if loc_el     else ""
                    href    = await link_el.get_attribute("href")     if link_el    else ""
                    salary  = (await sal_el.inner_text()).strip()     if sal_el     else ""
                    date_posted = ""
                    if time_el:
                        date_posted = await time_el.get_attribute("datetime") or ""
                        if not date_posted:
                            date_posted = _parse_relative_date(await time_el.inner_text())

                    if title and company:
                        results.append({
                            "title": title, "company": company, "location": loc,
                            "url": href, "source": "linkedin", "salary_text": salary,
                            "date_posted": date_posted,
                        })
                except Exception:
                    continue
        except PWTimeout:
            pass
        finally:
            await browser.close()
    return results


# ── Indeed ────────────────────────────────────────────────────────────────────

async def search_indeed(keywords: str, location: str = "Bellevue, WA",
                        limit: int = 20) -> list[dict]:
    results = []
    async with async_playwright() as p:
        browser = await _new_browser(p)
        page = await browser.new_page()
        url = (
            "https://www.indeed.com/jobs"
            f"?q={keywords.replace(' ', '+')}"
            f"&l={location.replace(' ', '+').replace(',', '%2C')}"
            "&fromage=7"
        )
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(3000)

            cards = await page.query_selector_all(".job_seen_beacon")
            for card in cards[:limit]:
                try:
                    title_el   = await card.query_selector("h2.jobTitle span")
                    company_el = await card.query_selector("[data-testid='company-name']")
                    loc_el     = await card.query_selector("[data-testid='text-location']")
                    link_el    = await card.query_selector("h2.jobTitle a")
                    sal_el     = await card.query_selector("[data-testid='attribute_snippet_testid']")
                    date_el    = await card.query_selector("[data-testid='myJobsStateDate'], .date, span.date")

                    title   = (await title_el.inner_text()).strip()   if title_el   else ""
                    company = (await company_el.inner_text()).strip() if company_el else ""
                    loc     = (await loc_el.inner_text()).strip()     if loc_el     else ""
                    href    = await link_el.get_attribute("href")     if link_el    else ""
                    salary  = (await sal_el.inner_text()).strip()     if sal_el     else ""
                    date_posted = _parse_relative_date(
                        await date_el.inner_text() if date_el else ""
                    )

                    if href and not href.startswith("http"):
                        href = "https://www.indeed.com" + href

                    if title and company:
                        results.append({
                            "title": title, "company": company, "location": loc,
                            "url": href, "source": "indeed", "salary_text": salary,
                            "date_posted": date_posted,
                        })
                except Exception:
                    continue
        except PWTimeout:
            pass
        finally:
            await browser.close()
    return results


# ── Fetch JD from individual job page ────────────────────────────────────────

async def fetch_jds(jobs: list[dict]) -> list[dict]:
    """Visit each job page to pull full JD text + salary. Mutates in place."""
    async with async_playwright() as p:
        browser = await _new_browser(p)
        page = await browser.new_page()
        for j in jobs:
            if not j.get("url"):
                continue
            jd_text, salary = await _fetch_jd(page, j["url"])
            j["jd_full"] = jd_text
            if salary and not j.get("salary_text"):
                j["salary_text"] = salary
        await browser.close()
    return jobs


# ── Generic career page ───────────────────────────────────────────────────────

async def scrape_careers_page(url: str, company: str) -> list[dict]:
    """Scrape any company careers page; returns raw job links."""
    results = []
    async with async_playwright() as p:
        browser = await _new_browser(p)
        page = await browser.new_page()
        await page.goto(url, timeout=30000)
        await page.wait_for_timeout(3000)
        links = await page.query_selector_all("a")
        seen = set()
        for link in links:
            text = (await link.inner_text()).strip()
            href = await link.get_attribute("href") or ""
            if not href.startswith("http"):
                from urllib.parse import urljoin
                href = urljoin(url, href)
            if text and href not in seen and any(
                k in href.lower() for k in ["job", "career", "position", "opening", "role"]
            ):
                seen.add(href)
                results.append({
                    "title": text, "company": company, "location": "",
                    "url": href, "source": "careers", "salary_text": "",
                })
        await browser.close()
    return results[:50]


# ── public entry point (CLI / legacy) ────────────────────────────────────────

def run_search(keywords: str, location: str = "Bellevue, WA",
               sources: list[str] | None = None) -> list[dict]:
    """Search and save new jobs to DB. Returns newly added jobs."""
    if sources is None:
        sources = ["linkedin", "indeed"]

    async def _run():
        jobs = []
        if "linkedin" in sources:
            jobs += await search_linkedin(keywords, location)
        if "indeed" in sources:
            jobs += await search_indeed(keywords, location)
        return jobs

    all_jobs = asyncio.run(_run())
    new_jobs = []
    for j in all_jobs:
        if add_job(j["title"], j["company"], j["location"], j["url"], j["source"],
                   salary_text=j.get("salary_text", "")):
            new_jobs.append(j)
    return new_jobs
