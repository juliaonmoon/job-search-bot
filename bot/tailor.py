"""Gemini-powered resume/cover letter tailoring."""
import os
import google.generativeai as genai
from pathlib import Path

PROFILE_PATH = Path(__file__).parent.parent / "julia_profile.md"

PERSONA_HINTS = {
    "pgm": "General Program Manager / TPM at tech companies — lead with Agentic AI, cloud governance, OKR planning.",
    "biz": "Business Program Manager at large enterprise — emphasise cloud+AI transformation and customer success.",
    "cx": "Customer Experience / CRM Ops — lead with call-center transformation and $1M+ LSS projects.",
    "apac": "TPM + APAC / NPI — highlight CHT, Promise Tech, OEM hardware-software integration, Mandarin fluency.",
    "network": "TPM Network Engineering / DevSecOps — lead with VoIP, JWT, RDS/ElastiCache encryption, zero-downtime.",
    "usa": "US-formatted PGM (Bellevue WA address) — same as pgm but optimised for US market.",
    "bsa": "Business System Analyst — BigQuery/data engineering, Scrum Master, SQL/Python/Java focus.",
}


def _check_api_key():
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key or key.startswith("your-"):
        raise ValueError(
            "GEMINI_API_KEY not set. Add it to your .env file:\n"
            "  GEMINI_API_KEY=your-key-here\n"
            "Get a free key at https://aistudio.google.com"
        )
    return key


def _client():
    key = _check_api_key()
    genai.configure(api_key=key)
    return genai.GenerativeModel("gemini-1.5-flash")


def _profile() -> str:
    return PROFILE_PATH.read_text(encoding="utf-8")


def pick_persona(jd: str) -> str:
    """Ask Gemini to pick the best persona given a JD."""
    model = _client()
    hint_list = "\n".join(f"- {k}: {v}" for k, v in PERSONA_HINTS.items())
    prompt = (
        f"Given this job description, pick the single best resume persona key from the list below.\n"
        f"Reply with only the key (e.g. 'pgm').\n\nPersonas:\n{hint_list}\n\nJD:\n{jd[:3000]}"
    )
    response = model.generate_content(prompt)
    key = response.text.strip().lower()
    return key if key in PERSONA_HINTS else "pgm"


def tailor_resume(jd: str, persona: str | None = None) -> str:
    """Return a tailored resume bullet summary for this JD."""
    if persona is None:
        persona = pick_persona(jd)
    profile = _profile()
    model = _client()
    prompt = (
        f"You are a professional resume writer. Using Julia's career profile below, "
        f"produce a tailored resume summary + 5 bullet points optimised for this job description. "
        f"Persona to use: {persona} — {PERSONA_HINTS.get(persona, '')}.\n\n"
        f"--- PROFILE ---\n{profile}\n\n"
        f"--- JOB DESCRIPTION ---\n{jd[:4000]}\n\n"
        f"Output plain text, no markdown headers."
    )
    response = model.generate_content(prompt)
    return response.text.strip()


def write_cover_letter(jd: str, company: str, title: str, persona: str | None = None) -> str:
    """Return a tailored cover letter."""
    if persona is None:
        persona = pick_persona(jd)
    profile = _profile()
    model = _client()
    prompt = (
        f"Write a concise, confident cover letter from Julia Cheng applying for {title} at {company}. "
        f"Persona: {persona}. Match the tone of the JD. 3 paragraphs max. No filler.\n\n"
        f"--- PROFILE ---\n{profile}\n\n"
        f"--- JOB DESCRIPTION ---\n{jd[:4000]}"
    )
    response = model.generate_content(prompt)
    return response.text.strip()
