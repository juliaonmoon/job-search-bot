"""ATS form auto-filler using Playwright.

Supports: Greenhouse, Lever, Workday, LinkedIn Easy Apply, and any unknown
portal via generic label-based field matching.

NEVER clicks the final Submit/Apply button — always pauses for review.
"""
import asyncio
import os
import re
from playwright.async_api import async_playwright, Page

from bot.profile_data import PROFILE

P = PROFILE  # short alias


# ── Low-level helpers ─────────────────────────────────────────────────────────

async def _fill(page: Page, selector: str, value: str):
    try:
        el = await page.query_selector(selector)
        if el and value:
            await el.fill(value)
    except Exception:
        pass


async def _click(page: Page, selector: str):
    try:
        el = await page.query_selector(selector)
        if el:
            await el.click()
    except Exception:
        pass


async def _select_option(page: Page, selector: str, value: str):
    try:
        el = await page.query_selector(selector)
        if el and value:
            try:
                await el.select_option(label=value)
            except Exception:
                try:
                    await el.select_option(value=value)
                except Exception:
                    pass
    except Exception:
        pass


async def _upload(page: Page, selector: str, path: str):
    if not path or not os.path.isfile(path):
        return
    try:
        el = await page.query_selector(selector)
        if el:
            await el.set_input_files(path)
    except Exception:
        pass


# ── Generic label-based filler (works on most portals) ───────────────────────

LABEL_MAP = {
    # name
    "first name": P["first_name"],
    "first":      P["first_name"],
    "given name": P["first_name"],
    "last name":  P["last_name"],
    "last":       P["last_name"],
    "family name":P["last_name"],
    "surname":    P["last_name"],
    "full name":  P["full_name"],
    "name":       P["full_name"],
    # contact
    "email":      P["email"],
    "e-mail":     P["email"],
    "phone":      P["phone"],
    "mobile":     P["phone"],
    "telephone":  P["phone"],
    # location
    "city":       P["city"],
    "state":      P["state"],
    "zip":        P["zip"],
    "postal":     P["zip"],
    "country":    P["country"],
    "address":    P["address"],
    "location":   P["address"],
    # online
    "linkedin":   P["linkedin"],
    "website":    P["website"],
    "portfolio":  P["website"],
    # employment
    "current company":  P["current_company"],
    "current employer": P["current_company"],
    "company":          P["current_company"],
    "employer":         P["current_company"],
    "current title":    P["current_title"],
    "current position": P["current_title"],
    "job title":        P["current_title"],
    "title":            P["current_title"],
    "years of experience": P["years_experience"],
    "years experience":    P["years_experience"],
    # work auth
    "authorized to work":      P["work_auth"],
    "work authorization":      P["work_auth"],
    "legally authorized":      P["work_auth"],
    "require sponsorship":     P["sponsorship"],
    "visa sponsorship":        P["sponsorship"],
    "need sponsorship":        P["sponsorship"],
    # skills
    "skills":           P["skills"],
    "certifications":   P["certifications"],
    "certificates":     P["certifications"],
}

YES_NO_MAP = {
    "yes": ["yes", "true", "1"],
    "no":  ["no",  "false", "0"],
}


