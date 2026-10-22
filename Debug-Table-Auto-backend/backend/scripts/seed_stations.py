from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

STATIONS = [
    "嘉庚体育馆站",
    "东安站",
    "美峰站",
    "洪塘头站",
    "潘涂站",
    "官浔站",
    "智谷云谷站",
    "后吴站",
    "西湖站",
    "第三医院站",
    "杜桥站",
    "祥桥站",
    "小西门站",
    "同安一中站",
    "同翔高新城站",
    "寨阳站",
    "洪塘头停车场站",
    "寨阳车辆段",
]


def seed(database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS stations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL COLLATE NOCASE UNIQUE,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
            """
        )
        for index, name in enumerate(STATIONS, start=1):
            connection.execute(
                """
                INSERT INTO stations(code, name, sort_order, is_enabled)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(name) DO UPDATE SET sort_order = excluded.sort_order,
                    is_enabled = 1,
                    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                """,
                (f"STATION_{index:03d}", name, index),
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    args = parser.parse_args()
    seed(args.database)
    print(f"seeded stations: {len(STATIONS)}")
