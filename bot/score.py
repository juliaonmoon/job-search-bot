"""Score and filter job listings against Julia's preferences."""
import re

MEGA_CAPS = {
    "google", "alphabet", "microsoft", "amazon", "aws", "meta", "apple", "nvidia",
    "salesforce", "adobe", "ea", "electronic arts", "netflix", "uber", "lyft",
    "airbnb", "stripe", "palantir", "servicenow", "workday", "atlassian",
    "shopify", "snowflake", "datadog", "crowdstrike", "palo alto networks",
    "intuit", "oracle", "sap", "ibm", "accenture", "expedia", "zillow",
    "tableau", "vmware", "intel", "amd", "qualcomm", "broadcom", "cisco",
    "linkedin", "snap", "pinterest", "mongodb", "elastic", "splunk",
    "twilio", "zendesk", "okta", "cloudflare", "hashicorp", "databricks",
    "confluent", "github", "figma", "notion", "slack", "zoom", "dropbox",
}

DOMAIN_KEYWORDS = [
    ("devsecops", 30), ("cloud infrastructure", 30), ("cloud infra", 30),
    ("platform engineering", 28), ("site reliability", 25), ("sre", 22),
    ("generative ai", 25), ("ai/ml", 25), ("machine learning", 25),
    ("artificial intelligence", 25), ("ai platform", 25), ("llm", 22),
    ("data platform", 22), ("data engineering", 22), ("data infrastructure", 22),
    ("data analytics", 20), ("analytics platform", 20), ("analytics", 18),
    ("network engineering", 15), ("cybersecurity", 15), ("security", 12),
]

TITLE_KEYWORDS = [
    ("staff tpm", 25), ("staff technical program", 25),
    ("principal program manager", 24), ("principal tpm", 24),
    ("senior tpm", 22), ("senior technical program manager", 22),
    ("technical program manager", 20), (" tpm", 18),
    ("staff program manager", 20), ("senior program manager", 18),
    ("program manager", 10), ("project manager", 5),
]

US_SALARY_FLOOR = 150_000
CA_SALARY_FLOOR = 130_000


def _extract_salary(text: str) -> tuple[int | None, str]:
    """Return (annual_amount, raw_string) or (-1, raw) if below floor, or (None, '') if missing."""
    text_lower = text.lower()
    is_cad = any(x in text_lower for x in [" cad", "cdn", "canadian dollar", "ca$"])

    patterns = [
        r'\$\s*(\d{1,3}),(\d{3})',                                    # $150,000
        r'\$\s*(\d{2,3})[kK]',                                        # $150k
        r'\b(\d{2,3})[kK]\s*[-–]\s*\$?\s*(\d{2,3})[kK]',            # 150k-180k
        r'(\d{1,3}),(\d{3})\s*[-–]\s*\$?\s*(\d{1,3}),(\d{3})',      # 150,000-180,000
    ]

    for i, pat in enumerate(patterns):
        m = re.search(pat, text, re.IGNORECASE)
        if not m:
            continue
        raw = m.group(0)
        g = m.groups()
        if i == 0:
            num = int(g[0]) * 1000 + int(g[1])
        elif i == 1:
            num = int(g[0]) * 1000
        elif i == 2:
            num = int(g[0]) * 1000  # lower bound of range
        else:
            num = int(g[0]) * 1000 + int(g[1])  # lower bound

        floor = CA_SALARY_FLOOR if is_cad else US_SALARY_FLOOR
        return (num if num >= floor else -1), raw

    return None, ""


def is_mega_cap(company: str) -> bool:
    cl = company.lower()
    return any(mc in cl for mc in MEGA_CAPS)


def score_job(title: str, company: str, jd_text: str, salary_text: str = "") -> tuple[int, bool]:
    """Return (score 0-100, should_skip).

    should_skip=True when salary is below floor, or absent and company isn't mega-cap.
    """
    combined = f"{title} {jd_text}".lower()
    score = 0

    # Title match (0-25)
    for kw, pts in TITLE_KEYWORDS:
        if kw in title.lower():
            score += pts
            break

    # Domain match (0-30)
    best_domain = 0
    for kw, pts in DOMAIN_KEYWORDS:
        if kw in combined:
            best_domain = max(best_domain, pts)
    score += best_domain

    # Salary / skip logic (0-20)
    sal_amount, _ = _extract_salary(salary_text or jd_text)
    if sal_amount is not None and sal_amount > 0:
        score += 20
        should_skip = False
    elif sal_amount == -1:
        should_skip = True  # has salary but below floor
    else:
        # No salary found
        if is_mega_cap(company):
            score += 10
            should_skip = False
        else:
            should_skip = True

    # Location (0-15)
    if any(loc in combined for loc in ["seattle", "bellevue", "kirkland", "redmond", "remote", "hybrid"]):
        score += 15
    elif any(x in combined for x in ["washington", "wfh", "anywhere", "distributed"]):
        score += 8

    # Mega-cap bonus (0-10)
    if is_mega_cap(company):
        score += 10

    return min(score, 100), should_skip
