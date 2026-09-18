"""Same schema and points logic as the root db.py, but the SQLite file
is just a local cache: gdrive_sync downloads it from Google Drive before
each request and uploads it back after each request (see
sync_from_drive / sync_to_drive below, wired up in client_app.py /
machine_app.py). See gdrive_sync.py for the (deliberately dumb)
caveats.
"""
import os
import secrets
import sqlite3
import string

import gdrive_sync

DB_PATH = os.path.join(os.path.dirname(__file__), "waste.db")

CATEGORY_LABELS = {
    "food": "เศษอาหาร",
    "recycle": "รีไซเคิล",
    "general": "ทั่วไป",
}

BASE_POINTS = {
    "food": 10,
    "recycle": 15,
    "general": 5,
}

DETAIL_BONUS = 5
DETAIL_MIN_LEN = 8  # note must be at least this long to count as "detailed"

PENALTY_POINTS = 20

REWARDS_SEED = [
    ("บัตรกำนัลร้านกาแฟในตึก", "แลกได้ทันที ใช้ได้ 30 วัน", 500),
    ("ส่วนลดค่าส่วนกลาง 200 บาท", "ตัดยอดในบิลเดือนถัดไป", 1000),
    ("Grab ส่วนลดค่าส่ง 50 บาท", "ใช้ได้ภายใน 14 วัน", 300),
    ("Shopee โค้ดส่วนลด 100 บาท", "ขั้นต่ำการสั่งซื้อ 300 บาท", 700),
]


def sync_from_drive():
    gdrive_sync.download_db(DB_PATH)


def sync_to_drive():
    gdrive_sync.upload_db(DB_PATH)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            unit TEXT NOT NULL DEFAULT 'อาคาร A · ชั้น 12',
            points INTEGER NOT NULL DEFAULT 0,
            flags INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS bags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'created',
            category TEXT,
            note TEXT,
            photo_path TEXT,
            ai_result TEXT,
            ai_confidence REAL,
            staff_decision TEXT,
            points_awarded INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            cost INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS redemptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reward_id INTEGER NOT NULL,
            redeemed_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (reward_id) REFERENCES rewards(id)
        );
        """
    )

    if conn.execute("SELECT COUNT(*) FROM rewards").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO rewards (name, description, cost) VALUES (?, ?, ?)",
            REWARDS_SEED,
        )

    conn.commit()
    conn.close()


def new_bag_code():
    chars = string.ascii_uppercase + string.digits
    return "BAG-" + "".join(secrets.choice(chars) for _ in range(6))


def get_bag_with_status(status):
    """Oldest bag currently in the given status. Used by the machine
    app, which has no session and just services whatever bag is next
    in the (single-bin, one-at-a-time) queue."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM bags WHERE status = ? ORDER BY id ASC LIMIT 1", (status,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_or_create_demo_user(session_name="คุณนพัตร"):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE name = ?", (session_name,)).fetchone()
    if row is None:
        cur = conn.execute(
            "INSERT INTO users (name, points) VALUES (?, ?)", (session_name, 1240)
        )
        conn.commit()
        user_id = cur.lastrowid
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row)
