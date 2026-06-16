"""Job board scrapers using Playwright."""
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from bot.db import add_job


# ── helpers ──────────────────────────────────────────────────────────────────

async def _new_browser(p):
    return await p.chromium.launch(headless=True)


# ── LinkedIn ──────────────────────────────────────────────────────────────────

async def search_linkedin(keywords: str, location: str = "Seattle, WA", limit: int = 25) -> list[dict]:
    results = []
    async with async_playwright() as p:
        browser = await _new_browser(p)
        page = await browser.new_page()
        url = (
            "https://www.linkedin.com/jobs/search/"
            f"?keywords={keywords.replace(' ', '%20')}"
            f"&location={location.replace(' ', '%20').replace(',', '%2C')}"
            f"&f_TPR=r604800"  # past week
        )
        await page.goto(url, timeout=30000)
        await page.wait_for_timeout(3000)

        cards = await page.query_selector_all(".jobs-search__results-list li")
        for card in cards[:limit]:
            try:
                title_el = await card.query_selector("h3")
                company_el = await card.query_selector("h4")
                loc_el = await card.query_selector(".job-search-card__location")
                link_el = await card.query_selector("a.base-card__full-link")

                title = (await title_el.inner_text()).strip() if title_el else ""
                company = (await company_el.inner_text()).strip() if company_el else ""
                loc = (await loc_el.inner_text()).strip() if loc_el else ""
                href = await link_el.get_attribute("href") if link_el else ""

                if title and company:
                    results.append({"title": title, "company": company, "location": loc, "url": href, "source": "linkedin"})
            except Exception:
                continue

        await browser.close()
    return results


# ── Indeed ────────────────────────────────────────────────────────────────────

async def search_indeed(keywords: str, location: str = "Bellevue, WA", limit: int = 25) -> list[dict]:
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
        await page.goto(url, timeout=30000)
        await page.wait_for_timeout(3000)

        cards = await page.query_selector_all(".job_seen_beacon")
        for card in cards[:limit]:
            try:
                title_el = await card.query_selector("h2.jobTitle span")
                company_el = await card.query_selector("[data-testid='company-name']")
                loc_el = await card.query_selector("[data-testid='text-location']")
                link_el = await card.query_selector("h2.jobTitle a")

                title = (await title_el.inner_text()).strip() if title_el else ""
                company = (await company_el.inner_text()).strip() if company_el else ""
                loc = (await loc_el.inner_text()).strip() if loc_el else ""
                href = await link_el.get_attribute("href") if link_el else ""
                if href and not href.startswith("http"):
                    href = "https://www.indeed.com" + href

                if title and company:
                    results.append({"title": title, "company": company, "location": loc, "url": href, "source": "indeed"})
            except Exception:
                continue

        await browser.close()
    return results


# ── Generic career page ───────────────────────────────────────────────────────

async def scrape_careers_page(url: str, company: str) -> list[dict]:
    """Scrape any company careers page and return raw job links."""
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
            if text and href not in seen and any(k in href.lower() for k in ["job", "career", "position", "opening", "role"]):
                seen.add(href)
                results.append({"title": text, "company": company, "location": "", "url": href, "source": "careers"})

        await browser.close()
    return results[:50]


# ── public entry point ────────────────────────────────────────────────────────

def run_search(keywords: str, location: str = "Bellevue, WA", sources: list[str] | None = None) -> list[dict]:
    """Run searches and save new jobs to DB. Returns list of newly added jobs."""
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
        if add_job(j["title"], j["company"], j["location"], j["url"], j["source"]):
            new_jobs.append(j)
    return new_jobs
