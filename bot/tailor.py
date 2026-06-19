"""Claude-powered resume/cover letter tailoring."""
import os
import anthropic
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


def _profile() -> str:
    return PROFILE_PATH.read_text(encoding="utf-8")


def _check_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key or key.startswith("sk-ant-..."):
        raise ValueError(
            "ANTHROPIC_API_KEY not set. Add it to your .env file:\n"
            "  ANTHROPIC_API_KEY=sk-ant-your-key-here\n"
            "Get a key at https://console.anthropic.com"
        )


def pick_persona(jd: str) -> str:
    """Ask Claude to pick the best persona given a JD."""
    _check_api_key()
    client = anthropic.Anthropic()
    hint_list = "\n".join(f"- {k}: {v}" for k, v in PERSONA_HINTS.items())
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": (
                f"Given this job description, pick the single best resume persona key from the list below.\n"
                f"Reply with only the key (e.g. 'pgm').\n\nPersonas:\n{hint_list}\n\nJD:\n{jd[:3000]}"
            ),
        }],
    )
    key = msg.content[0].text.strip().lower()
    return key if key in PERSONA_HINTS else "pgm"


def tailor_resume(jd: str, persona: str | None = None) -> str:
    """Return a tailored resume bullet summary for this JD."""
    if persona is None:
        persona = pick_persona(jd)
    profile = _profile()
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": (
                f"You are a professional resume writer. Using Julia's career profile below, "
                f"produce a tailored resume summary + 5 bullet points optimised for this job description. "
                f"Persona to use: {persona} — {PERSONA_HINTS.get(persona, '')}.\n\n"
                f"--- PROFILE ---\n{profile}\n\n"
                f"--- JOB DESCRIPTION ---\n{jd[:4000]}\n\n"
                f"Output plain text, no markdown headers."
            ),
        }],
    )
    return msg.content[0].text.strip()


def write_cover_letter(jd: str, company: str, title: str, persona: str | None = None) -> str:
    """Return a tailored cover letter."""
    if persona is None:
        persona = pick_persona(jd)
    profile = _profile()
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        messages=[{
            "role": "user",
            "content": (
                f"Write a concise, confident cover letter from Julia Cheng applying for {title} at {company}. "
                f"Persona: {persona}. Match the tone of the JD. 3 paragraphs max. No filler.\n\n"
                f"--- PROFILE ---\n{profile}\n\n"
                f"--- JOB DESCRIPTION ---\n{jd[:4000]}"
            ),
        }],
    )
    return msg.content[0].text.strip()
