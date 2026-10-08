"""SQLite schema and read access for reusable test rules."""

from __future__ import annotations

import sqlite3
from uuid import uuid4
from contextlib import closing
from pathlib import Path
from typing import Any

from app.exceptions import BusinessError
from app.schemas.catalog import (
    DisciplineItem,
    DisciplineListItem,
    DisciplineWriteRequest,
    EquipmentStatusWriteRequest,
    EquipmentHierarchyItem,
    EquipmentSubtypeWriteRequest,
    EquipmentSubtypeItem,
    EquipmentTypeItem,
    EquipmentTypeSummary,
    EquipmentTypeWriteRequest,
    OperationStepItem,
    ResultOutputItem,
    StationListItem,
    StationWriteRequest,
    TestContentItem,
    TestContentWriteRequest,
)

SCHEMA_VERSION = 7

_BUILTIN_PARENT_STATUSES: dict[str, list[str]] = {
    "排烟机": ["运行状态", "手自动切换状态", "开启控制命令"],
    "加压送风机": ["运行状态", "手自动切换状态", "开启控制命令"],
}

_BUILTIN_SUBTYPE_STATUSES: dict[tuple[str, str], list[str]] = {
    ("防火阀", "电动防火阀"): ["动作状态", "关控制命令"],
    ("监视模块", "吸气式主机"): ["预警", "火警", "故障", "远程复位"],
    ("控制模块", "吸气式主机"): ["预警", "火警", "故障", "远程复位"],
    ("监视模块", "感温电缆"): ["报警反馈", "故障反馈", "远程复位"],
    ("控制模块", "感温电缆"): ["报警反馈", "故障反馈", "远程复位"],
    ("监视模块", "感温光纤"): ["感温光纤综合故障", "区间上行感温光纤报警反馈", "区间下行感温光纤报警反馈"],
    ("监视模块", "AFC"): ["AFC切非反馈", "AFC切非", "AFC状态反馈", "AFC释放控制"],
    ("控制模块", "AFC"): ["AFC切非反馈", "AFC切非", "AFC状态反馈", "AFC释放控制"],
    ("监视模块", "EPS"): ["状态反馈", "启动控制"],
    ("控制模块", "EPS"): ["状态反馈", "启动控制"],
    ("监视模块", "垂直电梯"): ["垂直电梯状态反馈", "垂直电梯归首控制"],
    ("控制模块", "垂直电梯"): ["垂直电梯状态反馈", "垂直电梯归首控制"],
    ("监视模块", "防火卷帘"): ["防火卷帘一次降落反馈", "防火卷帘一次降落控制", "防火卷帘二次降落反馈", "防火卷帘二次降落控制"],
    ("控制模块", "防火卷帘"): ["防火卷帘一次降落反馈", "防火卷帘一次降落控制", "防火卷帘二次降落反馈", "防火卷帘二次降落控制"],
    ("监视模块", "400V切非"): ["切非反馈"],
    ("控制模块", "400V切非"): ["切非"],
    ("监视模块", "消防泵"): ["消防泵手/自动反馈", "消防泵动作反馈", "消防泵故障反馈", "压力开关动作反馈", "流量开关动作反馈", "高水位报警反馈", "低水位报警反馈", "最低水位报警反馈", "稳压泵动作反馈", "稳压泵故障反馈", "消防泵启动控制", "巡检柜报警反馈", "信号阀动作反馈", "水流指示器动作反馈"],
    ("控制模块", "消防泵"): ["消防泵手/自动反馈", "消防泵动作反馈", "消防泵故障反馈", "压力开关动作反馈", "流量开关动作反馈", "高水位报警反馈", "低水位报警反馈", "最低水位报警反馈", "稳压泵动作反馈", "稳压泵故障反馈", "消防泵启动控制", "巡检柜报警反馈", "信号阀动作反馈", "水流指示器动作反馈"],
    ("监视模块", "门禁释放"): ["门禁释放反馈", "门禁释放"],
    ("控制模块", "门禁释放"): ["门禁释放反馈", "门禁释放"],
    ("监视模块", "电气火灾、消防电源、应急疏散"): ["电气火灾监控报警", "电气火灾监控故障反馈", "消防电源监控系统报警", "消防电源监控系统故障反馈", "应急照明及疏散指示系统状态反馈", "应急照明及疏散指示系统模式控制"],
    ("控制模块", "电气火灾、消防电源、应急疏散"): ["电气火灾监控报警", "电气火灾监控故障反馈", "消防电源监控系统报警", "消防电源监控系统故障反馈", "应急照明及疏散指示系统状态反馈", "应急照明及疏散指示系统模式控制"],
    ("控制模块", "主机手自动、人工确认"): ["FAS主机人工确定按钮", "FAS主机自动状态按钮", "气灭主机自动状态按钮", "FAS主机综合火警"],
}

