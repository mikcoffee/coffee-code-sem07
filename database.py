
import sqlite3
from pathlib import Path
from dataclasses import dataclass

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    city TEXT,
    state TEXT,
    modality TEXT,
    level TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    published TEXT,
    tags TEXT,
    url TEXT NOT NULL,
    description TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    UNIQUE(source, external_id)
);

CREATE TABLE IF NOT EXISTS events(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    start_time TEXT,
    location TEXT,
    online INTEGER,
    price_cents INTEGER,
    student_price_cents INTEGER,
    organization TEXT,
    url TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    UNIQUE(source, external_id)
);

CREATE TABLE IF NOT EXISTS executions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TEXT NOT NULL,
    end_time TEXT,
    status TEXT,
    summary TEXT
);
"""

@dataclass
class Count:
    new: int = 0
    updated: int = 0
    unchanged: int = 0
    deactivated: int = 0

def open_db(path: str):
    """Opens the database and creates tables."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn

def start_execution(conn, start_time: str) -> int:
    """Registers the start of an execution."""
    cursor = conn.execute(
        "INSERT INTO executions(start_time, status) VALUES(?, 'running')",
        (start_time,)
    )
    conn.commit()
    return cursor.lastrowid

def finish_execution(conn, execution_id: int, end_time: str, status: str, summary: str):
    """Finishes the execution record."""
    conn.execute(
        "UPDATE executions SET end_time=?, status=?, summary=? WHERE id=?",
        (end_time, status, summary, execution_id)
    )
    conn.commit()

def save_jobs(conn, items: list, now: str, source: str = "mural_tech") -> Count:
    """Saves jobs without duplication."""
    count = Count()
    for item in items:
        existing = conn.execute(
            "SELECT * FROM jobs WHERE source=? AND external_id=?",
            (source, item["external_id"]),
        ).fetchone()

        # Preserve description if it couldn't be read today
        if existing and existing["description"] and not item.get("description"):
            item["description"] = existing["description"]

        # Check if data has changed
        if existing and existing["title"] == item["title"] and \
           existing["salary_min"] == item.get("salary_min") and \
           existing["salary_max"] == item.get("salary_max") and \
           existing["description"] == item.get("description"):
            conn.execute(
                "UPDATE jobs SET last_seen=?, active=1 WHERE source=? AND external_id=?",
                (now, source, item["external_id"]),
            )
            count.unchanged += 1
            continue

        salary_min, salary_max = item.get("salary_min"), item.get("salary_max")
        tags = ",".join(item.get("tags", []))
        conn.execute(
            """INSERT INTO jobs(source, external_id, title, company, city, state,
               modality, level, salary_min, salary_max, published, tags, url,
               description, active, first_seen, last_seen)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(source, external_id) DO UPDATE SET
               title=excluded.title, company=excluded.company, city=excluded.city,
               state=excluded.state, modality=excluded.modality, level=excluded.level,
               salary_min=excluded.salary_min, salary_max=excluded.salary_max,
               published=excluded.published, tags=excluded.tags, url=excluded.url,
               description=excluded.description, active=1, last_seen=excluded.last_seen""",
            (source, item["external_id"], item["title"], item.get("company"),
             item.get("city"), item.get("state"), item.get("modality"),
             item.get("level"), salary_min, salary_max, item.get("published"),
             tags, item["url"], item.get("description"), 1, now, now),
        )
        if existing:
            count.updated += 1
        else:
            count.new += 1
    conn.commit()
    return count

def save_events(conn, items: list, now: str, source: str = "mural_tech") -> Count:
    """Saves events without duplication."""
    count = Count()
    for item in items:
        existing = conn.execute(
            "SELECT * FROM events WHERE source=? AND external_id=?",
            (source, item["external_id"]),
        ).fetchone()

        if existing and existing["title"] == item["title"] and \
           existing["start_time"] == item.get("start_time") and \
           existing["price_cents"] == item.get("price_cents"):
            conn.execute(
                "UPDATE events SET last_seen=?, active=1 WHERE source=? AND external_id=?",
                (now, source, item["external_id"]),
            )
            count.unchanged += 1
            continue

        conn.execute(
            """INSERT INTO events(source, external_id, title, start_time, location, online,
               price_cents, student_price_cents, organization, url,
               active, first_seen, last_seen)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(source, external_id) DO UPDATE SET
               title=excluded.title, start_time=excluded.start_time, location=excluded.location,
               online=excluded.online, price_cents=excluded.price_cents,
               student_price_cents=excluded.student_price_cents,
               organization=excluded.organization, url=excluded.url,
               active=1, last_seen=excluded.last_seen""",
            (source, item["external_id"], item["title"], item.get("start_time"),
             item.get("location"), 1 if item.get("online") else 0,
             item.get("price_cents"), item.get("student_price_cents"),
             item.get("organization"), item["url"], 1, now, now),
        )
        if existing:
            count.updated += 1
        else:
            count.new += 1
    conn.commit()
    return count

def deactivate_unseen(conn, table: str, source: str, now: str) -> int:
    """Marks as inactive the items that did not appear in the current collection."""
    cursor = conn.execute(
        f"UPDATE {table} SET active=0 WHERE source=? AND active=1 AND last_seen<?",
        (source, now),
    )
    conn.commit()
    return cursor.rowcount
