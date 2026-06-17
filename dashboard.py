#!/usr/bin/env python3
"""Job Search Dashboard — Flask web UI.

Run:  python dashboard.py
Open: http://localhost:5056
"""
import subprocess
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify, render_template, request

sys.path.insert(0, str(Path(__file__).parent))
from bot.db import (
    get_job, get_stats, init_db, list_jobs, save_cover, save_tailor, update_status,
)
from bot.tailor import pick_persona, tailor_resume, write_cover_letter

app = Flask(__name__)

DEFAULT_RESUME = r"C:\Users\jules\job-search-bot\resume.pdf"

_search_running = False
_search_log: list[str] = []
_search_lock = threading.Lock()


# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/jobs")
def api_jobs():
    status = request.args.get("status") or None
    return jsonify(list_jobs(status=status))


@app.route("/api/stats")
def api_stats():
    stats = get_stats()
    stats["total"] = sum(stats.values())
    return jsonify(stats)


@app.route("/api/search", methods=["POST"])
def api_search():
    global _search_running, _search_log
    with _search_lock:
        if _search_running:
            return jsonify({"ok": False, "msg": "Search already running"})
        _search_running = True
        _search_log = []

    def _run():
        global _search_running
        import builtins
        original_print = builtins.print

        def _capture(*args, **kwargs):
            msg = " ".join(str(a) for a in args)
            with _search_lock:
                _search_log.append(msg)
            original_print(*args, **kwargs)

        builtins.print = _capture
        try:
            import importlib
            import daily_run
            importlib.reload(daily_run)  # pick up today's date
            daily_run.run()
        except Exception as e:
            with _search_lock:
                _search_log.append(f"ERROR: {e}")
        finally:
            builtins.print = original_print
            _search_running = False

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "msg": "Search started"})


@app.route("/api/search_status")
def api_search_status():
    with _search_lock:
        return jsonify({"running": _search_running, "log": list(_search_log[-30:])})


@app.route("/api/tailor/<int:job_id>", methods=["POST"])
def api_tailor(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"ok": False, "msg": "Job not found"}), 404
    # Return cached output if available
    if job.get("tailor_output"):
        return jsonify({"ok": True, "persona": job.get("persona", "—"), "text": job["tailor_output"], "cached": True})
    jd = job.get("jd_full") or job.get("jd_snippet") or f"{job['title']} at {job['company']}"
    persona = pick_persona(jd)
    text = tailor_resume(jd, persona)
    save_tailor(job_id, text, persona)
    return jsonify({"ok": True, "persona": persona, "text": text})


@app.route("/api/cover/<int:job_id>", methods=["POST"])
def api_cover(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"ok": False, "msg": "Job not found"}), 404
    if job.get("cover_output"):
        return jsonify({"ok": True, "persona": job.get("persona", "—"), "text": job["cover_output"], "cached": True})
    jd = job.get("jd_full") or job.get("jd_snippet") or f"{job['title']} at {job['company']}"
    persona = pick_persona(jd)
    text = write_cover_letter(jd, job["company"], job["title"], persona)
    save_cover(job_id, text)
    return jsonify({"ok": True, "persona": persona, "text": text})


@app.route("/api/apply/<int:job_id>", methods=["POST"])
def api_apply(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"ok": False, "msg": "Job not found"}), 404

    data = request.get_json() or {}
    resume_path = data.get("resume_path") or DEFAULT_RESUME
    cover = job.get("cover_output") or ""

    script = (
        f"import sys; sys.path.insert(0, r'{Path(__file__).parent}')\n"
        f"from bot.autofill import autofill\n"
        f"autofill({repr(job['url'])}, {repr(resume_path)}, {repr(cover)}, headless=False)\n"
    )
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
    subprocess.Popen([sys.executable, "-c", script], **kwargs)

    update_status(job_id, "applied")
    return jsonify({"ok": True, "msg": "Browser opened — review the form and click Submit when ready."})


@app.route("/api/status/<int:job_id>", methods=["POST"])
def api_status(job_id):
    data = request.get_json() or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"ok": False, "msg": "status required"}), 400
    update_status(job_id, new_status, notes=data.get("notes"))
    return jsonify({"ok": True})


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("Job Search Dashboard → http://localhost:5056")
    app.run(host="0.0.0.0", port=5056, debug=False)
