import sqlite3
from pathlib import Path
from datetime import date

DB_PATH = Path(__file__).parent.parent / "jobs.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                title         TEXT NOT NULL,
                company       TEXT NOT NULL,
                location      TEXT,
                url           TEXT UNIQUE,
                source        TEXT,
                status        TEXT DEFAULT 'found',
                date_found    TEXT DEFAULT (date('now')),
                date_applied  TEXT,
                notes         TEXT,
                contact       TEXT,
                follow_up     TEXT,
                persona       TEXT,
                jd_snippet    TEXT,
                salary_text   TEXT,
                score         INTEGER DEFAULT 0,
                jd_full       TEXT,
                tailor_output TEXT,
                cover_output  TEXT,
                daily_batch   TEXT
            );
        """)
    _migrate()


def _migrate():
    """Add columns introduced after initial schema (safe to re-run)."""
    new_cols = [
        ("salary_text",   "TEXT"),
        ("score",         "INTEGER DEFAULT 0"),
        ("jd_full",       "TEXT"),
        ("tailor_output", "TEXT"),
        ("cover_output",  "TEXT"),
        ("daily_batch",   "TEXT"),
        ("date_posted",   "TEXT"),
    ]
    with get_conn() as conn:
        for col, col_type in new_cols:
            try:
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass  # column already exists


def add_job(title, company, location, url, source, jd_snippet="",
            salary_text="", score=0, jd_full="", daily_batch="", date_posted=""):
    with get_conn() as conn:
        try:
            conn.execute(
                """INSERT INTO jobs
                   (title, company, location, url, source, jd_snippet,
                    salary_text, score, jd_full, daily_batch, date_posted)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (title, company, location, url, source, jd_snippet,
                 salary_text, score, jd_full, daily_batch, date_posted),
            )
            return True
        except sqlite3.IntegrityError:
            return False  # duplicate URL


def update_status(job_id, status, notes=None, contact=None, follow_up=None):
    with get_conn() as conn:
        fields = ["status = ?"]
        vals = [status]
        if status == "applied":
            fields.append("date_applied = ?")
            vals.append(date.today().isoformat())
        if notes is not None:
            fields.append("notes = ?")
            vals.append(notes)
        if contact is not None:
            fields.append("contact = ?")
            vals.append(contact)
        if follow_up is not None:
            fields.append("follow_up = ?")
            vals.append(follow_up)
        vals.append(job_id)
        conn.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", vals)


def save_tailor(job_id, tailor_output, persona=None):
    with get_conn() as conn:
        if persona:
            conn.execute(
                "UPDATE jobs SET tailor_output=?, persona=? WHERE id=?",
                (tailor_output, persona, job_id),
            )
        else:
            conn.execute(
                "UPDATE jobs SET tailor_output=? WHERE id=?",
                (tailor_output, job_id),
            )


def save_cover(job_id, cover_output):
    with get_conn() as conn:
        conn.execute("UPDATE jobs SET cover_output=? WHERE id=?", (cover_output, job_id))


def list_jobs(status=None, limit=200):
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE status=? ORDER BY score DESC, date_found DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY score DESC, date_found DESC LIMIT ?", (limit,)
            ).fetchall()
    return [dict(r) for r in rows]


def get_job(job_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    return dict(row) if row else None


def get_stats():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status"
        ).fetchall()
    return {r["status"]: r["cnt"] for r in rows}