async def fill_generic(page: Page, resume_path: str, cover_letter_text: str = ""):
    """Generic label-based filler — works on most ATS portals."""
    await page.wait_for_timeout(1500)

    # Upload resume if field exists
    for sel in [
        "input[type='file'][accept*='pdf']",
        "input[type='file'][name*='resume']",
        "input[type='file'][name*='cv']",
        "input[type='file']",
    ]:
        if resume_path and os.path.isfile(resume_path):
            await _upload(page, sel, resume_path)
            await page.wait_for_timeout(2000)
            break

    # Fill text inputs by matching their label
    inputs = await page.query_selector_all("input[type='text'], input[type='email'], input[type='tel'], input[type='number'], textarea")
    for inp in inputs:
        try:
            # Try several ways to find the label
            label_text = ""

            # 1. aria-label attribute
            label_text = (await inp.get_attribute("aria-label") or "").strip()

            # 2. placeholder
            if not label_text:
                label_text = (await inp.get_attribute("placeholder") or "").strip()

            # 3. associated <label> via id
            if not label_text:
                inp_id = await inp.get_attribute("id")
                if inp_id:
                    lbl = await page.query_selector(f"label[for='{inp_id}']")
                    if lbl:
                        label_text = (await lbl.inner_text()).strip()

            # 4. parent/sibling label
            if not label_text:
                lbl = await inp.evaluate_handle(
                    "el => el.closest('label') || el.previousElementSibling"
                )
                try:
                    label_text = (await lbl.as_element().inner_text()).strip()
                except Exception:
                    pass

            if not label_text:
                continue

            lt = label_text.lower().strip("* :")
            for key, value in LABEL_MAP.items():
                if key in lt and value:
                    tag = await inp.evaluate("el => el.tagName.toLowerCase()")
                    if tag == "textarea":
                        await inp.fill(value)
                    else:
                        await inp.fill(value)
                    break

        except Exception:
            continue

    # Fill select dropdowns for yes/no questions
    selects = await page.query_selector_all("select")
    for sel_el in selects:
        try:
            sel_id = await sel_el.get_attribute("id") or ""
            sel_name = (await sel_el.get_attribute("name") or "").lower()
            lbl_text = ""
            if sel_id:
                lbl = await page.query_selector(f"label[for='{sel_id}']")
                if lbl:
                    lbl_text = (await lbl.inner_text()).lower()
            if not lbl_text:
                lbl_text = sel_name

            for key, value in LABEL_MAP.items():
                if key in lbl_text:
                    await _select_option(page, f"#{sel_id}" if sel_id else "select", value)
                    break
        except Exception:
            continue

    # Cover letter textarea
    if cover_letter_text:
        for sel in [
            "textarea[name*='cover']",
            "textarea[id*='cover']",
            "textarea[placeholder*='cover']",
            "textarea[placeholder*='letter']",
        ]:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.fill(cover_letter_text)
                    break
            except Exception:
                pass

    print("[autofill:generic] Basic fields filled. Review and complete any remaining fields, then click Submit.")


# ── Greenhouse ────────────────────────────────────────────────────────────────

async def fill_greenhouse(page: Page, resume_path: str, cover_letter_text: str = ""):
    await _upload(page, "input[type='file'][name*='resume']", resume_path)
    await _fill(page, "#first_name", P["first_name"])
    await _fill(page, "#last_name",  P["last_name"])
    await _fill(page, "#email",      P["email"])
    await _fill(page, "#phone",      P["phone"])
    await _fill(page, "input[id*='linkedin']", P["linkedin"])
    await _fill(page, "input[id*='website']",  P["website"])
    await _fill(page, "input[id*='location']", P["city"] + ", " + P["state"])

    if cover_letter_text:
        await _fill(page, "textarea[name*='cover']", cover_letter_text)

    # Work auth dropdowns
    for sel in await page.query_selector_all("select"):
        try:
            lbl_id = await sel.get_attribute("id") or ""
            lbl = await page.query_selector(f"label[for='{lbl_id}']")
            lbl_text = (await lbl.inner_text()).lower() if lbl else ""
            if "authorized" in lbl_text or "work auth" in lbl_text:
                await sel.select_option(label="Yes")
            elif "sponsor" in lbl_text:
                await sel.select_option(label="No")
        except Exception:
            pass

    print("[autofill:greenhouse] Fields filled. Review and click Submit when ready.")


# ── Lever ─────────────────────────────────────────────────────────────────────

async def fill_lever(page: Page, resume_path: str, cover_letter_text: str = ""):
    await _upload(page, "input[type='file']", resume_path)
    await _fill(page, "input[name='name']",  P["full_name"])
    await _fill(page, "input[name='email']", P["email"])
    await _fill(page, "input[name='phone']", P["phone"])
    await _fill(page, "input[name='org']",   P["current_company"])
    await _fill(page, "input[name='urls[LinkedIn]']", P["linkedin"])

    if cover_letter_text:
        await _fill(page, "textarea[name*='comments'], textarea[name*='cover']", cover_letter_text)

    print("[autofill:lever] Fields filled. Review and click Submit when ready.")


# ── Workday ───────────────────────────────────────────────────────────────────

