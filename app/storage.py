
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

def _connect(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    with closing(conn.cursor()) as cur:
        cur.execute("PRAGMA foreign_keys = ON;")
    return conn

SCHEMA = [
    '''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER UNIQUE NOT NULL,
        created_at TEXT NOT NULL
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        alias TEXT,
        plate TEXT,
        brand TEXT,
        model TEXT,
        year INTEGER,
        notes TEXT,
        km_current INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS maintenance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER NOT NULL,
        date TEXT NOT NULL, -- ISO YYYY-MM-DD
        km INTEGER,
        type TEXT NOT NULL,
        notes TEXT,
        cost REAL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER NOT NULL,
        kind TEXT NOT NULL, -- 'time' | 'km'
        due_at TEXT,        -- ISO datetime per kind='time'
        km_threshold INTEGER, -- per kind='km'
        description TEXT,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
    );
    '''
]

def init_db(db_path: str):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(db_path)
    with closing(conn):
        cur = conn.cursor()
        for stmt in SCHEMA:
            cur.execute(stmt)
        conn.commit()

def ensure_user(conn, chat_id: int) -> int:
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    if row:
        return row["id"]
    now = datetime.utcnow().isoformat()
    cur.execute("INSERT INTO users (chat_id, created_at) VALUES (?,?)", (chat_id, now))
    conn.commit()
    return cur.lastrowid

# Vehicles
def add_vehicle(db_path: str, chat_id: int, alias: str, plate: str, brand: str, model: str, year: Optional[int], notes: Optional[str]) -> int:
    conn = _connect(db_path)
    with closing(conn):
        user_id = ensure_user(conn, chat_id)
        now = datetime.utcnow().isoformat()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO vehicles (user_id, alias, plate, brand, model, year, notes, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (user_id, alias, plate, brand, model, year, notes, now)
        )
        conn.commit()
        return cur.lastrowid

def list_vehicles(db_path: str, chat_id: int) -> List[sqlite3.Row]:
    conn = _connect(db_path)
    with closing(conn):
        user_id = ensure_user(conn, chat_id)
        cur = conn.cursor()
        cur.execute("SELECT * FROM vehicles WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        return cur.fetchall()

def get_vehicle(db_path: str, vehicle_id: int) -> Optional[sqlite3.Row]:
    conn = _connect(db_path)
    with closing(conn):
        cur = conn.cursor()
        cur.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,))
        return cur.fetchone()

def update_vehicle_km(db_path: str, vehicle_id: int, km: int):
    conn = _connect(db_path)
    with closing(conn):
        cur = conn.cursor()
        cur.execute("UPDATE vehicles SET km_current = ? WHERE id = ?", (km, vehicle_id))
        conn.commit()

def delete_vehicle(db_path: str, vehicle_id: int):
    conn = _connect(db_path)
    with closing(conn):
        cur = conn.cursor()
        cur.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
        conn.commit()

# Maintenance
def add_maintenance(db_path: str, vehicle_id: int, date_iso: str, km: Optional[int], mtype: str, notes: Optional[str], cost: Optional[float]) -> int:
    conn = _connect(db_path)
    with closing(conn):
        now = datetime.utcnow().isoformat()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO maintenance (vehicle_id, date, km, type, notes, cost, created_at) VALUES (?,?,?,?,?,?,?)",
            (vehicle_id, date_iso, km, mtype, notes, cost, now)
        )
        conn.commit()
        return cur.lastrowid

def list_maintenance(db_path: str, vehicle_id: int, limit: int = 50) -> List[sqlite3.Row]:
    conn = _connect(db_path)
    with closing(conn):
        cur = conn.cursor()
        cur.execute("SELECT * FROM maintenance WHERE vehicle_id = ? ORDER BY date DESC, id DESC LIMIT ?", (vehicle_id, limit))
        return cur.fetchall()

# Reminders
def add_time_reminder(db_path: str, vehicle_id: int, due_at_iso: str, description: str) -> int:
    conn = _connect(db_path)
    with closing(conn):
        now = datetime.utcnow().isoformat()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO reminders (vehicle_id, kind, due_at, description, active, created_at) VALUES (?,?,?,?,1,?)",
            (vehicle_id, 'time', due_at_iso, description, now)
        )
        conn.commit()
        return cur.lastrowid

def add_km_reminder(db_path: str, vehicle_id: int, km_threshold: int, description: str) -> int:
    conn = _connect(db_path)
    with closing(conn):
        now = datetime.utcnow().isoformat()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO reminders (vehicle_id, kind, km_threshold, description, active, created_at) VALUES (?,?,?,?,1,?)",
            (vehicle_id, 'km', km_threshold, description, now)
        )
        conn.commit()
        return cur.lastrowid

def list_active_time_reminders(db_path: str) -> List[sqlite3.Row]:
    conn = _connect(db_path)
    with closing(conn):
        cur = conn.cursor()
        cur.execute("SELECT r.*, v.user_id, v.alias FROM reminders r JOIN vehicles v ON v.id = r.vehicle_id WHERE r.kind = 'time' AND r.active = 1")
        return cur.fetchall()

def list_active_km_reminders(db_path: str) -> List[sqlite3.Row]:
    conn = _connect(db_path)
    with closing(conn):
        cur = conn.cursor()
        cur.execute("SELECT r.*, v.user_id, v.alias, v.km_current FROM reminders r JOIN vehicles v ON v.id = r.vehicle_id WHERE r.kind = 'km' AND r.active = 1")
        return cur.fetchall()

def deactivate_reminder(db_path: str, reminder_id: int):
    conn = _connect(db_path)
    with closing(conn):
        cur = conn.cursor()
        cur.execute("UPDATE reminders SET active = 0 WHERE id = ?", (reminder_id,))
        conn.commit()

# Exports
def fetch_user_export(db_path: str, chat_id: int) -> Dict[str, Any]:
    conn = _connect(db_path)
    with closing(conn):
        user_id = ensure_user(conn, chat_id)
        cur = conn.cursor()
        cur.execute("SELECT * FROM vehicles WHERE user_id = ?", (user_id,))
        vehicles = [dict(row) for row in cur.fetchall()]
        cur.execute("SELECT m.*, v.alias FROM maintenance m JOIN vehicles v ON v.id = m.vehicle_id WHERE v.user_id = ? ORDER BY date", (user_id,))
        maint = [dict(row) for row in cur.fetchall()]
        cur.execute("SELECT r.*, v.alias FROM reminders r JOIN vehicles v ON v.id = r.vehicle_id WHERE v.user_id = ?", (user_id,))
        rems = [dict(row) for row in cur.fetchall()]
        return {"vehicles": vehicles, "maintenance": maint, "reminders": rems}
