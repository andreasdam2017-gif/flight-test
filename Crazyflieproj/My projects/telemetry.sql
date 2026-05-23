CREATE TABLE IF NOT EXISTS drone_flights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_id TEXT UNIQUE NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS telemetry_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_id TEXT NOT NULL,
    timestamp_ms INTEGER NOT NULL,
    log_name TEXT NOT NULL,
    data TEXT NOT NULL CHECK (json_valid(data)),
    FOREIGN KEY (flight_id) REFERENCES drone_flights(flight_id)
);

CREATE INDEX IF NOT EXISTS idx_telemetry_entries_flight_id
ON telemetry_entries(flight_id);

CREATE INDEX IF NOT EXISTS idx_telemetry_entries_log_name
ON telemetry_entries(log_name);