async def fill_workday(page: Page, resume_path: str, cover_letter_text: str = ""):
    # Step 1: upload resume — Workday parses it and pre-fills most fields
    upload = await page.query_selector("input[type='file']")
    if upload and resume_path and os.path.isfile(resume_path):
        await upload.set_input_files(resume_path)
        print("[autofill:workday] Resume uploaded — waiting for parse...")
        await page.wait_for_timeout(4000)

    # Step 2: fill personal info fields that Workday may not parse
    workday_fields = [
        ("[data-automation-id='legalNameSection_firstName'] input",   P["first_name"]),
        ("[data-automation-id='legalNameSection_lastName'] input",    P["last_name"]),
        ("[data-automation-id='email-address'] input",                P["email"]),
        ("[data-automation-id='phone-device-type'] input",            P["phone"]),
        ("[data-automation-id='addressSection_city'] input",          P["city"]),
        ("[data-automation-id='country-phone-code'] input",           P["country"]),
        ("input[data-automation-id*='linkedin']",                     P["linkedin"]),
    ]
    for sel, val in workday_fields:
        await _fill(page, sel, val)

    # Step 3: work auth questions (common in Workday)
    for q in await page.query_selector_all("[data-automation-id*='questionnaire'] input, [data-automation-id*='question'] input"):
        try:
            label_el = await q.query_selector("xpath=ancestor::*[contains(@class,'question')]//*[self::label or self::span][1]")
            lbl = (await label_el.inner_text()).lower() if label_el else ""
            if "authorized" in lbl or "work auth" in lbl:
                await q.check() if "yes" in (await q.get_attribute("value") or "").lower() else None
            elif "sponsor" in lbl:
                await q.check() if "no" in (await q.get_attribute("value") or "").lower() else None
        except Exception:
            pass

    print("[autofill:workday] Fields filled. Complete any remaining steps, then click Submit.")


# ── LinkedIn Easy Apply ───────────────────────────────────────────────────────

async def fill_linkedin_easy_apply(page: Page, resume_path: str, cover_letter_text: str = ""):
    """Step through LinkedIn Easy Apply pages, filling fields. STOPS before Submit."""
    for step in range(15):
        await page.wait_for_timeout(1000)

        # Fill text inputs
        for inp in await page.query_selector_all("input[type='text'], input[type='email'], input[type='tel']"):
            try:
                label_el = await inp.query_selector("xpath=../preceding-sibling::label[1]")
                label = (await label_el.inner_text()).lower() if label_el else ""
                val = None
                if "first" in label:   val = P["first_name"]
                elif "last" in label:  val = P["last_name"]
                elif "email" in label: val = P["email"]
                elif "phone" in label: val = P["phone"]
                elif "city" in label or "location" in label: val = P["city"]
                elif "linkedin" in label: val = P["linkedin"]
                if val:
                    await inp.fill(val)
            except Exception:
                pass

        if resume_path and os.path.isfile(resume_path):
            await _upload(page, "input[type='file']", resume_path)

        if cover_letter_text:
            ta = await page.query_selector("textarea")
            if ta:
                await ta.fill(cover_letter_text)

        # Find Next/Continue — but STOP at Submit/Apply
        next_btn = await page.query_selector(
            "button[aria-label*='Continue to next step'], "
            "button[aria-label*='Next'], "
            "button[aria-label*='Continue']"
        )
        submit_btn = await page.query_selector(
            "button[aria-label*='Submit application'], "
            "button[aria-label*='Apply']"
        )

        if submit_btn:
            print(f"[autofill:linkedin] Reached Submit after {step+1} step(s). Review and click Submit yourself.")
            return

        if next_btn:
            await next_btn.click()
        else:
            break

    print("[autofill:linkedin] Easy Apply steps complete. Review and click Submit.")


# ── ATS detector ─────────────────────────────────────────────────────────────

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
    if "icims.com" in u:
        return "icims"
    if "taleo.net" in u or "oracle.com/taleo" in u:
        return "taleo"
    if "smartrecruiters.com" in u:
        return "smartrecruiters"
    return "generic"


# ── Main entry ────────────────────────────────────────────────────────────────

async def _run(job_url: str, cover_letter_text: str, resume_path: str):
    ats = detect_ats(job_url)
    print(f"\n[autofill] Detected ATS: {ats}")
    print(f"[autofill] URL: {job_url[:80]}")
    print("[autofill] Opening browser — DO NOT click Submit until you have reviewed everything.\n")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        ctx = await browser.new_context()
        page = await ctx.new_page()

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
        else:
            # Generic: covers iCIMS, Taleo, SmartRecruiters, custom portals
            await fill_generic(page, resume_path, cover_letter_text)

        print("\n[autofill] ✅ Done filling. Review the form, upload your resume PDF if needed, then click Submit.")
        print("[autofill] Close this window when finished.\n")

        # Keep browser open until user closes it (up to 30 min)
        try:
            await page.wait_for_event("close", timeout=1_800_000)
        except Exception:
            pass

        await browser.close()


def autofill(job_url: str, cover_letter_text: str = "", resume_path: str = ""):
    asyncio.run(_run(job_url, cover_letter_text, resume_path))
