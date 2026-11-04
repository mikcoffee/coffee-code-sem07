import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
from http_client import HttpClient
import database
import collect_jobs
import collect_events

BASE = "http://127.0.0.1:8080"
USER_AGENT = "MuralColetaBot/1.0 (study project; contact: voce@example.com)"
DB_PATH = "data/jobs.db"
LOG_PATH = "logs"

SUCCESS = 0
PARTIAL = 1
FAILURE = 2

def setup_logging():
    """Sets up logging to file and console."""
    Path(LOG_PATH).mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s")
    root = logging.getLogger("collection")
    root.handlers.clear()
    root.setLevel(logging.INFO)
    
    file_handler = RotatingFileHandler(
        Path(LOG_PATH) / "collection.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    console_handler = logging.StreamHandler()
    
    for handler in (file_handler, console_handler):
        handler.setFormatter(fmt)
        root.addHandler(handler)

def main() -> int:
    """Main function."""
    setup_logging()
    logger = logging.getLogger("collection")
    start_time = datetime.now().isoformat()

    conn = database.open_db(DB_PATH)
    execution_id = database.start_execution(conn, start_time)
    client = HttpClient(BASE, USER_AGENT)
    client.load_robots()
    
    summaries = []
    total_errors = 0
    status = "ok"

    try:
        # Collect jobs
        logger.info("Starting jobs collection...")
        jobs_result = collect_jobs.collect(client)
        with conn:
            jobs_count = database.save_jobs(conn, jobs_result["items"], start_time)
            if jobs_result["complete"]:
                jobs_count.deactivated = database.deactivate_unseen(
                    conn, "jobs", "mural_tech", start_time
                )
        
        total_errors += len(jobs_result["errors"])
        jobs_summary = (f"jobs: {jobs_count.new} new, "
                        f"{jobs_count.updated} updated, "
                        f"{jobs_count.unchanged} unchanged, "
                        f"{jobs_count.deactivated} deactivated")
        summaries.append(jobs_summary)
        logger.info(jobs_summary)
        for error in jobs_result["errors"]:
            logger.warning(f"jobs: {error}")

        # Collect events
        logger.info("Starting events collection...")
        events_result = collect_events.collect(client)
        with conn:
            events_count = database.save_events(conn, events_result["items"], start_time)
            if events_result["complete"]:
                events_count.deactivated = database.deactivate_unseen(
                    conn, "events", "mural_tech", start_time
                )
        
        total_errors += len(events_result["errors"])
        events_summary = (f"events: {events_count.new} new, "
                          f"{events_count.updated} updated, "
                          f"{events_count.unchanged} unchanged, "
                          f"{events_count.deactivated} deactivated")
        summaries.append(events_summary)
        logger.info(events_summary)
        for error in events_result["errors"]:
            logger.warning(f"events: {error}")

        if total_errors:
            status = "partial"
    except Exception as e:
        logger.exception("Unexpected error")
        status = "failure"
        summaries.append(f"error: {e}")

    end_time = datetime.now().isoformat()
    database.finish_execution(conn, execution_id, end_time, status, " | ".join(summaries))
    conn.close()
    
    logger.info(f"Execution {execution_id} finished: {status}")
    return {"ok": SUCCESS, "partial": PARTIAL, "failure": FAILURE}[status]

if __name__ == "__main__":
    sys.exit(main())