_SCHEMA_V1_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS equipment_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL COLLATE NOCASE UNIQUE,
        name TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        sort_order INTEGER NOT NULL DEFAULT 0,
        is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS test_contents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL COLLATE NOCASE UNIQUE,
        equipment_type_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
        sort_order INTEGER NOT NULL DEFAULT 0,
        is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        FOREIGN KEY (equipment_type_id) REFERENCES equipment_types(id) ON DELETE RESTRICT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS operation_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_content_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        ratio_change TEXT NOT NULL CHECK (ratio_change IN ('是', '否')),
        sort_order INTEGER NOT NULL,
        is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        FOREIGN KEY (test_content_id) REFERENCES test_contents(id) ON DELETE RESTRICT,
        UNIQUE (test_content_id, sort_order)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS result_outputs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operation_step_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        sort_order INTEGER NOT NULL,
        is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        FOREIGN KEY (operation_step_id) REFERENCES operation_steps(id) ON DELETE RESTRICT,
        UNIQUE (operation_step_id, sort_order)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS disciplines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL COLLATE NOCASE UNIQUE,
        name TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        sort_order INTEGER NOT NULL DEFAULT 0,
        is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS result_output_disciplines (
        result_output_id INTEGER NOT NULL,
        discipline_id INTEGER NOT NULL,
        sort_order INTEGER NOT NULL,
        PRIMARY KEY (result_output_id, discipline_id),
        FOREIGN KEY (result_output_id) REFERENCES result_outputs(id) ON DELETE CASCADE,
        FOREIGN KEY (discipline_id) REFERENCES disciplines(id) ON DELETE CASCADE,
        UNIQUE (result_output_id, sort_order)
    )
    """,
    (
        "CREATE INDEX IF NOT EXISTS ix_test_contents_equipment_type "
        "ON test_contents(equipment_type_id)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS ix_operation_steps_test_content "
        "ON operation_steps(test_content_id)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS ix_result_outputs_operation_step "
        "ON result_outputs(operation_step_id)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS ix_result_output_disciplines_discipline "
        "ON result_output_disciplines(discipline_id)"
    ),
)

_SCHEMA_V2_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS generation_runs (
        id TEXT PRIMARY KEY,
        integration_code TEXT NOT NULL DEFAULT 'T19',
        request_id TEXT NOT NULL,
        generated_at TEXT NOT NULL,
        filename TEXT NOT NULL,
        output_sha256 TEXT NOT NULL CHECK (length(output_sha256) = 64),
        location_type TEXT NOT NULL,
        direction TEXT NOT NULL,
        start_station TEXT NOT NULL,
        end_station TEXT NOT NULL,
        test_content_count INTEGER NOT NULL CHECK (test_content_count >= 0),
        operation_step_count INTEGER NOT NULL CHECK (operation_step_count >= 0),
        result_output_count INTEGER NOT NULL CHECK (result_output_count >= 0),
        discipline_count INTEGER NOT NULL CHECK (discipline_count >= 0),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS generation_test_contents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        generation_id TEXT NOT NULL,
        sequence_index INTEGER NOT NULL CHECK (sequence_index > 0),
        sort_index INTEGER NOT NULL CHECK (sort_index > 0),
        generated_content TEXT NOT NULL,
        equipment_code TEXT NOT NULL,
        equipment_type TEXT NOT NULL,
        excel_row_number INTEGER NOT NULL CHECK (excel_row_number > 0),
        FOREIGN KEY (generation_id) REFERENCES generation_runs(id) ON DELETE CASCADE,
        UNIQUE (generation_id, sequence_index),
        UNIQUE (generation_id, sort_index),
        UNIQUE (generation_id, excel_row_number)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS generation_operation_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        generation_test_content_id INTEGER NOT NULL,
        sequence_index INTEGER NOT NULL CHECK (sequence_index > 0),
        description TEXT NOT NULL,
        ratio_change TEXT NOT NULL CHECK (ratio_change IN ('是', '否')),
        excel_row_number INTEGER NOT NULL CHECK (excel_row_number > 0),
        FOREIGN KEY (generation_test_content_id)
            REFERENCES generation_test_contents(id) ON DELETE CASCADE,
        UNIQUE (generation_test_content_id, sequence_index)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS generation_result_outputs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        generation_operation_step_id INTEGER NOT NULL,
        sequence_index INTEGER NOT NULL CHECK (sequence_index > 0),
        description TEXT NOT NULL,
        excel_row_number INTEGER NOT NULL CHECK (excel_row_number > 0),
        FOREIGN KEY (generation_operation_step_id)
            REFERENCES generation_operation_steps(id) ON DELETE CASCADE,
        UNIQUE (generation_operation_step_id, sequence_index)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS generation_result_disciplines (
        generation_result_output_id INTEGER NOT NULL,
        sequence_index INTEGER NOT NULL CHECK (sequence_index > 0),
        discipline_name TEXT NOT NULL,
        PRIMARY KEY (generation_result_output_id, sequence_index),
        FOREIGN KEY (generation_result_output_id)
            REFERENCES generation_result_outputs(id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_generation_runs_generated_at ON generation_runs(generated_at)",
    (
        "CREATE INDEX IF NOT EXISTS ix_generation_test_contents_generation "
        "ON generation_test_contents(generation_id)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS ix_generation_steps_content "
        "ON generation_operation_steps(generation_test_content_id)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS ix_generation_results_step "
        "ON generation_result_outputs(generation_operation_step_id)"
    ),
)

_SCHEMA_V3_STATEMENTS = (
    "ALTER TABLE test_contents ADD COLUMN equipment_subtype TEXT NOT NULL DEFAULT ''",
)

_SCHEMA_V4_STATEMENTS = (
    "ALTER TABLE test_contents ADD COLUMN equipment_status TEXT NOT NULL DEFAULT ''",
    """
    CREATE TABLE IF NOT EXISTS equipment_type_statuses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipment_type_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        sort_order INTEGER NOT NULL DEFAULT 0,
        is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
        FOREIGN KEY (equipment_type_id) REFERENCES equipment_types(id) ON DELETE RESTRICT,
        UNIQUE (equipment_type_id, name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS equipment_subtype_statuses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipment_subtype_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        sort_order INTEGER NOT NULL DEFAULT 0,
        is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
        FOREIGN KEY (equipment_subtype_id) REFERENCES equipment_type_subtypes(id) ON DELETE RESTRICT,
        UNIQUE (equipment_subtype_id, name)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_test_contents_selector ON test_contents(equipment_type_id, equipment_subtype, equipment_status)",
)

_SCHEMA_V5_STATEMENTS = (
    "ALTER TABLE generation_runs ADD COLUMN output_blob BLOB",
)

_SCHEMA_V6_STATEMENTS = (
    "ALTER TABLE generation_runs ADD COLUMN integration_code TEXT NOT NULL DEFAULT 'T19'",
    "CREATE INDEX IF NOT EXISTS ix_generation_runs_integration_code ON generation_runs(integration_code)",
)

_SCHEMA_V7_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS auth_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL COLLATE NOCASE UNIQUE,
        password_hash TEXT NOT NULL,
        display_name TEXT NOT NULL,
        is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
        last_login_at TEXT,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_sessions (
        token_hash TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at TEXT NOT NULL,
        revoked_at TEXT,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_auth_sessions_user_id ON auth_sessions(user_id)",
    "CREATE INDEX IF NOT EXISTS ix_auth_sessions_expires_at ON auth_sessions(expires_at)",
)


def _seed_builtin_statuses(connection: sqlite3.Connection) -> None:
    """Add the built-in status choices without replacing custom catalog data."""
    equipment_tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN "
            "('equipment_types', 'equipment_type_subtypes', "
            "'equipment_type_statuses', 'equipment_subtype_statuses')"
        ).fetchall()
    }
    if equipment_tables != {
        "equipment_types",
        "equipment_type_subtypes",
        "equipment_type_statuses",
        "equipment_subtype_statuses",
    }:
        return
    seeded = connection.execute(
        "SELECT 1 FROM builtin_catalog_seed_markers WHERE name = 'statuses-v1'"
    ).fetchone()
    if seeded is not None:
        return
    for parent_name, status_names in _BUILTIN_PARENT_STATUSES.items():
        parent = connection.execute(
            "SELECT id FROM equipment_types WHERE name = ? COLLATE NOCASE LIMIT 1",
            (parent_name,),
        ).fetchone()
        if parent is None:
            continue
        for sort_order, status_name in enumerate(status_names, start=1):
            connection.execute(
                """
                INSERT OR IGNORE INTO equipment_type_statuses(
                    equipment_type_id, name, sort_order, is_enabled
                ) VALUES (?, ?, ?, 1)
                """,
                (int(parent["id"]), status_name, sort_order),
            )

    for (parent_name, subtype_name), status_names in _BUILTIN_SUBTYPE_STATUSES.items():
        subtype = connection.execute(
            """
            SELECT ets.id
            FROM equipment_type_subtypes AS ets
            JOIN equipment_types AS et ON et.id = ets.parent_equipment_type_id
            WHERE et.name = ? COLLATE NOCASE AND ets.name = ? COLLATE NOCASE
            LIMIT 1
            """,
            (parent_name, subtype_name),
        ).fetchone()
        if subtype is None:
            continue
        for sort_order, status_name in enumerate(status_names, start=1):
            connection.execute(
                """
                INSERT OR IGNORE INTO equipment_subtype_statuses(
                    equipment_subtype_id, name, sort_order, is_enabled
                ) VALUES (?, ?, ?, 1)
                """,
                (int(subtype["id"]), status_name, sort_order),
            )
    connection.execute(
        "INSERT OR IGNORE INTO builtin_catalog_seed_markers(name) VALUES ('statuses-v1')"
    )

# Kept as a separate idempotent statement so existing v2 databases gain the
# hierarchy table without changing the public schema version or legacy tables.
_SCHEMA_HIERARCHY_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS equipment_type_subtypes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_equipment_type_id INTEGER NOT NULL,
        code TEXT NOT NULL COLLATE NOCASE,
        name TEXT NOT NULL,
        sort_order INTEGER NOT NULL DEFAULT 0,
        is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        FOREIGN KEY (parent_equipment_type_id) REFERENCES equipment_types(id) ON DELETE RESTRICT,
        UNIQUE (parent_equipment_type_id, code),
        UNIQUE (parent_equipment_type_id, name)
    )
    """,
    (
        "CREATE INDEX IF NOT EXISTS ix_equipment_type_subtypes_parent "
        "ON equipment_type_subtypes(parent_equipment_type_id)"
    ),
    """
    CREATE TABLE IF NOT EXISTS test_content_selectors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_content_id INTEGER NOT NULL,
        equipment_type TEXT NOT NULL DEFAULT '',
        equipment_subtype TEXT NOT NULL DEFAULT '',
        FOREIGN KEY (test_content_id) REFERENCES test_contents(id) ON DELETE CASCADE,
        UNIQUE (test_content_id, equipment_type, equipment_subtype)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_test_content_selectors_lookup ON test_content_selectors(equipment_type, equipment_subtype)",
    """
    CREATE TABLE IF NOT EXISTS builtin_catalog_seed_markers (
        name TEXT PRIMARY KEY,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    )
    """,
)

