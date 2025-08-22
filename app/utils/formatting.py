from __future__ import annotations
from datetime import datetime, date, timedelta
import re
from typing import Optional, Tuple

# Formati canonici
DATE_FMT = "%Y-%m-%d"
DATETIME_FMT = "%Y-%m-%d %H:%M"

# ----------------------------
# PARSING DATE "UMANO"
# ----------------------------

def _try_parse_with_formats(s: str, fmts: Tuple[str, ...]) -> Optional[datetime]:
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None

def parse_date(s: str) -> Optional[str]:
    """
    Converte input "umani" in ISO YYYY-MM-DD.
    Supporta:
    - 'YYYY-MM-DD' (anche con - o /)
    - 'DD/MM/YYYY', 'D/M/YYYY', 'DD-MM-YYYY'
    - 'DD/MM/YY', 'D/M/YY' (anno 20xx)
    - parole: 'oggi', 'domani', 'ieri'
    """
    if not s:
        return None
    raw = s.strip().lower()

    # parole chiave
    today = date.today()
    if raw in ("oggi",):
        return today.isoformat()
    if raw in ("domani",):
        return (today + timedelta(days=1)).isoformat()
    if raw in ("ieri",):
        return (today - timedelta(days=1)).isoformat()

    # normalizza separatori multipli
    raw_norm = re.sub(r"[.\s]", "/", raw)  # 22.08 -> 22/08
    raw_norm = raw_norm.replace("-", "/")  # 2025-08-22 -> 2025/08/22

    # YYYY/MM/DD
    dt = _try_parse_with_formats(raw_norm, ("%Y/%m/%d",))
    if dt:
        return dt.date().isoformat()

    # DD/MM/YYYY o D/M/YYYY
    dt = _try_parse_with_formats(raw_norm, ("%d/%m/%Y", "%-d/%-m/%Y" if "/" in raw_norm else "%d/%m/%Y"))
    if dt:
        return dt.date().isoformat()

    # DD/MM/YY → 20YY
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2})", raw_norm)
    if m:
        dd, mm, yy = map(int, m.groups())
        yy += 2000
        try:
            return date(yy, mm, dd).isoformat()
        except Exception:
            return None

    return None

def _parse_time_only(s: str) -> Optional[Tuple[int, int]]:
    """
    Estrae un orario HH:MM da stringhe tipo:
    '14:30', '14.30', 'h14', 'h 14:05', 'ore 9', 'alle 18:05'
    Ritorna (hh, mm)
    """
    raw = s.strip().lower()
    raw = raw.replace(".", ":")
    raw = re.sub(r"\s+", " ", raw)

    # pattern vari
    patterns = [
        r"^(\d{1,2}):(\d{2})$",
        r"^h\s*(\d{1,2})(?::(\d{2}))?$",
        r"^(?:ore|alle)\s+(\d{1,2})(?::(\d{2}))?$",
        r"^(\d{1,2})$",
    ]
    for p in patterns:
        m = re.match(p, raw)
        if m:
            hh = int(m.group(1))
            mm = int(m.group(2)) if m.lastindex and m.lastindex >= 2 and m.group(2) else 0
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                return hh, mm
    return None

