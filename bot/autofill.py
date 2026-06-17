"""ATS form auto-filler using Playwright.

Supported: Greenhouse, Lever, Workday, LinkedIn Easy Apply.
"""
import asyncio
from playwright.async_api import async_playwright


DEFAULTS = {
    "first_name":          "Julia",
    "last_name":           "Cheng",
    "email":               "juleselianac@gmail.com",
    "phone":               "(604) 230-2415",
    "location":            "Bellevue, WA",
    "linkedin":            "https://www.linkedin.com/in/juleselicheng/",
    "work_auth":           "Yes",
    "require_sponsorship": "No",
    "gender":              "Female",
    "ethnicity":           "Asian",
    "veteran":             "No",
    "disability":          "No",
}


# ── field helpers ─────────────────────────────────────────────────────────────

async def _fill(page, selector: str, value: str):
    el = await page.query_selector(selector)
    if el:
        await el.fill(value)


async def _select(page, selector: str, value: str):
    el = await page.query_selector(selector)
    if el:
        try:
            await el.select_option(label=value)
        except Exception:
            await el.select_option(value=value)


# ── Greenhouse ────────────────────────────────────────────────────────────────

async def fill_greenhouse(page, resume_path: str, cover_letter_text: str = ""):
    await _fill(page, "#first_name", DEFAULTS["first_name"])
    await _fill(page, "#last_name", DEFAULTS["last_name"])
    await _fill(page, "#email", DEFAULTS["email"])
    await _fill(page, "#phone", DEFAULTS["phone"])

    upload = await page.query_selector("input[type='file'][name*='resume']")
    if upload:
        await upload.set_input_files(resume_path)

    if cover_letter_text:
        cl_box = await page.query_selector("textarea[name*='cover']")
        if cl_box:
            await cl_box.fill(cover_letter_text)

    li = await page.query_selector("input[id*='linkedin']")
    if li:
        await li.fill(DEFAULTS["linkedin"])


# ── Lever ─────────────────────────────────────────────────────────────────────

async def fill_lever(page, resume_path: str, cover_letter_text: str = ""):
    await _fill(page, "input[name='name']", f"{DEFAULTS['first_name']} {DEFAULTS['last_name']}")
    await _fill(page, "input[name='email']", DEFAULTS["email"])
    await _fill(page, "input[name='phone']", DEFAULTS["phone"])
    await _fill(page, "input[name='org']", "Electronic Arts")

    upload = await page.query_selector("input[type='file']")
    if upload:
        await upload.set_input_files(resume_path)

    if cover_letter_text:
        cl = await page.query_selector("textarea[name*='comments'], textarea[name*='cover']")
        if cl:
            await cl.fill(cover_letter_text)


# ── Workday ───────────────────────────────────────────────────────────────────

async def fill_workday(page, resume_path: str, cover_letter_text: str = ""):
    upload = await page.query_selector("input[type='file']")
    if upload:
        await upload.set_input_files(resume_path)
        await page.wait_for_timeout(3000)

    for sel, val in [
        ("[data-automation-id='legalNameSection_firstName'] input", DEFAULTS["first_name"]),
        ("[data-automation-id='legalNameSection_lastName'] input",  DEFAULTS["last_name"]),
        ("[data-automation-id='email-address'] input",              DEFAULTS["email"]),
        ("[data-automation-id='phone-device-type'] input",          DEFAULTS["phone"]),
    ]:
        await _fill(page, sel, val)


# ── LinkedIn Easy Apply ───────────────────────────────────────────────────────

async def fill_linkedin_easy_apply(page, resume_path: str, cover_letter_text: str = ""):
    for _ in range(10):
        await page.wait_for_timeout(1000)

        for inp in await page.query_selector_all("input[type='text'], input[type='email'], input[type='tel']"):
            label_el = await inp.query_selector("xpath=../preceding-sibling::label[1]")
            label = (await label_el.inner_text()).lower() if label_el else ""
            if "first" in label:
                await inp.fill(DEFAULTS["first_name"])
            elif "last" in label:
                await inp.fill(DEFAULTS["last_name"])
            elif "email" in label:
                await inp.fill(DEFAULTS["email"])
            elif "phone" in label:
                await inp.fill(DEFAULTS["phone"])
            elif "city" in label or "location" in label:
                await inp.fill(DEFAULTS["location"])

        upload = await page.query_selector("input[type='file']")
        if upload:
            await upload.set_input_files(resume_path)

        if cover_letter_text:
            ta = await page.query_selector("textarea")
            if ta:
                await ta.fill(cover_letter_text)

        next_btn = await page.query_selector(
            "button[aria-label*='Continue'], button[aria-label*='Submit'], button[aria-label*='Next']"
        )
        if not next_btn:
            break
        label = (await next_btn.get_attribute("aria-label") or "").lower()
        await next_btn.click()
        if "submit" in label:
            break


# ── dispatcher ────────────────────────────────────────────────────────────────

def detect_ats(url: str) -> str:
    u = url.lower()
    if "greenhouse.io" in u or "boards.greenhouse" in u:
        return "greenhouse"
    if "lever.co" in u or "jobs.lever.co" in u:
        return "lever"
    if "myworkdayjobs.com" in u or "workday.com" in u:
        return "workday"
    if "linkedin.com" in u:
        return "linkedin"
    return "unknown"


async def _autofill(job_url: str, resume_path: str, cover_letter_text: str, headless: bool):
    ats = detect_ats(job_url)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        await page.goto(job_url, timeout=30000)
        await page.wait_for_timeout(2000)

        if ats == "greenhouse":
            await fill_greenhouse(page, resume_path, cover_letter_text)
        elif ats == "lever":
            await fill_lever(page, resume_path, cover_letter_text)
        elif ats == "workday":
            await fill_workday(page, resume_path, cover_letter_text)
        elif ats == "linkedin":
            btn = await page.query_selector("button.jobs-apply-button")
            if btn:
                await btn.click()
                await page.wait_for_timeout(1500)
            await fill_linkedin_easy_apply(page, resume_path, cover_letter_text)

        print(f"[autofill] ATS={ats} — form filled. Review in browser and click Submit.")

        if not headless:
            # Wait until user closes the browser tab/window (up to 10 minutes)
            try:
                await page.wait_for_event("close", timeout=600_000)
            except Exception:
                pass

        await browser.close()


def autofill(job_url: str, resume_path: str, cover_letter_text: str = "", headless: bool = False):
    asyncio.run(_autofill(job_url, resume_path, cover_letter_text, headless))
