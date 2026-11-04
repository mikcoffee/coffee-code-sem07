
import logging
from parsers import parse_jobs_from_page, get_next_page, parse_description, parse_html
from cleaning import clean_text, parse_location, parse_salary_range
from http_client import HttpClient

logger = logging.getLogger("collection")

BASE = "http://127.0.0.1:8080"
USER_AGENT = "MuralColetaBot/1.0 (study project; contact: voce@example.com)"
MAX_PAGES = 20

def collect(client: HttpClient) -> dict:
    """Collects all jobs."""
    raw_jobs = []
    visited = set()
    url = f"{BASE}/vagas/"
    errors = []
    complete = True

    while url and url not in visited and len(visited) < MAX_PAGES:
        visited.add(url)
        try:
            response = client.fetch(url)
            soup = parse_html(response)
            from_page = parse_jobs_from_page(soup, url)
            logger.info(f"page {len(visited)}: {len(from_page)} jobs")
            
            for job in from_page:
                # Try to get description
                try:
                    detail_response = client.fetch(job["url"])
                    detail_soup = parse_html(detail_response)
                    job["description"] = parse_description(detail_soup)
                except Exception as e:
                    logger.warning(f"Failed to fetch detail for {job['url']}: {e}")
                    job["description"] = None
                    errors.append(f"detail failure: {job['external_id']}")
                raw_jobs.append(job)
            
            url = get_next_page(soup, url)
        except Exception as e:
            logger.error(f"Failure on page {url}: {e}")
            errors.append(f"page failure: {url}")
            complete = False
            break

    # Clean data
    clean_jobs = []
    for raw in raw_jobs:
        city, state = parse_location(raw["location"])
        salary_min, salary_max = parse_salary_range(raw["salary"])
        job = {
            "external_id": raw["external_id"],
            "title": clean_text(raw["title"]),
            "company": clean_text(raw["company"]),
            "city": city,
            "state": state,
            "modality": clean_text(raw["modality"]),
            "level": clean_text(raw["level"]),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "published": raw["published"],
            "tags": [t.lower() for t in raw["tags"]],
            "url": raw["url"],
            "description": raw.get("description"),
        }
        clean_jobs.append(job)

    return {
        "items": clean_jobs,
        "errors": errors,
        "complete": complete
    }
