"""Standalone ATS autofill runner — launched via os.startfile() from dashboard.

Usage: python bot/autofill_runner.py <job_id>

Reads job from store, fills the ATS form in a visible browser,
then keeps the browser open for the user to review and submit.
"""
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from bot.store import get_job
from bot.autofill import autofill

RESUME_PATH = r"C:\Users\jules\job-search-bot\resume.pdf"


def main():
    if len(sys.argv) < 2:
        print("Usage: python bot/autofill_runner.py <job_id>")
        sys.exit(1)

    job_id = int(sys.argv[1])
    job = get_job(job_id)
    if not job:
        print(f"Job {job_id} not found in store.")
        input("Press Enter to close...")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  ATS Autofill — {job['title']} @ {job['company']}")
    print(f"{'='*60}")
    print(f"  URL: {job['url'][:80]}")
    print(f"{'='*60}\n")

    cover_letter = job.get("cover_output") or ""

    autofill(
        job_url=job["url"],
        cover_letter_text=cover_letter,
        resume_path=RESUME_PATH,
    )

    input("\nPress Enter to close this window...")


if __name__ == "__main__":
    main()
