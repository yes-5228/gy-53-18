from contextlib import contextmanager
from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "parking.db"


@contextmanager
def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def rows_to_dicts(rows):
    return [dict(row) for row in rows]


def init_db():
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS parking_zones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                floor INTEGER NOT NULL,
                code TEXT NOT NULL UNIQUE,
                capacity INTEGER NOT NULL DEFAULT 0,
                maintenance_status TEXT NOT NULL DEFAULT 'normal',
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS spaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                zone_id INTEGER,
                area TEXT NOT NULL,
                status TEXT NOT NULL,
                plate_number TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (zone_id) REFERENCES parking_zones(id)
            );

            CREATE TABLE IF NOT EXISTS monthly_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                holder_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                plate_number TEXT NOT NULL UNIQUE,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                fee REAL NOT NULL,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS parking_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_number TEXT NOT NULL,
                space_code TEXT NOT NULL,
                entry_time TEXT NOT NULL,
                exit_time TEXT,
                duration_hours REAL,
                amount REAL,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                buyer_name TEXT NOT NULL,
                tax_number TEXT,
                email TEXT NOT NULL,
                amount REAL NOT NULL,
                issued_at TEXT NOT NULL,
                invoice_no TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL
            );
            """
        )

        existing_zones = conn.execute("SELECT COUNT(*) AS count FROM parking_zones").fetchone()["count"]
        if existing_zones == 0:
            conn.executemany(
                """
                INSERT INTO parking_zones (name, floor, code, capacity, maintenance_status, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'normal', ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
                """,
                [
                    ("A区", 1, "F1-A", 20, "一层A区-靠近电梯"),
                    ("B区", 1, "F1-B", 15, "一层B区-靠近出口"),
                    ("C区", 2, "F2-C", 25, "二层C区-普通车位"),
                    ("D区", 2, "F2-D", 30, "二层D区-大型车位"),
                ],
            )

        existing_spaces = conn.execute("SELECT COUNT(*) AS count FROM spaces").fetchone()["count"]
        if existing_spaces == 0:
            zone_a = conn.execute("SELECT id FROM parking_zones WHERE code = 'F1-A'").fetchone()["id"]
            zone_b = conn.execute("SELECT id FROM parking_zones WHERE code = 'F1-B'").fetchone()["id"]
            zone_c = conn.execute("SELECT id FROM parking_zones WHERE code = 'F2-C'").fetchone()["id"]

            conn.executemany(
                """
                INSERT INTO spaces (code, zone_id, area, status, plate_number, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
                """,
                [
                    ("A-001", zone_a, "A区", "occupied", "沪A12345"),
                    ("A-002", zone_a, "A区", "free", None),
                    ("A-003", zone_a, "A区", "reserved", None),
                    ("B-001", zone_b, "B区", "free", None),
                    ("B-002", zone_b, "B区", "occupied", "浙B88K21"),
                    ("C-001", zone_c, "C区", "maintenance", None),
                    ("C-002", zone_c, "C区", "free", None),
                    ("C-003", zone_c, "C区", "free", None),
                ],
            )
