#!/usr/bin/env python3
"""Julia's Job Search Bot — CLI entry point.

Usage:
  python cli.py search "Technical Program Manager" --location "Seattle, WA"
  python cli.py list [--status found|applied|interviewing|rejected|offer]
  python cli.py status <job_id> applied --notes "Submitted via LinkedIn"
  python cli.py tailor <job_id>
  python cli.py cover <job_id>
  python cli.py apply <job_id> --resume path/to/resume.pdf
"""
import argparse
import sys
from bot.db import init_db, list_jobs, update_status, get_job
from bot.search import run_search
from bot.tailor import tailor_resume, write_cover_letter, pick_persona


# ── formatters ────────────────────────────────────────────────────────────────

STATUS_COLORS = {
    "found":        "\033[37m",   # grey
    "applied":      "\033[34m",   # blue
    "interviewing": "\033[33m",   # yellow
    "offer":        "\033[32m",   # green
    "rejected":     "\033[31m",   # red
}
RESET = "\033[0m"


def fmt_job(j: dict, verbose: bool = False) -> str:
    color = STATUS_COLORS.get(j["status"], "")
    line = f"[{j['id']:>4}] {color}{j['status']:>12}{RESET}  {j['company']:<30} {j['title']}"
    if verbose:
        line += f"\n       {j['url']}"
        if j.get("notes"):
            line += f"\n       Notes: {j['notes']}"
        if j.get("follow_up"):
            line += f"\n       Follow-up: {j['follow_up']}"
    return line


# ── commands ──────────────────────────────────────────────────────────────────

def cmd_search(args):
    print(f"Searching for '{args.keywords}' in {args.location} …")
    new_jobs = run_search(args.keywords, args.location, args.sources)
    if not new_jobs:
        print("No new jobs found (all already in DB or no results).")
    else:
        print(f"\nAdded {len(new_jobs)} new job(s):\n")
        for j in new_jobs:
            print(f"  {j['company']:<30} {j['title']}")
            print(f"  {j['url']}\n")


def cmd_list(args):
    jobs = list_jobs(status=args.status)
    if not jobs:
        print("No jobs found.")
        return
    for j in jobs:
        print(fmt_job(j, verbose=args.verbose))
    print(f"\n{len(jobs)} job(s) shown.")


def cmd_status(args):
    update_status(args.job_id, args.new_status, notes=args.notes, contact=args.contact, follow_up=args.follow_up)
    print(f"Job {args.job_id} → {args.new_status}")


def cmd_tailor(args):
    job = get_job(args.job_id)
    if not job:
        print(f"Job {args.job_id} not found.")
        sys.exit(1)
    jd = job.get("jd_snippet") or f"{job['title']} at {job['company']}"
    persona = args.persona or pick_persona(jd)
    print(f"Persona: {persona}\n")
    print(tailor_resume(jd, persona))


def cmd_cover(args):
    job = get_job(args.job_id)
    if not job:
        print(f"Job {args.job_id} not found.")
        sys.exit(1)
    jd = job.get("jd_snippet") or f"{job['title']} at {job['company']}"
    persona = args.persona or pick_persona(jd)
    print(f"Persona: {persona}\n")
    print(write_cover_letter(jd, job["company"], job["title"], persona))


def cmd_apply(args):
    from bot.autofill import autofill
    job = get_job(args.job_id)
    if not job:
        print(f"Job {args.job_id} not found.")
        sys.exit(1)

    cover = ""
    if args.cover:
        cover = write_cover_letter(
            job.get("jd_snippet") or job["title"],
            job["company"],
            job["title"],
        )
        print("--- Cover Letter ---\n")
        print(cover)
        print("\n--- Filling form ---\n")

    autofill(job["url"], args.resume, cover_letter_text=cover, headless=False)
    update_status(args.job_id, "applied")
    print(f"Marked job {args.job_id} as applied.")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    init_db()
    parser = argparse.ArgumentParser(prog="jobbot", description="Julia's Job Search Bot")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # search
    p_search = sub.add_parser("search", help="Search job boards")
    p_search.add_argument("keywords")
    p_search.add_argument("--location", default="Bellevue, WA")
    p_search.add_argument("--sources", nargs="+", choices=["linkedin", "indeed"], default=["linkedin", "indeed"])

    # list
    p_list = sub.add_parser("list", help="List tracked jobs")
    p_list.add_argument("--status", choices=["found", "applied", "interviewing", "offer", "rejected"])
    p_list.add_argument("--verbose", "-v", action="store_true")

    # status
    p_status = sub.add_parser("status", help="Update a job's status")
    p_status.add_argument("job_id", type=int)
    p_status.add_argument("new_status", choices=["found", "applied", "interviewing", "offer", "rejected", "skipped"])
    p_status.add_argument("--notes")
    p_status.add_argument("--contact")
    p_status.add_argument("--follow-up")

    # tailor
    p_tailor = sub.add_parser("tailor", help="Generate tailored resume bullets for a job")
    p_tailor.add_argument("job_id", type=int)
    p_tailor.add_argument("--persona", choices=["pgm", "biz", "cx", "apac", "network", "usa", "bsa"])

    # cover
    p_cover = sub.add_parser("cover", help="Generate cover letter for a job")
    p_cover.add_argument("job_id", type=int)
    p_cover.add_argument("--persona", choices=["pgm", "biz", "cx", "apac", "network", "usa", "bsa"])

    # apply
    p_apply = sub.add_parser("apply", help="Auto-fill ATS form for a job")
    p_apply.add_argument("job_id", type=int)
    p_apply.add_argument("--resume", required=True, help="Path to resume PDF")
    p_apply.add_argument("--cover", action="store_true", help="Auto-generate and fill cover letter")

    args = parser.parse_args()
    dispatch = {"search": cmd_search, "list": cmd_list, "status": cmd_status,
                "tailor": cmd_tailor, "cover": cmd_cover, "apply": cmd_apply}
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
