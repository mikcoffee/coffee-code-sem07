
import logging
from parsers import parse_events_from_page, parse_html
from cleaning import clean_text, parse_event_date, parse_price
from http_client import HttpClient

logger = logging.getLogger("collection")

BASE = "http://127.0.0.1:8080"

def collect(client: HttpClient) -> dict:
    """Collects all events."""
    raw_events = []
    errors = []
    try:
        response = client.fetch(f"{BASE}/eventos/")
        soup = parse_html(response)
        raw_events = parse_events_from_page(soup, f"{BASE}/eventos/")
        logger.info(f"events: {len(raw_events)} collected")
    except Exception as e:
        logger.error(f"Failed to collect events: {e}")
        errors.append("failure on events page")

    # Clean data
    clean_events = []
    for raw in raw_events:
        price, student_price = parse_price(raw["price"])
        where_location = clean_text(raw["where"])
        event = {
            "external_id": raw["external_id"],
            "title": clean_text(raw["title"]),
            "start_time": parse_event_date(raw["when"]),
            "location": where_location,
            "online": (where_location or "").lower() == "online",
            "price_cents": price,
            "student_price_cents": student_price,
            "organization": clean_text(raw["organization"]),
            "url": raw["url"],
        }
        if event["start_time"] is None:
            errors.append(f"event with unreadable date: {raw['external_id']}")
        clean_events.append(event)

    return {
        "items": clean_events,
        "errors": errors,
        "complete": len(errors) == 0
    }
