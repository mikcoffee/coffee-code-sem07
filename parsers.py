from urllib.parse import urljoin
from bs4 import BeautifulSoup

BASE = "http://127.0.0.1:8080"

def get_text(tag):
    """Clean text of a tag, or None if the tag doesn't exist."""
    return tag.get_text(strip=True) if tag is not None else None

def parse_html(response):
    """Creates BeautifulSoup from a requests response."""
    return BeautifulSoup(response.content, "lxml")

def parse_job_card(card):
    """Extracts data from a job card."""
    link = card.select_one("h2.titulo a")
    return {
        "external_id": card["data-id"],
        "title": get_text(card.select_one("h2.titulo a")),
        "company": get_text(card.select_one(".empresa")),
        "location": get_text(card.select_one(".local")),
        "modality": get_text(card.select_one(".modalidade")),
        "level": get_text(card.select_one(".nivel")),
        "salary": get_text(card.select_one(".salario")),
        "published": card.select_one("time")["datetime"],
        "tags": [li.get_text(strip=True) for li in card.select("ul.tags li")],
        "url": urljoin(BASE, link["href"]) if link else None,
    }

def parse_jobs_from_page(soup, page_url):
    """Extracts all jobs from a page."""
    return [parse_job_card(c) for c in soup.select("article.vaga")]

def get_next_page(soup, current_url):
    """Finds the link to the next page."""
    link = soup.select_one("a[rel=next]")
    if link is None:
        return None
    return urljoin(current_url, link["href"])

def parse_description(soup):
    """Extracts the job description from the details page."""
    div = soup.select_one(".descricao")
    return get_text(div)

def parse_event(item, page_url):
    """Extracts data from an event card."""
    link = item.select_one("h3 a")
    return {
        "external_id": item["data-id"],
        "title": get_text(link),
        "when": get_text(item.select_one(".quando")),
        "where": get_text(item.select_one(".onde")),
        "price": get_text(item.select_one(".preco")),
        "organization": get_text(item.select_one(".organizacao")),
        "url": urljoin(page_url, link["href"]) if link else None,
    }

def parse_events_from_page(soup, page_url):
    """Extracts all events from a page."""
    return [parse_event(item, page_url) for item in soup.select("li.evento")]