def parse_datetime(s: str) -> Optional[str]:
    """
    Converte input in ISO 'YYYY-MM-DD HH:MM'.
    Supporta:
    - 'YYYY-MM-DD HH:MM' (o con '/')
    - 'DD/MM/YYYY HH:MM'
    - 'DD/MM HH:MM' (assume anno corrente)
    - solo orario ('14:00', 'h14', 'ore 9') → assume oggi
    - 'oggi/domani/ieri' + 'alle HH:MM' o solo parola (allora 09:00)
    - '22/08 ore 9', '22/8 9', '2025-08-22 9'
    """
    if not s:
        return None
    raw = s.strip().lower()
    today = date.today()

    # parole + orario
    for key, d in (("oggi", today), ("domani", today + timedelta(days=1)), ("ieri", today - timedelta(days=1))):
        if raw.startswith(key):
            rest = raw[len(key):].strip()
            t = _parse_time_only(rest) if rest else (9, 0)  # default 09:00
            if not t:
                return None
            hh, mm = t
            return datetime(d.year, d.month, d.day, hh, mm).strftime(DATETIME_FMT)

    # se è solo orario → oggi
    t_only = _parse_time_only(raw)
    if t_only:
        hh, mm = t_only
        return datetime(today.year, today.month, today.day, hh, mm).strftime(DATETIME_FMT)

    # normalizza separatori
    raw_norm = re.sub(r"[.\s]", " ", raw)     # 22.08 9 -> "22 08 9"
    raw_norm = raw_norm.replace("/", "-")     # 22/08 -> 22-08
    raw_norm = re.sub(r"\s+ore\s+", " ", raw_norm)
    raw_norm = re.sub(r"\s+alle\s+", " ", raw_norm)

    # tentativi diretti completi
    dt = _try_parse_with_formats(raw_norm, ("%Y-%m-%d %H:%M", "%Y-%m-%d %H",))
    if dt:
        return dt.strftime(DATETIME_FMT)

    # 'DD-MM-YYYY HH:MM' o 'DD-MM-YYYY H'
    dt = _try_parse_with_formats(raw_norm, ("%d-%m-%Y %H:%M", "%d-%m-%Y %H",))
    if dt:
        return dt.strftime(DATETIME_FMT)

    # 'DD-MM HH:MM' (anno corrente) o 'DD-MM H'
    m = re.match(r"^(\d{1,2})-(\d{1,2})\s+(\d{1,2})(?::(\d{2}))?$", raw_norm)
    if m:
        dd, mm, hh = int(m.group(1)), int(m.group(2)), int(m.group(3))
        mins = int(m.group(4)) if m.group(4) else 0
        try:
            return datetime(today.year, mm, dd, hh, mins).strftime(DATETIME_FMT)
        except Exception:
            return None

    # 'DD/MM/YYYY HH:MM' varianti originali (con slash)
    raw_slash = raw.replace(".", "/")
    dt = _try_parse_with_formats(raw_slash, ("%d/%m/%Y %H:%M", "%d/%m/%Y %H",))
    if dt:
        return dt.strftime(DATETIME_FMT)

    # 'DD/MM HH:MM' (assume anno corrente)
    m = re.match(r"^(\d{1,2})/(\d{1,2})\s+(\d{1,2})(?::(\d{2}))?$", raw_slash)
    if m:
        dd, mm, hh = int(m.group(1)), int(m.group(2)), int(m.group(3))
        mins = int(m.group(4)) if m.group(4) else 0
        try:
            return datetime(today.year, mm, dd, hh, mins).strftime(DATETIME_FMT)
        except Exception:
            return None

    # fallback: se è solo una data, prova a parsarla e usa 09:00
    d_iso = parse_date(s)
    if d_iso:
        return f"{d_iso} 09:00"

    return None

# ----------------------------
# SANITIZZAZIONI & FORMATTERS
# ----------------------------

def clean_plate(s: str) -> str:
    """Normalizza targa: rimuove spazi/simboli, lascia solo alfanumerico maiuscolo."""
    return re.sub(r"[^A-Z0-9]", "", s.upper())

def parse_km(s: str) -> Optional[int]:
    """Converte '123 456', '123.456', '123,456' in int chilometri."""
    if not s:
        return None
    raw = s.strip().replace(" ", "").replace(".", "").replace(",", "")
    return int(raw) if raw.isdigit() else None

def parse_euro(s: str) -> Optional[float]:
    """Converte '89,90' o '89.90' in float (euro)."""
    if not s:
        return None
    raw = s.strip().replace("€", "").replace(" ", "").replace(",", ".")
    try:
        return float(raw)
    except Exception:
        return None

def format_euro(x: Optional[float]) -> str:
    return f"€{x:.2f}" if isinstance(x, (float, int)) else "-"

def format_vehicle(v) -> str:
    parts = [p for p in [v.get("alias"), v.get("plate"), v.get("brand"), v.get("model")] if p]
    return " · ".join(parts)

def human_date(d_iso: str) -> str:
    """'2025-08-22' -> '22/08/2025'"""
    try:
        d = datetime.strptime(d_iso, DATE_FMT).date()
        return d.strftime("%d/%m/%Y")
    except Exception:
        return d_iso

def human_datetime(dt_iso: str) -> str:
    """'2025-08-22 09:00' -> '22/08/2025 09:00'"""
    try:
        dt = datetime.strptime(dt_iso, DATETIME_FMT)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return dt_iso
