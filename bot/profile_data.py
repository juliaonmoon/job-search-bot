"""Julia Cheng — structured profile for ATS form filling.

Single source of truth. Edit here, not in autofill.py.
"""

PROFILE = {
    # ── Personal ──────────────────────────────────────────────────────────────
    "first_name":   "Julia",
    "last_name":    "Cheng",
    "full_name":    "Julia Cheng",
    "email":        "juleselianac@gmail.com",
    "phone":        "604-230-2415",
    "city":         "Bellevue",
    "state":        "WA",
    "state_full":   "Washington",
    "zip":          "98004",
    "country":      "United States",
    "address":      "Bellevue, WA 98004",
    "linkedin":     "https://www.linkedin.com/in/juleselicheng/",
    "website":      "",

    # ── Work authorization ─────────────────────────────────────────────────────
    "work_auth":         "Yes",
    "sponsorship":       "No",

    # ── EEO ───────────────────────────────────────────────────────────────────
    "gender":            "Female",
    "ethnicity":         "Asian",
    "veteran":           "No",
    "disability":        "No",

    # ── Current role ──────────────────────────────────────────────────────────
    "current_company":   "Electronic Arts",
    "current_title":     "Technical Program Manager, PI&E",
    "years_experience":  "20",

    # ── Work history ──────────────────────────────────────────────────────────
    "work_history": [
        {
            "company":      "Electronic Arts",
            "title":        "Technical Program Manager, PI&E",
            "start_month":  "04", "start_year": "2024",
            "end_month":    "",   "end_year":   "",
            "current":      True,
            "description": (
                "Leading enterprise-scale Agentic AI program to transform cloud observability "
                "and incident response across EA Digital Platform. Delivered Cloud Tagging initiative "
                "20% ahead of schedule, 40% beyond original scope. Automated 90% of manual VoIP "
                "provisioning via Secret Management program. Maintained 99.9% service availability "
                "for global player-facing services. Led Datadog to Grafana migration end-to-end."
            ),
        },
        {
            "company":      "Electronic Arts",
            "title":        "Program Manager, DnA-QVS Analytics",
            "start_month":  "07", "start_year": "2021",
            "end_month":    "04", "end_year":   "2024",
            "current":      False,
            "description": (
                "VP-sponsored QVS Product KPIs initiative — unified metrics across 30+ teams for "
                "senior leadership. CMMI-compliant Data Maturity Framework: 16 metrics across 30 "
                "global game studios. Data governance tracking 180+ managed data sources."
            ),
        },
        {
            "company":      "TELUS Telecommunications",
            "title":        "Senior BA / Project Manager, Process Ownership",
            "start_month":  "05", "start_year": "2016",
            "end_month":    "07", "end_year":   "2021",
            "current":      False,
            "description": (
                "$1M+ annual savings from Lean Six Sigma projects. Compass reverse logistics: "
                "$1.5M Year 1 benefit. Ran 10-15 concurrent project streams across SHS, FIFA, "
                "Compass, LWC, ADT migrations."
            ),
        },
        {
            "company":      "ZE Power Group",
            "title":        "Senior Data Analyst / Project Manager",
            "start_month":  "08", "start_year": "2012",
            "end_month":    "05", "end_year":   "2016",
            "current":      False,
            "description": (
                "Energy market BI: billions of data points from 30+ sources (CME, ICE, ISOs). "
                "30% data accuracy improvement via ML automation."
            ),
        },
        {
            "company":      "Promise Technology Inc.",
            "title":        "Product Manager / Global OEM Account Manager",
            "start_month":  "03", "start_year": "2005",
            "end_month":    "04", "end_year":   "2007",
            "current":      False,
            "description": (
                "Full-lifecycle NPI for OEM storage solutions. Hardware-software liaison: "
                "RAID controllers, firmware, chip vendors, Contract Manufacturers."
            ),
        },
        {
            "company":      "Chunghwa Telecom",
            "title":        "Technical Project Manager",
            "start_month":  "01", "start_year": "2002",
            "end_month":    "03", "end_year":   "2005",
            "current":      False,
            "description": (
                "Bill merge system: Java front-end + PL/SQL back-end web application. "
                "Promoted from Java Engineer to Project Manager."
            ),
        },
    ],

    # ── Education ─────────────────────────────────────────────────────────────
    "education": [
        {
            "school":       "University of British Columbia — Sauder School of Business",
            "degree":       "Master of Business Administration",
            "degree_short": "MBA",
            "field":        "Business Administration",
            "start_year":   "2007", "end_year": "2008",
        },
        {
            "school":       "National Chengchi University",
            "degree":       "Master of Science",
            "degree_short": "M.Sc.",
            "field":        "Management Information Systems",
            "start_year":   "1999", "end_year": "2001",
        },
        {
            "school":       "National Chengchi University",
            "degree":       "Bachelor of Science",
            "degree_short": "B.Sc.",
            "field":        "Management Information Systems",
            "start_year":   "1995", "end_year": "1999",
        },
    ],

    # ── Skills & certs (for text boxes) ───────────────────────────────────────
    "skills": (
        "Technical Program Management, AWS, Azure, Cloud Infrastructure, DevSecOps, "
        "Agile, Scrum, Kanban, OKR Planning, Data Governance, Tableau, Power BI, "
        "SQL, Python, Jira, Confluence, Observability, Incident Response"
    ),
    "certifications": (
        "AWS Certified Cloud Practitioner (2026), "
        "Project Management Professional — PMP (2009), "
        "Certified Scrum Master — CSM (2024), "
        "Lean Six Sigma Green Belt (2017), "
        "ITIL Foundation (2014)"
    ),
}
