# Collection Project - Mural Tech
Automated collection pipeline for jobs and events from the Mural Tech training site.

## Installation
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage
Start the training site (in one terminal):
```bash
cd site-treino
python3 servidor.py
```

Run the collection (in another terminal):
```bash
python3 main.py
```

## Structure
- `main.py` - Main orchestrator
- `collect_jobs.py` - Jobs collector
- `collect_events.py` - Events collector
- `parsers.py` - HTML parsing functions
- `cleaning.py` - Data cleaning functions
- `database.py` - SQLite operations
- `http_client.py` - HTTP client with retry and robots.txt

## Features
- Respects robots.txt and Crawl-delay
- Automatic retry on 503/429 errors
- Storage in SQLite without duplication
- Change detection (new, updated, deactivated)
- Rotating logs
- Exit codes (0=ok, 1=partial, 2=failure)

## Tested on
- Linux
- Python 3.12.3
- requests 2.34.2
- beautifulsoup4 4.15.0
- lxml 6.1.3

## Tests
sqlite3 data/jobs.db
### View tables
.tables

### View schema
.schema

### Count jobs
SELECT count(*) FROM jobs;

### View first 5 jobs
SELECT external_id, title, company, salary_min, salary_max FROM jobs LIMIT 5;

### View events
SELECT external_id, title, start_time FROM events LIMIT 5;

### View execution history
SELECT * FROM executions;

### Count records
SELECT count(*) FROM jobs;

SELECT count(*) FROM events;

### View execution history
SELECT status, summary FROM executions;

### Salary v002
SELECT external_id, salary_min, salary_max FROM jobs WHERE external_id = 'v002';

### Location v001
SELECT external_id, city, state FROM jobs WHERE external_id = 'v001';

### Event e004
SELECT external_id, start_time, online, price_cents, student_price_cents 
FROM events 
WHERE external_id = 'e004';

### Salary v003
SELECT external_id, salary_min, salary_max FROM jobs WHERE external_id = 'v003';

### Status v015
SELECT external_id, active FROM jobs WHERE external_id = 'v015';

## Scheduling
- Execution script: `scheduling/execute_pipeline.sh`
- Cron expression tested with croniter: `0 7 * * *` (every day at 7 AM)
