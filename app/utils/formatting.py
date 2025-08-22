
from datetime import datetime
import re
from typing import Optional

DATE_FMT = "%Y-%m-%d"
DATETIME_FMT = "%Y-%m-%d %H:%M"

def parse_date(s: str) -> Optional[str]:
    s = s.strip()
    # accetta YYYY-MM-DD oppure DD/MM/YYYY
    try:
        if re.match(r"\d{4}-\d{2}-\d{2}$", s):
            return datetime.strptime(s, DATE_FMT).date().isoformat()
        if re.match(r"\d{2}/\d{2}/\d{4}$", s):
            d = datetime.strptime(s, "%d/%m/%Y").date()
            return d.isoformat()
    except Exception:
        return None
    return None

def parse_datetime(s: str) -> Optional[str]:
    s = s.strip()
    # formati: YYYY-MM-DD HH:MM oppure DD/MM/YYYY HH:MM
    for fmt in (DATETIME_FMT, "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt).isoformat(timespec="minutes")
        except Exception:
            continue
    return None

def clean_plate(s: str) -> str:
    return re.sub(r"\s+", "", s.upper())

def format_vehicle(v) -> str:
    parts = [p for p in [v.get("alias"), v.get("plate"), v.get("brand"), v.get("model")] if p]
    return " · ".join(parts)
