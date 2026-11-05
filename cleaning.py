import re
from decimal import Decimal
from datetime import datetime

_MONEY = re.compile(r"R\$\s*([\d.,]+)")
_LONG_DATE = re.compile(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4}),\s*(\d{1,2})h(\d{2})")

MONTHS = {
    "janeiro": 1,  "fevereiro": 2,  "março": 3,  "abril": 4,
    "maio": 5,  "junho": 6,  "julho": 7,  "agosto": 8,
    "setembro": 9,  "outubro": 10,  "novembro": 11,  "dezembro": 12
}

def clean_text(text: str | None) -> str | None:
    """Removes duplicate spaces and line breaks. Empty becomes None."""
    if text is None:
        return None
    cleaned = "".join(text.split())
    return cleaned or None

def to_cents(value: str) -> int:
    """'7.000' becomes 700000 and '3.200,50' becomes 320050 (integers, no float)."""
    number = Decimal(value.replace(".", "").replace(",", "."))
    return int(number * 100)

def parse_salary_range(text: str | None) -> tuple[int | None, int | None]:
    """Returns (min, max) in cents. No value: (None, None)."""
    if not text:
        return (None, None)
    values = [to_cents(v) for v in _MONEY.findall(text)]
    if not values:
        return (None, None)
    if len(values) == 1:
        if text.strip().lower().startswith("até"):
            return (None, values[0])
        return (values[0], values[0])
    return (min(values), max(values))

def parse_location(text: str | None) -> tuple[str | None, str | None]:
    """'Curitiba, PR' becomes ('Curitiba', 'PR'). 'Remoto' becomes (None, None)."""
    text = clean_text(text)
    if not text or "," not in text:
        return (None, None)
    city, state = (part.strip() for part in text.rsplit(",", 1))
    return (city, state.upper())

def parse_event_date(text: str | None) -> str | None:
    """'sábado, 17 de outubro de 2026, 14h00' becomes '2026-10-17T14:00'."""
    match = _LONG_DATE.search(text or "")
    if not match:
        return None
    day, month, year, hour, minute = match.groups()
    month_number = MONTHS.get(month.lower())
    if month_number is None:
        return None
    try:
        moment = datetime(int(year), month_number, int(day), int(hour), int(minute))
    except ValueError:
        return None
    return moment.isoformat(timespec="minutes")

def parse_price(text: str | None) -> tuple[int | None, int | None]:
    """Returns (price, student price) in cents. 'Gratuito' is 0."""
    text = clean_text(text) or ""
    if text.lower().startswith("gratuito"):
        return (0, None)
    values = [to_cents(v) for v in _MONEY.findall(text)]
    if not values:
        return (None, None)
    return (values[0], values[1] if len(values) > 1 else None)