_SCHEMA_STATION_STATEMENTS = (
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
    """,
    "CREATE INDEX IF NOT EXISTS ix_stations_sort_order ON stations(sort_order, id)",
)


class CatalogRepository:
    """Create and read the catalog without owning business-data writes."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def ensure_schema(self) -> None:
        """Apply the known schema exactly once, safely across concurrent starts."""
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT (
                        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    )
                )
                """
            )
            row = connection.execute(
                "SELECT MAX(version) AS version FROM schema_migrations"
            ).fetchone()
            current_version = int(row["version"] or 0)
            if current_version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"Database schema version {current_version} is newer than supported "
                    f"version {SCHEMA_VERSION}"
                )
            if current_version < 1:
                for statement in _SCHEMA_V1_STATEMENTS:
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations(version) VALUES (1)"
                )
                current_version = 1
            if current_version < 2:
                for statement in _SCHEMA_V2_STATEMENTS:
                    connection.execute(statement)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (2)")
                current_version = 2
            for statement in _SCHEMA_HIERARCHY_STATEMENTS:
                connection.execute(statement)
            for statement in _SCHEMA_STATION_STATEMENTS:
                connection.execute(statement)
            if current_version < 3:
                table_exists = connection.execute(
                    """
                    SELECT 1 FROM sqlite_master
                    WHERE type = 'table' AND name = 'test_contents'
                    """
                ).fetchone()
                if table_exists:
                    for statement in _SCHEMA_V3_STATEMENTS:
                        connection.execute(statement)
                    connection.execute(
                        """
                        UPDATE test_contents
                        SET equipment_subtype = COALESCE(
                            (
                                SELECT s.equipment_subtype
                                FROM test_content_selectors AS s
                                WHERE s.test_content_id = test_contents.id
                                  AND s.equipment_subtype <> ''
                                ORDER BY s.id
                                LIMIT 1
                            ),
                            ''
                        )
                        WHERE equipment_subtype = ''
                        """
                    )
                connection.execute("INSERT INTO schema_migrations(version) VALUES (3)")
                current_version = 3
            if current_version < 4:
                table_exists = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'test_contents'"
                ).fetchone()
                if table_exists:
                    test_content_columns = {
                        row[1]
                        for row in connection.execute(
                            "PRAGMA table_info(test_contents)"
                        ).fetchall()
                    }
                    if "equipment_status" not in test_content_columns:
                        connection.execute(_SCHEMA_V4_STATEMENTS[0])
                for statement in _SCHEMA_V4_STATEMENTS[1:]:
                    if "ON test_contents(" in statement and not table_exists:
                        continue
                    connection.execute(statement)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (4)")
                current_version = 4
            if current_version < 5:
                table_exists = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'generation_runs'"
                ).fetchone()
                if table_exists:
                    generation_columns = {
                        row[1]
                        for row in connection.execute(
                            "PRAGMA table_info(generation_runs)"
                        ).fetchall()
                    }
                    if "output_blob" not in generation_columns:
                        connection.execute(_SCHEMA_V5_STATEMENTS[0])
                connection.execute("INSERT INTO schema_migrations(version) VALUES (5)")
                current_version = 5
            if current_version < 6:
                table_exists = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'generation_runs'"
                ).fetchone()
                if table_exists:
                    generation_columns = {
                        row[1]
                        for row in connection.execute(
                            "PRAGMA table_info(generation_runs)"
                        ).fetchall()
                    }
                    if "integration_code" not in generation_columns:
                        connection.execute(_SCHEMA_V6_STATEMENTS[0])
                    connection.execute(_SCHEMA_V6_STATEMENTS[1])
                connection.execute("INSERT INTO schema_migrations(version) VALUES (6)")
                current_version = 6
            if current_version < 7:
                for statement in _SCHEMA_V7_STATEMENTS:
                    connection.execute(statement)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (7)")
                current_version = 7
            selector_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(test_content_selectors)"
                ).fetchall()
            }
            if selector_columns and "equipment_type" not in selector_columns:
                connection.execute(
                    "ALTER TABLE test_content_selectors ADD COLUMN equipment_type TEXT NOT NULL DEFAULT ''"
                )
                selector_columns.add("equipment_type")
            if selector_columns and "equipment_status" in selector_columns:
                connection.execute("DROP INDEX IF EXISTS ix_test_content_selectors_lookup")
                connection.execute(
                    """
                    CREATE TABLE test_content_selectors_without_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        test_content_id INTEGER NOT NULL,
                        equipment_type TEXT NOT NULL DEFAULT '',
                        equipment_subtype TEXT NOT NULL DEFAULT '',
                        FOREIGN KEY (test_content_id) REFERENCES test_contents(id) ON DELETE CASCADE,
                        UNIQUE (test_content_id, equipment_type, equipment_subtype)
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO test_content_selectors_without_status(
                        id, test_content_id, equipment_type, equipment_subtype
                    )
                    SELECT id, test_content_id, equipment_type, equipment_subtype
                    FROM test_content_selectors
                    """
                )
                connection.execute("DROP TABLE test_content_selectors")
                connection.execute(
                    "ALTER TABLE test_content_selectors_without_status RENAME TO test_content_selectors"
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS ix_test_content_selectors_lookup ON test_content_selectors(equipment_type, equipment_subtype)"
                )
            _seed_builtin_statuses(connection)

    def list_equipment_types(self, *, include_disabled: bool = False) -> list[EquipmentTypeItem]:
        self.ensure_schema()
        where_clause = "" if include_disabled else "WHERE is_enabled = 1"
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                f"""
                SELECT id, code, name, description, sort_order, is_enabled
                FROM equipment_types
                {where_clause}
                ORDER BY sort_order, id
                """
            ).fetchall()
        return [
            EquipmentTypeItem(
                id=int(row["id"]),
                code=str(row["code"]),
                name=str(row["name"]),
                description=str(row["description"]),
                sortOrder=int(row["sort_order"]),
                isEnabled=bool(row["is_enabled"]),
            )
            for row in rows
        ]

    def list_equipment_subtypes(
        self, parent_equipment_type_id: int, *, include_disabled: bool = False
    ) -> list[EquipmentSubtypeItem]:
        self.ensure_schema()
        where_enabled = "" if include_disabled else "AND is_enabled = 1"
        with closing(self._connect()) as connection, connection:
            parent = connection.execute(
                "SELECT id, is_enabled FROM equipment_types WHERE id = ?",
                (parent_equipment_type_id,),
            ).fetchone()
            if parent is None or (not include_disabled and not bool(parent["is_enabled"])):
                raise BusinessError(
                    "设备类型不存在",
                    "CATALOG_EQUIPMENT_TYPE_NOT_FOUND",
                    path=["equipmentTypeId"],
                    status_code=404,
                )
            rows = connection.execute(
                f"""
                SELECT id, parent_equipment_type_id, code, name, sort_order, is_enabled
                FROM equipment_type_subtypes AS ets
                WHERE ets.parent_equipment_type_id = ? {where_enabled}
                ORDER BY ets.sort_order, ets.id
                """,
                (parent_equipment_type_id,),
            ).fetchall()
            status_rows = connection.execute(
                f"""
                SELECT equipment_subtype_id, name
                FROM equipment_subtype_statuses
                WHERE equipment_subtype_id IN (
                    SELECT id FROM equipment_type_subtypes
                    WHERE parent_equipment_type_id = ? {where_enabled}
                ) AND is_enabled = 1
                ORDER BY sort_order, id
                """,
                (parent_equipment_type_id,),
            ).fetchall()
        statuses_by_subtype: dict[int, list[str]] = {}
        for status_row in status_rows:
            statuses_by_subtype.setdefault(int(status_row["equipment_subtype_id"]), []).append(str(status_row["name"]))
        result = [
            {
                "id": int(row["id"]),
                "parentEquipmentTypeId": int(row["parent_equipment_type_id"]),
                "code": str(row["code"]),
                "name": str(row["name"]),
                "sortOrder": int(row["sort_order"]),
                "isEnabled": bool(row["is_enabled"]),
                "statuses": statuses_by_subtype.get(int(row["id"]), []),
            }
            for row in rows
        ]
        return result

    def replace_equipment_subtype_statuses(
        self, subtype_id: int, payload: EquipmentStatusWriteRequest
    ) -> EquipmentSubtypeItem:
        """Replace editable status choices without orphaning existing rules."""
        self.ensure_schema()
        statuses = list(payload.statuses)
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            subtype = connection.execute(
                """
                SELECT ets.id, ets.parent_equipment_type_id, ets.code, ets.name,
                       ets.sort_order, ets.is_enabled
                FROM equipment_type_subtypes AS ets
                JOIN equipment_types AS et ON et.id = ets.parent_equipment_type_id
                WHERE ets.id = ? AND et.is_enabled = 1
                """,
                (subtype_id,),
            ).fetchone()
            if subtype is None:
                raise BusinessError(
                    "设备子类型不存在",
                    "CATALOG_EQUIPMENT_SUBTYPE_NOT_FOUND",
                    path=["subtypeId"],
                    status_code=404,
                )

            existing = [
                str(row["name"])
                for row in connection.execute(
                    """
                    SELECT name FROM equipment_subtype_statuses
                    WHERE equipment_subtype_id = ?
                    ORDER BY sort_order, id
                    """,
                    (subtype_id,),
                ).fetchall()
            ]
            removed = {name.casefold() for name in existing} - {
                name.casefold() for name in statuses
            }
            if removed:
                used = connection.execute(
                    """
                    SELECT DISTINCT equipment_status
                    FROM test_contents
                    WHERE equipment_type_id = ?
                      AND equipment_subtype = ? COLLATE NOCASE
                      AND equipment_status <> ''
                    """,
                    (int(subtype["parent_equipment_type_id"]), str(subtype["name"])),
                ).fetchall()
                used_removed = {
                    str(row["equipment_status"]).casefold()
                    for row in used
                    if str(row["equipment_status"]).casefold() in removed
                }
                if used_removed:
                    raise BusinessError(
                        "已有正式规则使用被删除的状态/动作，请先处理对应规则",
                        "CATALOG_STATUS_IN_USE",
                        path=["statuses"],
                        status_code=409,
                    )

            connection.execute(
                "DELETE FROM equipment_subtype_statuses WHERE equipment_subtype_id = ?",
                (subtype_id,),
            )
            connection.executemany(
                """
                INSERT INTO equipment_subtype_statuses(
                    equipment_subtype_id, name, sort_order, is_enabled
                ) VALUES (?, ?, ?, 1)
                """,
                ((subtype_id, name, sort_order) for sort_order, name in enumerate(statuses, 1)),
            )

        refreshed = self.list_equipment_subtypes(int(subtype["parent_equipment_type_id"]))
        for item in refreshed:
            if item["id"] == subtype_id:
                return item
        raise RuntimeError("Updated equipment subtype disappeared")

    def list_equipment_hierarchy(
        self, *, include_disabled: bool = False
    ) -> list[EquipmentHierarchyItem]:
        """Return equipment types with their explicitly configured subtypes."""
        types = self.list_equipment_types(include_disabled=include_disabled)
        # Workbook imports from older versions may have stored subtype names as
        # standalone equipment types. Hide those duplicate leaves in the tree
        # response while keeping the rows intact for legacy rule matching.
        subtype_names: set[str] = set()
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                "SELECT DISTINCT name FROM equipment_type_subtypes"
                + ("" if include_disabled else " WHERE is_enabled = 1")
            ).fetchall()
            subtype_names = {str(row["name"]) for row in rows}
        result: list[EquipmentHierarchyItem] = []
        for item in types:
            subtypes = self.list_equipment_subtypes(
                item["id"], include_disabled=include_disabled
            )
            if item["name"] in subtype_names and not subtypes:
                continue
            result.append(
                {
                    **item,
                    "statuses": self._list_equipment_statuses(item["id"], include_disabled=include_disabled),
                    "subtypes": subtypes,
                }
            )
        return result

    def _list_equipment_statuses(self, equipment_type_id: int, *, include_disabled: bool = False) -> list[str]:
        where_enabled = "" if include_disabled else "AND is_enabled = 1"
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                f"SELECT name FROM equipment_type_statuses WHERE equipment_type_id = ? {where_enabled} ORDER BY sort_order, id",
                (equipment_type_id,),
            ).fetchall()
        return [str(row["name"]) for row in rows]

    def list_disciplines(self, *, include_disabled: bool = False) -> list[DisciplineListItem]:
        self.ensure_schema()
        where_clause = "" if include_disabled else "WHERE is_enabled = 1"
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                f"""
                SELECT id, code, name, description, sort_order, is_enabled
                FROM disciplines
                {where_clause}
                ORDER BY sort_order, id
                """
            ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "code": str(row["code"]),
                "name": str(row["name"]),
                "description": str(row["description"]),
                "sortOrder": int(row["sort_order"]),
                "isEnabled": bool(row["is_enabled"]),
            }
            for row in rows
        ]

    def list_stations(self, *, include_disabled: bool = False) -> list[StationListItem]:
        self.ensure_schema()
        where_clause = "" if include_disabled else "WHERE is_enabled = 1"
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                f"""
                SELECT id, code, name, description, sort_order, is_enabled
                FROM stations
                {where_clause}
                ORDER BY sort_order, id
                """
            ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "code": str(row["code"]),
                "name": str(row["name"]),
                "description": str(row["description"]),
                "sortOrder": int(row["sort_order"]),
                "isEnabled": bool(row["is_enabled"]),
            }
            for row in rows
        ]

    def create_station(self, payload: StationWriteRequest) -> StationListItem:
        return self._save_station(None, payload)

    def update_station(
        self, station_id: int, payload: StationWriteRequest
    ) -> StationListItem:
        return self._save_station(station_id, payload)

    def delete_station(self, station_id: int) -> None:
        self.ensure_schema()
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT id FROM stations WHERE id = ?", (station_id,)
            ).fetchone()
            if row is None:
                raise BusinessError(
                    "站点不存在",
                    "CATALOG_STATION_NOT_FOUND",
                    path=["stationId"],
                    status_code=404,
                )
            connection.execute("DELETE FROM stations WHERE id = ?", (station_id,))

    def create_equipment_type(
        self, payload: EquipmentTypeWriteRequest
    ) -> EquipmentTypeItem:
        return self._save_equipment_type(None, payload)

    def update_equipment_type(
        self, equipment_type_id: int, payload: EquipmentTypeWriteRequest
    ) -> EquipmentTypeItem:
        return self._save_equipment_type(equipment_type_id, payload)

    def delete_equipment_type(self, equipment_type_id: int) -> None:
        self.ensure_schema()
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT id FROM equipment_types WHERE id = ?",
                (equipment_type_id,),
            ).fetchone()
            if row is None:
                raise BusinessError(
                    "设备类型不存在",
                    "CATALOG_EQUIPMENT_TYPE_NOT_FOUND",
                    path=["equipmentTypeId"],
                    status_code=404,
                )
            content_count = connection.execute(
                "SELECT COUNT(*) FROM test_contents WHERE equipment_type_id = ?",
                (equipment_type_id,),
            ).fetchone()[0]
            if int(content_count or 0):
                raise BusinessError(
                    "设备类型下存在测试内容，无法删除",
                    "CATALOG_EQUIPMENT_TYPE_IN_USE",
                    path=["equipmentTypeId"],
                    status_code=409,
                )
            subtype_count = connection.execute(
                "SELECT COUNT(*) FROM equipment_type_subtypes WHERE parent_equipment_type_id = ?",
                (equipment_type_id,),
            ).fetchone()[0]
            if int(subtype_count or 0):
                raise BusinessError(
                    "设备类型下存在子类型，无法删除",
                    "CATALOG_EQUIPMENT_TYPE_HAS_SUBTYPES",
                    path=["equipmentTypeId"],
                    status_code=409,
                )
            connection.execute(
                "DELETE FROM equipment_types WHERE id = ?",
                (equipment_type_id,),
            )

    def create_discipline(self, payload: DisciplineWriteRequest) -> DisciplineListItem:
        return self._save_discipline(None, payload)

    def update_discipline(
        self, discipline_id: int, payload: DisciplineWriteRequest
    ) -> DisciplineListItem:
        return self._save_discipline(discipline_id, payload)

    def delete_discipline(self, discipline_id: int) -> None:
        self.ensure_schema()
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT id FROM disciplines WHERE id = ?",
                    (discipline_id,),
                ).fetchone()
                if row is None:
                    raise BusinessError(
                        "责任专业不存在",
                        "CATALOG_DISCIPLINE_NOT_FOUND",
                        path=["disciplineId"],
                        status_code=404,
                    )
                in_use = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM result_output_disciplines
                    WHERE discipline_id = ?
                    """,
                    (discipline_id,),
                ).fetchone()[0]
                if int(in_use or 0):
                    raise BusinessError(
                        "责任专业已被结果输出引用，无法删除",
                        "CATALOG_DISCIPLINE_IN_USE",
                        path=["disciplineId"],
                        status_code=409,
                    )
                connection.execute("DELETE FROM disciplines WHERE id = ?", (discipline_id,))
        except sqlite3.IntegrityError as error:
            raise self._integrity_error(error) from error

    def create_test_content(self, payload: TestContentWriteRequest) -> TestContentItem:
        return self._save_test_content(None, payload)

    def update_test_content(
        self, content_id: int, payload: TestContentWriteRequest
    ) -> TestContentItem:
        return self._save_test_content(content_id, payload)

    def delete_test_content(self, content_id: int) -> None:
        self.ensure_schema()
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            self._require_test_content(connection, content_id)
            self._delete_test_content_tree(connection, content_id)
            connection.execute("DELETE FROM test_contents WHERE id = ?", (content_id,))

    def list_test_contents(
        self,
        *,
        equipment_type: str | None = None,
        equipment_subtype: str | None = None,
        equipment_status: str | None = None,
        include_disabled: bool = False,
        content_id: int | None = None,
    ) -> list[TestContentItem]:
        self.ensure_schema()
        conditions: list[str] = []
        parameters: list[Any] = []
        if not include_disabled:
            conditions.extend(("tc.is_enabled = 1", "et.is_enabled = 1"))
        if equipment_type is not None:
            conditions.append("(et.code = ? COLLATE NOCASE OR et.name = ? COLLATE NOCASE)")
            parameters.extend((equipment_type, equipment_type))
        if equipment_subtype is not None:
            conditions.append("tc.equipment_subtype = ? COLLATE NOCASE")
            parameters.append(equipment_subtype)
        if equipment_status is not None:
            conditions.append("tc.equipment_status = ? COLLATE NOCASE")
            parameters.append(equipment_status)
        if content_id is not None:
            conditions.append("tc.id = ?")
            parameters.append(content_id)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        enabled_step_join = "" if include_disabled else "AND os.is_enabled = 1"
        enabled_result_join = "" if include_disabled else "AND ro.is_enabled = 1"
        enabled_discipline_join = "" if include_disabled else "AND d.is_enabled = 1"

        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                f"""
                SELECT
                    tc.id AS content_id,
                    tc.code AS content_code,
                    tc.content,
                    tc.description AS content_description,
                    tc.revision,
                    tc.sort_order AS content_sort_order,
                    tc.is_enabled AS content_is_enabled,
                    et.id AS equipment_type_id,
                    et.code AS equipment_type_code,
                    et.name AS equipment_type_name,
                    os.id AS step_id,
                    os.description AS step_description,
                    os.ratio_change,
                    os.sort_order AS step_sort_order,
                    ro.id AS result_id,
                    ro.description AS result_description,
                    ro.sort_order AS result_sort_order,
                    d.id AS discipline_id,
                    d.code AS discipline_code,
                    d.name AS discipline_name,
                    rod.sort_order AS discipline_sort_order,
                    tc.equipment_subtype,
                    tc.equipment_status
                FROM test_contents AS tc
                JOIN equipment_types AS et ON et.id = tc.equipment_type_id
                LEFT JOIN operation_steps AS os
                    ON os.test_content_id = tc.id {enabled_step_join}
                LEFT JOIN result_outputs AS ro
                    ON ro.operation_step_id = os.id {enabled_result_join}
                LEFT JOIN result_output_disciplines AS rod
                    ON rod.result_output_id = ro.id
                LEFT JOIN disciplines AS d
                    ON d.id = rod.discipline_id {enabled_discipline_join}
                {where_clause}
                ORDER BY
                    et.sort_order,
                    et.id,
                    tc.sort_order,
                    tc.id,
                    os.sort_order,
                    os.id,
                    ro.sort_order,
                    ro.id,
                    rod.sort_order,
                    d.id
                """,
                parameters,
            ).fetchall()
        return self._assemble_test_contents(rows)

    def find_test_content_rule(
        self,
        equipment_type: str,
        equipment_subtype: str = "",
        equipment_status: str = "",
    ) -> TestContentItem | None:
        """Resolve the most specific catalog rule for a parsed frontend row."""
        self.ensure_schema()
        with closing(self._connect()) as connection, connection:
            row = None
            if equipment_subtype and equipment_status:
                row = connection.execute(
                    """
                    SELECT tc.id FROM test_contents tc
                    JOIN equipment_types et ON et.id = tc.equipment_type_id
                    WHERE tc.is_enabled = 1
                      AND et.is_enabled = 1
                      AND (et.code = ? COLLATE NOCASE OR et.name = ? COLLATE NOCASE)
                      AND tc.equipment_subtype = ? COLLATE NOCASE
                      AND tc.equipment_status = ? COLLATE NOCASE
                    ORDER BY tc.sort_order, tc.id LIMIT 1
                    """,
                    (equipment_type, equipment_type, equipment_subtype, equipment_status),
                ).fetchone()
            if row is None and equipment_subtype:
                row = connection.execute(
                    """
                    SELECT tc.id FROM test_contents tc
                    JOIN equipment_types et ON et.id = tc.equipment_type_id
                    WHERE tc.is_enabled = 1
                      AND et.is_enabled = 1
                      AND (et.code = ? COLLATE NOCASE OR et.name = ? COLLATE NOCASE)
                      AND tc.equipment_subtype = ? COLLATE NOCASE
                      AND tc.equipment_status = ''
                    ORDER BY tc.sort_order, tc.id LIMIT 1
                    """,
                    (equipment_type, equipment_type, equipment_subtype),
                ).fetchone()
            if row is None:
                row = connection.execute(
                    """
                    SELECT tc.id FROM test_contents tc
                    JOIN equipment_types et ON et.id = tc.equipment_type_id
                    WHERE tc.is_enabled = 1 AND et.is_enabled = 1
                      AND (et.code = ? COLLATE NOCASE OR et.name = ? COLLATE NOCASE)
                      AND tc.equipment_subtype = ''
                    ORDER BY tc.sort_order, tc.id LIMIT 1
                    """,
                    (equipment_type, equipment_type),
                ).fetchone()
        if row is None:
            return None
        items = self.list_test_contents(content_id=int(row["id"]))
        return items[0] if items else None

    @staticmethod
    def _assemble_test_contents(rows: list[sqlite3.Row]) -> list[TestContentItem]:
        contents: list[TestContentItem] = []
        content_lookup: dict[int, TestContentItem] = {}
        step_lookup: dict[int, OperationStepItem] = {}
        result_lookup: dict[int, ResultOutputItem] = {}

        for row in rows:
            content_id = int(row["content_id"])
            content = content_lookup.get(content_id)
            if content is None:
                equipment_type = EquipmentTypeSummary(
                    id=int(row["equipment_type_id"]),
                    code=str(row["equipment_type_code"]),
                    name=str(row["equipment_type_name"]),
                )
                content = TestContentItem(
                    id=content_id,
                    equipmentTypeId=int(row["equipment_type_id"]),
                    code=str(row["content_code"]),
                    content=str(row["content"]),
                    description=str(row["content_description"]),
                    revision=int(row["revision"]),
                    sortOrder=int(row["content_sort_order"]),
                    isEnabled=bool(row["content_is_enabled"]),
                    equipmentSubtype=str(row["equipment_subtype"] or ""),
                    equipmentStatus=str(row["equipment_status"] or ""),
                    equipmentType=equipment_type,
                    operationSteps=[],
                )
                content_lookup[content_id] = content
                contents.append(content)

            if row["step_id"] is None:
                continue
            step_id = int(row["step_id"])
            step = step_lookup.get(step_id)
            if step is None:
                step = OperationStepItem(
                    id=step_id,
                    description=str(row["step_description"]),
                    ratioChange=str(row["ratio_change"]),
                    sortOrder=int(row["step_sort_order"]),
                    results=[],
                )
                step_lookup[step_id] = step
                content["operationSteps"].append(step)

            if row["result_id"] is None:
                continue
            result_id = int(row["result_id"])
            result = result_lookup.get(result_id)
            if result is None:
                result = ResultOutputItem(
                    id=result_id,
                    description=str(row["result_description"]),
                    sortOrder=int(row["result_sort_order"]),
                    responsibleDisciplines=[],
                )
                result_lookup[result_id] = result
                step["results"].append(result)

            if row["discipline_id"] is not None:
                result["responsibleDisciplines"].append(
                    DisciplineItem(
                        id=int(row["discipline_id"]),
                        code=str(row["discipline_code"]),
                        name=str(row["discipline_name"]),
                    )
                )

        return contents

    def _save_equipment_type(
        self,
        equipment_type_id: int | None,
        payload: EquipmentTypeWriteRequest,
    ) -> EquipmentTypeItem:
        self.ensure_schema()
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                if equipment_type_id is not None:
                    existing = self._require_equipment_type(connection, equipment_type_id)
                    connection.execute(
                        """
                        UPDATE equipment_types
                        SET code = ?, name = ?, description = ?, sort_order = ?,
                            is_enabled = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        WHERE id = ?
                        """,
                        (
                            payload.code or str(existing["code"]),
                            payload.name,
                            payload.description,
                            payload.sort_order,
                            1 if payload.is_enabled else 0,
                            equipment_type_id,
                        ),
                    )
                    target_id = equipment_type_id
                else:
                    equipment_code = payload.code or self._generate_code(
                        connection, "equipment_types", "TYPE"
                    )
                    cursor = connection.execute(
                        """
                        INSERT INTO equipment_types(
                            code, name, description, sort_order, is_enabled
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            equipment_code,
                            payload.name,
                            payload.description,
                            payload.sort_order,
                            1 if payload.is_enabled else 0,
                        ),
                    )
                    target_id = int(cursor.lastrowid)
                if payload.subtypes is not None:
                    self._save_equipment_subtypes(connection, target_id, payload.subtypes)
        except sqlite3.IntegrityError as error:
            raise self._integrity_error(error) from error
        return self._get_equipment_type_or_raise(target_id)

    @staticmethod
    def _generate_code(
        connection: sqlite3.Connection, table_name: str, prefix: str
    ) -> str:
        while True:
            code = f"{prefix}_{uuid4().hex[:12].upper()}"
            exists = connection.execute(
                f"SELECT 1 FROM {table_name} WHERE code = ? COLLATE NOCASE LIMIT 1",
                (code,),
            ).fetchone()
            if exists is None:
                return code

    def _save_equipment_subtypes(
        self,
        connection: sqlite3.Connection,
        parent_id: int,
        subtypes: list[EquipmentSubtypeWriteRequest],
    ) -> None:
        parent = self._require_equipment_type(connection, parent_id)
        incoming_ids = {int(subtype.id) for subtype in subtypes if subtype.id is not None}
        existing_rows = connection.execute(
            """
            SELECT id, name FROM equipment_type_subtypes
            WHERE parent_equipment_type_id = ?
            """,
            (parent_id,),
        ).fetchall()
        for existing in existing_rows:
            existing_id = int(existing["id"])
            if existing_id in incoming_ids:
                continue
            self._delete_equipment_subtype_in_transaction(
                connection, existing_id, parent_id
            )

        for subtype in subtypes:
            subtype_id = getattr(subtype, "id", None)
            if subtype_id is None:
                subtype_code = self._generate_code(
                    connection, "equipment_type_subtypes", f"{parent['code']}_SUBTYPE"
                )
                cursor = connection.execute(
                    """
                    INSERT INTO equipment_type_subtypes(
                        parent_equipment_type_id, code, name, sort_order, is_enabled
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        parent_id,
                        subtype_code,
                        subtype.name,
                        subtype.sort_order,
                        1 if subtype.is_enabled else 0,
                    ),
                )
                subtype_id = int(cursor.lastrowid)
            else:
                existing = connection.execute(
                    """
                    SELECT id, name FROM equipment_type_subtypes
                    WHERE id = ? AND parent_equipment_type_id = ?
                    """,
                    (subtype_id, parent_id),
                ).fetchone()
                if existing is None:
                    raise BusinessError(
                        "设备子类型不属于当前设备类型",
                        "CATALOG_EQUIPMENT_SUBTYPE_PARENT_MISMATCH",
                        path=["subtypes"],
                        status_code=409,
                    )
                if str(existing["name"]).casefold() != subtype.name.casefold():
                    rule_count = connection.execute(
                        """
                        SELECT COUNT(*) FROM test_contents
                        WHERE equipment_type_id = ?
                          AND equipment_subtype = ? COLLATE NOCASE
                        """,
                        (parent_id, str(existing["name"])),
                    ).fetchone()[0]
                    if int(rule_count or 0):
                        raise BusinessError(
                            "设备子类型已被测试规则使用，无法重命名",
                            "CATALOG_EQUIPMENT_SUBTYPE_IN_USE",
                            path=["subtypes"],
                            status_code=409,
                        )
                connection.execute(
                    """
                    UPDATE equipment_type_subtypes
                    SET name = ?, sort_order = ?, is_enabled = ?,
                        updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    WHERE id = ?
                    """,
                    (
                        subtype.name,
                        subtype.sort_order,
                        1 if subtype.is_enabled else 0,
                        subtype_id,
                    ),
                )

            self._replace_subtype_statuses(
                connection, int(subtype_id), list(subtype.statuses)
            )

    def _replace_subtype_statuses(
        self,
        connection: sqlite3.Connection,
        subtype_id: int,
        statuses: list[str],
    ) -> None:
        existing = [
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM equipment_subtype_statuses WHERE equipment_subtype_id = ?",
                (subtype_id,),
            ).fetchall()
        ]
        removed = {name.casefold() for name in existing} - {
            name.casefold() for name in statuses
        }
        if removed:
            subtype = connection.execute(
                "SELECT parent_equipment_type_id, name FROM equipment_type_subtypes WHERE id = ?",
                (subtype_id,),
            ).fetchone()
            used = connection.execute(
                """
                SELECT DISTINCT equipment_status FROM test_contents
                WHERE equipment_type_id = ? AND equipment_subtype = ? COLLATE NOCASE
                  AND equipment_status <> ''
                """,
                (int(subtype["parent_equipment_type_id"]), str(subtype["name"])),
            ).fetchall()
            if any(str(row["equipment_status"]).casefold() in removed for row in used):
                raise BusinessError(
                    "已有正式规则使用被删除的状态/动作，请先处理对应规则",
                    "CATALOG_STATUS_IN_USE",
                    path=["subtypes"],
                    status_code=409,
                )
        connection.execute(
            "DELETE FROM equipment_subtype_statuses WHERE equipment_subtype_id = ?",
            (subtype_id,),
        )
        connection.executemany(
            """
            INSERT INTO equipment_subtype_statuses(
                equipment_subtype_id, name, sort_order, is_enabled
            ) VALUES (?, ?, ?, 1)
            """,
            ((subtype_id, name, index) for index, name in enumerate(statuses, 1)),
        )

    def delete_equipment_subtype(self, subtype_id: int) -> None:
        self.ensure_schema()
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            self._delete_equipment_subtype_in_transaction(connection, subtype_id)

    def _delete_equipment_subtype_in_transaction(
        self,
        connection: sqlite3.Connection,
        subtype_id: int,
        parent_id: int | None = None,
    ) -> None:
        subtype = connection.execute(
            """
            SELECT id, parent_equipment_type_id, name
            FROM equipment_type_subtypes
            WHERE id = ?
            """,
            (subtype_id,),
        ).fetchone()
        if subtype is None or (
            parent_id is not None and int(subtype["parent_equipment_type_id"]) != parent_id
        ):
            raise BusinessError(
                "设备子类型不存在",
                "CATALOG_EQUIPMENT_SUBTYPE_NOT_FOUND",
                path=["subtypeId"],
                status_code=404,
            )
        rule_count = connection.execute(
            """
            SELECT COUNT(*) FROM test_contents
            WHERE equipment_type_id = ?
              AND equipment_subtype = ? COLLATE NOCASE
            """,
            (int(subtype["parent_equipment_type_id"]), str(subtype["name"])),
        ).fetchone()[0]
        if int(rule_count or 0):
            raise BusinessError(
                "设备子类型已被测试规则使用，无法删除",
                "CATALOG_EQUIPMENT_SUBTYPE_IN_USE",
                path=["subtypeId"],
                status_code=409,
            )
        connection.execute(
            "DELETE FROM equipment_subtype_statuses WHERE equipment_subtype_id = ?",
            (subtype_id,),
        )
        connection.execute(
            "DELETE FROM equipment_type_subtypes WHERE id = ?",
            (subtype_id,),
        )

    def _save_discipline(
        self,
        discipline_id: int | None,
        payload: DisciplineWriteRequest,
    ) -> DisciplineListItem:
        self.ensure_schema()
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                if discipline_id is not None:
                    existing = self._require_discipline(connection, discipline_id)
                    connection.execute(
                        """
                        UPDATE disciplines
                        SET code = ?, name = ?, description = ?, sort_order = ?,
                            is_enabled = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        WHERE id = ?
                        """,
                        (
                            payload.code or str(existing["code"]),
                            payload.name,
                            payload.description,
                            payload.sort_order,
                            1 if payload.is_enabled else 0,
                            discipline_id,
                        ),
                    )
                    target_id = discipline_id
                else:
                    discipline_code = payload.code or self._generate_code(
                        connection, "disciplines", "DISC"
                    )
                    cursor = connection.execute(
                        """
                        INSERT INTO disciplines(
                            code, name, description, sort_order, is_enabled
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            discipline_code,
                            payload.name,
                            payload.description,
                            payload.sort_order,
                            1 if payload.is_enabled else 0,
                        ),
                    )
                    target_id = int(cursor.lastrowid)
        except sqlite3.IntegrityError as error:
            raise self._integrity_error(error) from error
        return self._get_discipline_or_raise(target_id)

    def _save_station(
        self, station_id: int | None, payload: StationWriteRequest
    ) -> StationListItem:
        self.ensure_schema()
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                if station_id is not None:
                    row = connection.execute(
                        "SELECT id, code FROM stations WHERE id = ?", (station_id,)
                    ).fetchone()
                    if row is None:
                        raise BusinessError(
                            "站点不存在",
                            "CATALOG_STATION_NOT_FOUND",
                            path=["stationId"],
                            status_code=404,
                        )
                    connection.execute(
                        """
                        UPDATE stations
                        SET code = ?, name = ?, description = ?, sort_order = ?,
                            is_enabled = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        WHERE id = ?
                        """,
                        (
                            payload.code or str(row["code"]),
                            payload.name,
                            payload.description,
                            payload.sort_order,
                            1 if payload.is_enabled else 0,
                            station_id,
                        ),
                    )
                    target_id = station_id
                else:
                    station_code = payload.code or self._generate_code(
                        connection, "stations", "STATION"
                    )
                    cursor = connection.execute(
                        """
                        INSERT INTO stations(code, name, description, sort_order, is_enabled)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            station_code,
                            payload.name,
                            payload.description,
                            payload.sort_order,
                            1 if payload.is_enabled else 0,
                        ),
                    )
                    target_id = int(cursor.lastrowid)
        except sqlite3.IntegrityError as error:
            raise self._integrity_error(error) from error
        return self._get_station_or_raise(target_id)

    def _save_test_content(
        self,
        content_id: int | None,
        payload: TestContentWriteRequest,
    ) -> TestContentItem:
        self.ensure_schema()
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                self._require_equipment_type(connection, payload.equipment_type_id)
                if content_id is not None:
                    existing = self._require_test_content(connection, content_id)
                    connection.execute(
                        """
                        UPDATE test_contents
                        SET code = ?, equipment_type_id = ?, equipment_subtype = ?,
                            equipment_status = ?,
                            content = ?, description = ?,
                            revision = ?, sort_order = ?, is_enabled = ?,
                            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        WHERE id = ?
                        """,
                        (
                            payload.code or str(existing["code"]),
                            payload.equipment_type_id,
                            payload.equipment_subtype,
                            payload.equipment_status,
                            payload.content,
                            payload.description,
                            payload.revision,
                            payload.sort_order,
                            1 if payload.is_enabled else 0,
                            content_id,
                        ),
                    )
                    target_id = content_id
                else:
                    content_code = payload.code or self._generate_code(
                        connection, "test_contents", "RULE"
                    )
                    cursor = connection.execute(
                        """
                        INSERT INTO test_contents(
                            code, equipment_type_id, equipment_subtype, equipment_status,
                            content, description,
                            revision, sort_order, is_enabled
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            content_code,
                            payload.equipment_type_id,
                            payload.equipment_subtype,
                            payload.equipment_status,
                            payload.content,
                            payload.description,
                            payload.revision,
                            payload.sort_order,
                            1 if payload.is_enabled else 0,
                        ),
                    )
                    target_id = int(cursor.lastrowid)

                self._delete_test_content_tree(connection, target_id)
                for step in payload.operation_steps:
                    step_cursor = connection.execute(
                        """
                        INSERT INTO operation_steps(
                            test_content_id, description, ratio_change, sort_order, is_enabled
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            target_id,
                            step.description,
                            step.ratio_change,
                            step.sort_order,
                            1 if step.is_enabled else 0,
                        ),
                    )
                    step_id = int(step_cursor.lastrowid)
                    for result in step.results:
                        result_cursor = connection.execute(
                            """
                            INSERT INTO result_outputs(
                                operation_step_id, description, sort_order, is_enabled
                            ) VALUES (?, ?, ?, ?)
                            """,
                            (
                                step_id,
                                result.description,
                                result.sort_order,
                                1 if result.is_enabled else 0,
                            ),
                        )
                        result_id = int(result_cursor.lastrowid)
                        for discipline_sort_order, discipline_id in enumerate(
                            result.responsible_discipline_ids, start=1
                        ):
                            self._require_discipline(connection, discipline_id)
                            connection.execute(
                                """
                                INSERT INTO result_output_disciplines(
                                    result_output_id, discipline_id, sort_order
                                ) VALUES (?, ?, ?)
                                """,
                                (result_id, discipline_id, discipline_sort_order),
                            )
        except sqlite3.IntegrityError as error:
            raise self._integrity_error(error) from error
        return self._get_test_content_or_raise(target_id)

    def _delete_test_content_tree(
        self, connection: sqlite3.Connection, content_id: int
    ) -> None:
        step_ids = [
            int(row["id"])
            for row in connection.execute(
                "SELECT id FROM operation_steps WHERE test_content_id = ?",
                (content_id,),
            ).fetchall()
        ]
        if not step_ids:
            return
        result_ids = [
            int(row["id"])
            for row in connection.execute(
                f"""
                SELECT id FROM result_outputs
                WHERE operation_step_id IN ({",".join("?" for _ in step_ids)})
                """,
                step_ids,
            ).fetchall()
        ]
        if result_ids:
            connection.execute(
                f"""
                DELETE FROM result_output_disciplines
                WHERE result_output_id IN ({",".join("?" for _ in result_ids)})
                """,
                result_ids,
            )
            connection.execute(
                f"""
                DELETE FROM result_outputs
                WHERE id IN ({",".join("?" for _ in result_ids)})
                """,
                result_ids,
            )
        connection.execute(
            f"""
            DELETE FROM operation_steps
            WHERE id IN ({",".join("?" for _ in step_ids)})
            """,
            step_ids,
        )

    def _require_equipment_type(
        self, connection: sqlite3.Connection, equipment_type_id: int
    ) -> sqlite3.Row:
        row = connection.execute(
            "SELECT id, code, name, description, sort_order, is_enabled "
            "FROM equipment_types WHERE id = ?",
            (equipment_type_id,),
        ).fetchone()
        if row is None:
            raise BusinessError(
                "设备类型不存在",
                "CATALOG_EQUIPMENT_TYPE_NOT_FOUND",
                path=["equipmentTypeId"],
                status_code=404,
            )
        return row

    def _require_discipline(
        self, connection: sqlite3.Connection, discipline_id: int
    ) -> sqlite3.Row:
        row = connection.execute(
            "SELECT id, code, name, description, sort_order, is_enabled "
            "FROM disciplines WHERE id = ?",
            (discipline_id,),
        ).fetchone()
        if row is None:
            raise BusinessError(
                "责任专业不存在",
                "CATALOG_DISCIPLINE_NOT_FOUND",
                path=["responsibleDisciplineIds"],
                status_code=404,
            )
        return row

    def _require_test_content(
        self, connection: sqlite3.Connection, content_id: int
    ) -> sqlite3.Row:
        row = connection.execute(
            """
            SELECT id, code, equipment_type_id, content, description, revision,
                   sort_order, is_enabled
            FROM test_contents
            WHERE id = ?
            """,
            (content_id,),
        ).fetchone()
        if row is None:
            raise BusinessError(
                "测试内容不存在",
                "CATALOG_TEST_CONTENT_NOT_FOUND",
                path=["testContentId"],
                status_code=404,
            )
        return row

    def _get_equipment_type_or_raise(self, equipment_type_id: int) -> EquipmentTypeItem:
        self.ensure_schema()
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT id, code, name, description, sort_order, is_enabled
                FROM equipment_types
                WHERE id = ?
                """,
                (equipment_type_id,),
            ).fetchone()
        if row is None:
            raise BusinessError(
                "设备类型不存在",
                "CATALOG_EQUIPMENT_TYPE_NOT_FOUND",
                path=["equipmentTypeId"],
                status_code=404,
            )
        return {
            "id": int(row["id"]),
            "code": str(row["code"]),
            "name": str(row["name"]),
            "description": str(row["description"]),
            "sortOrder": int(row["sort_order"]),
            "isEnabled": bool(row["is_enabled"]),
        }

    def _get_discipline_or_raise(self, discipline_id: int) -> DisciplineListItem:
        self.ensure_schema()
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT id, code, name, description, sort_order, is_enabled
                FROM disciplines
                WHERE id = ?
                """,
                (discipline_id,),
            ).fetchone()
        if row is None:
            raise BusinessError(
                "责任专业不存在",
                "CATALOG_DISCIPLINE_NOT_FOUND",
                path=["disciplineId"],
                status_code=404,
            )
        return {
            "id": int(row["id"]),
            "code": str(row["code"]),
            "name": str(row["name"]),
            "description": str(row["description"]),
            "sortOrder": int(row["sort_order"]),
            "isEnabled": bool(row["is_enabled"]),
        }

    def _get_station_or_raise(self, station_id: int) -> StationListItem:
        self.ensure_schema()
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT id, code, name, description, sort_order, is_enabled
                FROM stations WHERE id = ?
                """,
                (station_id,),
            ).fetchone()
        if row is None:
            raise BusinessError(
                "站点不存在",
                "CATALOG_STATION_NOT_FOUND",
                path=["stationId"],
                status_code=404,
            )
        return {
            "id": int(row["id"]),
            "code": str(row["code"]),
            "name": str(row["name"]),
            "description": str(row["description"]),
            "sortOrder": int(row["sort_order"]),
            "isEnabled": bool(row["is_enabled"]),
        }

    def _get_test_content_or_raise(self, content_id: int) -> TestContentItem:
        items = self.list_test_contents(content_id=content_id, include_disabled=True)
        if not items:
            raise BusinessError(
                "测试内容不存在",
                "CATALOG_TEST_CONTENT_NOT_FOUND",
                path=["testContentId"],
                status_code=404,
            )
        return items[0]

    @staticmethod
    def _integrity_error(error: sqlite3.IntegrityError) -> BusinessError:
        message = str(error)
        if "equipment_types.code" in message:
            return BusinessError(
                "设备类型编码已存在",
                "CATALOG_EQUIPMENT_TYPE_CODE_CONFLICT",
                status_code=409,
            )
        if "disciplines.code" in message:
            return BusinessError(
                "责任专业编码已存在",
                "CATALOG_DISCIPLINE_CODE_CONFLICT",
                status_code=409,
            )
        if "stations.code" in message or "stations.name" in message:
            return BusinessError(
                "站点编码或名称已存在",
                "CATALOG_STATION_CODE_OR_NAME_CONFLICT",
                status_code=409,
            )
        if "test_contents.code" in message:
            return BusinessError(
                "测试内容编码已存在",
                "CATALOG_TEST_CONTENT_CODE_CONFLICT",
                status_code=409,
            )
        if "operation_steps.test_content_id, operation_steps.sort_order" in message:
            return BusinessError(
                "同一测试内容下的操作步骤排序不能重复",
                "CATALOG_OPERATION_STEP_SORT_CONFLICT",
                status_code=409,
            )
        if "result_outputs.operation_step_id, result_outputs.sort_order" in message:
            return BusinessError(
                "同一步骤下的结果输出排序不能重复",
                "CATALOG_RESULT_OUTPUT_SORT_CONFLICT",
                status_code=409,
            )
        if (
            "result_output_disciplines.result_output_id, "
            "result_output_disciplines.sort_order"
        ) in message:
            return BusinessError(
                "同一结果输出下的责任专业排序不能重复",
                "CATALOG_DISCIPLINE_SORT_CONFLICT",
                status_code=409,
            )
        if "FOREIGN KEY constraint failed" in message:
            return BusinessError(
                "提交的数据包含不存在的关联项",
                "CATALOG_FOREIGN_KEY_CONFLICT",
                status_code=409,
            )
        return BusinessError(
            "规则保存失败",
            "CATALOG_WRITE_FAILED",
            status_code=500,
        )
