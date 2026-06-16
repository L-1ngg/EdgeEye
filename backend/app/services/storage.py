from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteStore:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        if self.database_path.parent != Path("."):
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            self._seed_devices(connection)

    def reset(self) -> None:
        if self.database_path.exists():
            self.database_path.unlink()
        self.initialize()

    def _seed_devices(self, connection: sqlite3.Connection) -> None:
        existing = connection.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
        if existing:
            return
        seed_rows = [
            (
                "device-001",
                "Line 2 insulator",
                "insulator",
                "Line 2 Area A",
                "online",
            ),
            (
                "device-002",
                "Transformer bay",
                "transformer",
                "Substation bay 1",
                "online",
            ),
            (
                "device-003",
                "Switchgear cabinet",
                "switchgear",
                "Distribution room",
                "online",
            ),
            (
                "device-004",
                "Circuit breaker",
                "circuit_breaker",
                "Feeder cabinet",
                "online",
            ),
        ]
        now = "2026-06-16T10:00:00+08:00"
        connection.executemany(
            """
            INSERT INTO devices (
                device_id, device_name, device_type, location, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [(*row, now, now) for row in seed_rows],
        )


SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    device_name TEXT NOT NULL,
    device_type TEXT NOT NULL,
    location TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inspections (
    inspection_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    operator TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    summary TEXT,
    failure_reason TEXT,
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);

CREATE TABLE IF NOT EXISTS detection_results (
    result_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL,
    inspection_id TEXT NOT NULL,
    frame_id TEXT NOT NULL,
    frame_seq INTEGER,
    timestamp TEXT NOT NULL,
    received_at TEXT NOT NULL,
    processed_at TEXT NOT NULL,
    device_id TEXT,
    is_key_frame INTEGER NOT NULL,
    upload_reason TEXT NOT NULL,
    event_key TEXT,
    sample_window_json TEXT,
    image_url TEXT NOT NULL,
    annotated_image_url TEXT,
    image_width INTEGER NOT NULL,
    image_height INTEGER NOT NULL,
    detections_json TEXT NOT NULL,
    performance_json TEXT NOT NULL,
    faults_created INTEGER NOT NULL DEFAULT 0,
    faults_updated INTEGER NOT NULL DEFAULT 0,
    alarms_created INTEGER NOT NULL DEFAULT 0,
    alarms_suppressed INTEGER NOT NULL DEFAULT 0,
    report_triggered INTEGER NOT NULL DEFAULT 0,
    warnings_json TEXT NOT NULL DEFAULT '[]',
    UNIQUE (inspection_id, frame_id),
    FOREIGN KEY (inspection_id) REFERENCES inspections(inspection_id)
);

CREATE TABLE IF NOT EXISTS faults (
    fault_id TEXT PRIMARY KEY,
    inspection_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    device_type TEXT NOT NULL,
    fault_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    risk_level TEXT NOT NULL,
    alarm_required INTEGER NOT NULL,
    alarm_level TEXT NOT NULL,
    priority TEXT NOT NULL,
    process_status TEXT NOT NULL,
    event_key TEXT NOT NULL UNIQUE,
    event_status TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    occurrence_count INTEGER NOT NULL,
    last_confidence REAL NOT NULL,
    max_confidence REAL NOT NULL,
    best_frame_id TEXT NOT NULL,
    best_image_url TEXT NOT NULL,
    best_annotated_image_url TEXT,
    location TEXT,
    created_at TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    FOREIGN KEY (inspection_id) REFERENCES inspections(inspection_id),
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);

CREATE TABLE IF NOT EXISTS alarms (
    alarm_id TEXT PRIMARY KEY,
    fault_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    alarm_level TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    message TEXT NOT NULL,
    process_status TEXT NOT NULL,
    dedup_key TEXT NOT NULL UNIQUE,
    first_triggered_at TEXT NOT NULL,
    last_triggered_at TEXT NOT NULL,
    suppressed_count INTEGER NOT NULL,
    reopen_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    FOREIGN KEY (fault_id) REFERENCES faults(fault_id),
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);

CREATE TABLE IF NOT EXISTS advice (
    advice_id TEXT PRIMARY KEY,
    fault_id TEXT NOT NULL UNIQUE,
    possible_causes_json TEXT NOT NULL,
    risk_analysis TEXT NOT NULL,
    inspection_steps_json TEXT NOT NULL,
    maintenance_suggestions_json TEXT NOT NULL,
    safety_notes_json TEXT NOT NULL,
    model_name TEXT NOT NULL,
    advice_status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (fault_id) REFERENCES faults(fault_id)
);

CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    inspection_id TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    report_status TEXT NOT NULL,
    format TEXT NOT NULL,
    url TEXT NOT NULL,
    created_at TEXT NOT NULL,
    exports_json TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    UNIQUE (inspection_id, format, version),
    FOREIGN KEY (inspection_id) REFERENCES inspections(inspection_id)
);
"""
