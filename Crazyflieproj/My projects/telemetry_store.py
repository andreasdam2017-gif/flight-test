import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "logging.jsonl"
DB_PATH = BASE_DIR / "telemetry.db"
SCHEMA_PATH = BASE_DIR / "telemetry.sql"


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_flight_id():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"flight-{timestamp}-{uuid.uuid4().hex[:8]}"


def save_flight_log_to_db(flight_id, start_time, end_time):
    entries = []

    with open(LOG_PATH, "r", encoding="utf-8") as log_file:
        for line_number, line in enumerate(log_file, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{LOG_PATH}:{line_number} is not valid JSON") from exc

            try:
                timestamp_ms = int(entry["timestamp_ms"])
                log_name = str(entry["log"])
                data = entry["data"]
            except KeyError as exc:
                raise ValueError(f"{LOG_PATH}:{line_number} is missing {exc}") from exc

            entries.append((
                flight_id,
                timestamp_ms,
                log_name,
                json.dumps(data, separators=(",", ":")),
            ))

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        with open(SCHEMA_PATH, "r", encoding="utf-8") as schema_file:
            conn.executescript(schema_file.read())

        conn.execute(
            """
            INSERT INTO drone_flights (flight_id, start_time, end_time)
            VALUES (?, ?, ?)
            """,
            (flight_id, start_time, end_time),
        )
        conn.executemany(
            """
            INSERT INTO telemetry_entries
                (flight_id, timestamp_ms, log_name, data)
            VALUES (?, ?, ?, ?)
            """,
            entries,
        )

    return len(entries)
