"""Persistence and authorization for the configurable workspace domain."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.db.catalog import CatalogRepository
from app.exceptions import BusinessError
from app.schemas.workspace import (
    BatchConfigCopyRequest,
    ConfigCopyRequest,
    ConfigImportRequest,
    ConfigResultWriteRequest,
    ConfigStepWriteRequest,
    ConfigWriteRequest,
    DebugItemsBatchWriteRequest,
    DebugItemWriteRequest,
    LineWriteRequest,
    ProfessionBatchWriteRequest,
    ProfessionWriteRequest,
    ProjectWriteRequest,
    ScopeSelection,
    UserWriteRequest,
    WorkspaceCatalogWriteRequest,
    WorkspaceStationsBatchWriteRequest,
)
from app.security import hash_password

ROLE_SUPER_ADMIN = "super_admin"
ROLE_LINE_ADMIN = "line_admin"
ROLE_PROFESSIONAL_CONFIGURATOR = "professional_configurator"
ROLES = {ROLE_SUPER_ADMIN, ROLE_LINE_ADMIN, ROLE_PROFESSIONAL_CONFIGURATOR}


class WorkspaceRepository:
    def __init__(self, database_path: Path) -> None:
        self.database = CatalogRepository(database_path)

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        return self.database._connect()

    @property
    def database_path(self) -> Path:
        return self.database.database_path

    def ensure_schema(self) -> None:
        self.database.ensure_schema()
        with closing(self._connect()) as connection, connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS workspace_lines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    name TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 1,
                    is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS workspace_professions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    name TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 1,
                    is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                )
            """)
            profession_columns = {
                str(row[1]) for row in connection.execute("PRAGMA table_info(workspace_professions)")
            }
            if "parent_id" not in profession_columns:
                connection.execute(
                    "ALTER TABLE workspace_professions ADD COLUMN parent_id "
                    "INTEGER REFERENCES workspace_professions(id) ON DELETE RESTRICT"
                )
            connection.execute("""
                CREATE TABLE IF NOT EXISTS workspace_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    line_id INTEGER,
                    profession_id INTEGER NOT NULL,
                    code TEXT NOT NULL COLLATE NOCASE,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    engine_code TEXT NOT NULL DEFAULT '',
                    sort_order INTEGER NOT NULL DEFAULT 1,
                    is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    FOREIGN KEY (profession_id) REFERENCES workspace_professions(id) ON DELETE RESTRICT,
                    UNIQUE (line_id, profession_id, code)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS workspace_configs (
                    id TEXT PRIMARY KEY,
                    business_id TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    line_id INTEGER NOT NULL,
                    profession_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    debug_subitem_id TEXT,
                    debug_division_id TEXT,
                    config_code TEXT NOT NULL,
                    device_type TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
                    revision INTEGER NOT NULL DEFAULT 1,
                    created_by INTEGER,
                    updated_by INTEGER,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    FOREIGN KEY (line_id) REFERENCES workspace_lines(id) ON DELETE RESTRICT,
                    FOREIGN KEY (profession_id) REFERENCES workspace_professions(id) ON DELETE RESTRICT,
                    FOREIGN KEY (project_id) REFERENCES workspace_projects(id) ON DELETE RESTRICT,
                    UNIQUE (line_id, profession_id, project_id, config_code)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS workspace_catalog_items (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    line_id INTEGER NOT NULL,
                    profession_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    code TEXT NOT NULL DEFAULT '',
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    sort_order INTEGER NOT NULL DEFAULT 1,
                    is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    FOREIGN KEY (line_id) REFERENCES workspace_lines(id) ON DELETE RESTRICT,
                    FOREIGN KEY (profession_id) REFERENCES workspace_professions(id) ON DELETE RESTRICT,
                    FOREIGN KEY (project_id) REFERENCES workspace_projects(id) ON DELETE RESTRICT,
                    UNIQUE (category, line_id, profession_id, project_id, code),
                    UNIQUE (category, line_id, profession_id, project_id, name)
                )
            """)
            catalog_columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(workspace_catalog_items)")}
            if "parent_id" not in catalog_columns:
                connection.execute("ALTER TABLE workspace_catalog_items ADD COLUMN parent_id TEXT")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS workspace_debug_items (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL CHECK (category IN ('debug_subitems', 'debug_divisions')),
                    line_id INTEGER NOT NULL,
                    profession_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    parent_id TEXT,
                    code TEXT NOT NULL DEFAULT '',
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    sort_order INTEGER NOT NULL DEFAULT 1,
                    is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    UNIQUE (category, line_id, profession_id, project_id, parent_id, code),
                    UNIQUE (category, line_id, profession_id, project_id, parent_id, name)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS workspace_config_classifications (
                    config_id TEXT NOT NULL,
                    debug_subitem_id TEXT NOT NULL,
                    debug_division_id TEXT,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    FOREIGN KEY (config_id) REFERENCES workspace_configs(id) ON DELETE CASCADE,
                    FOREIGN KEY (debug_subitem_id) REFERENCES workspace_debug_items(id) ON DELETE RESTRICT,
                    FOREIGN KEY (debug_division_id) REFERENCES workspace_debug_items(id) ON DELETE RESTRICT
                )
            """)
            classification_columns = connection.execute(
                "PRAGMA table_info(workspace_config_classifications)"
            ).fetchall()
            division_column = next(
                (row for row in classification_columns if row["name"] == "debug_division_id"), None
            )
            if division_column and division_column["notnull"]:
                connection.execute("""
                    CREATE TABLE workspace_config_classifications_new (
                        config_id TEXT NOT NULL,
                        debug_subitem_id TEXT NOT NULL,
                        debug_division_id TEXT,
                        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                        FOREIGN KEY (config_id) REFERENCES workspace_configs(id) ON DELETE CASCADE,
                        FOREIGN KEY (debug_subitem_id) REFERENCES workspace_debug_items(id) ON DELETE RESTRICT,
                        FOREIGN KEY (debug_division_id) REFERENCES workspace_debug_items(id) ON DELETE RESTRICT
                    )
                """)
                connection.execute("""
                    INSERT INTO workspace_config_classifications_new(
                        config_id, debug_subitem_id, debug_division_id, created_at
                    ) SELECT config_id, debug_subitem_id, debug_division_id, created_at
                    FROM workspace_config_classifications
                """)
                connection.execute("DROP TABLE workspace_config_classifications")
                connection.execute(
                    "ALTER TABLE workspace_config_classifications_new RENAME TO workspace_config_classifications"
                )
            connection.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_workspace_config_classification_division
                ON workspace_config_classifications(config_id, debug_subitem_id, debug_division_id)
                WHERE debug_division_id IS NOT NULL
            """)
            connection.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_workspace_config_classification_subitem
                ON workspace_config_classifications(config_id, debug_subitem_id)
                WHERE debug_division_id IS NULL
            """)
            connection.execute("""INSERT OR IGNORE INTO workspace_config_classifications(
                config_id, debug_subitem_id, debug_division_id)
                SELECT id, debug_subitem_id, debug_division_id FROM workspace_configs
                WHERE debug_subitem_id IS NOT NULL AND debug_division_id IS NOT NULL""")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS workspace_config_aliases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_id TEXT NOT NULL,
                    alias TEXT NOT NULL,
                    is_current INTEGER NOT NULL DEFAULT 0 CHECK (is_current IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    FOREIGN KEY (config_id) REFERENCES workspace_configs(id) ON DELETE CASCADE,
                    UNIQUE (config_id, alias)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS workspace_config_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_id TEXT NOT NULL,
                    sort_order INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    ratio_change TEXT NOT NULL DEFAULT '否' CHECK (ratio_change IN ('是', '否')),
                    is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
                    FOREIGN KEY (config_id) REFERENCES workspace_configs(id) ON DELETE RESTRICT,
                    UNIQUE (config_id, sort_order)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS workspace_config_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    step_id INTEGER NOT NULL,
                    sort_order INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    responsible_disciplines TEXT NOT NULL DEFAULT '[]',
                    FOREIGN KEY (step_id) REFERENCES workspace_config_steps(id) ON DELETE RESTRICT,
                    UNIQUE (step_id, sort_order)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS workspace_config_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    snapshot TEXT NOT NULL,
                    changed_by INTEGER,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    FOREIGN KEY (config_id) REFERENCES workspace_configs(id) ON DELETE RESTRICT
                )
            """)
            for statement in (
                "CREATE INDEX IF NOT EXISTS ix_workspace_configs_scope "
                "ON workspace_configs(line_id, profession_id, project_id)",
                "CREATE INDEX IF NOT EXISTS ix_workspace_aliases_alias ON workspace_config_aliases(alias)",
                "CREATE INDEX IF NOT EXISTS ix_workspace_steps_config ON workspace_config_steps(config_id, sort_order)",
                "CREATE INDEX IF NOT EXISTS ix_workspace_catalog_scope "
                "ON workspace_catalog_items(category, line_id, profession_id, project_id)",
            ):
                connection.execute(statement)
            columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(auth_users)")}
            project_columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(workspace_projects)")}
            if "line_id" not in project_columns:
                connection.execute("ALTER TABLE workspace_projects ADD COLUMN line_id INTEGER")
            # Project codes may repeat across lines and professions. Rebuild
            # older project tables with the full business key while
            # retaining IDs referenced by configs and every existing value.
            legacy_unique = False
            for index in connection.execute("PRAGMA index_list(workspace_projects)").fetchall():
                if int(index[2]):
                    indexed = tuple(
                        str(col[2]) for col in connection.execute(f"PRAGMA index_info('{index[1]}')").fetchall()
                    )
                    if indexed == ("profession_id", "code"):
                        legacy_unique = True
                        break
            if legacy_unique:
                connection.commit()
                connection.execute("PRAGMA foreign_keys = OFF")
                connection.execute("PRAGMA legacy_alter_table = ON")
                connection.execute("ALTER TABLE workspace_projects RENAME TO workspace_projects_legacy")
                connection.execute("""CREATE TABLE workspace_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, line_id INTEGER, profession_id INTEGER NOT NULL,
                    code TEXT NOT NULL COLLATE NOCASE, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
                    engine_code TEXT NOT NULL DEFAULT '', sort_order INTEGER NOT NULL DEFAULT 1,
                    is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    FOREIGN KEY (profession_id) REFERENCES workspace_professions(id) ON DELETE RESTRICT,
                    UNIQUE (line_id, profession_id, code))""")
                connection.execute("""INSERT INTO workspace_projects
                    (id, line_id, profession_id, code, name, description, engine_code,
                     sort_order, is_enabled, created_at, updated_at)
                    SELECT id, line_id, profession_id, code, name, description, engine_code,
                           sort_order, is_enabled, created_at, updated_at
                    FROM workspace_projects_legacy""")
                connection.execute("DROP TABLE workspace_projects_legacy")
                connection.execute("PRAGMA legacy_alter_table = OFF")
                connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_workspace_projects_line_code "
                "ON workspace_projects(line_id, code COLLATE NOCASE)"
            )
            config_columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(workspace_configs)")}
            for name, sql in (
                (
                    "debug_subitem_id",
                    "ALTER TABLE workspace_configs ADD COLUMN debug_subitem_id TEXT",
                ),
                (
                    "debug_division_id",
                    "ALTER TABLE workspace_configs ADD COLUMN debug_division_id TEXT",
                ),
            ):
                if name not in config_columns:
                    connection.execute(sql)
            for name, sql in (
                (
                    "role",
                    "ALTER TABLE auth_users ADD COLUMN role TEXT NOT NULL DEFAULT 'professional_configurator'",
                ),
                ("line_id", "ALTER TABLE auth_users ADD COLUMN line_id INTEGER"),
                ("profession_id", "ALTER TABLE auth_users ADD COLUMN profession_id INTEGER"),
            ):
                if name not in columns:
                    connection.execute(sql)
            if "role" not in columns:
                # Accounts created before role support were administrators.
                # Preserve that access when upgrading an existing database.
                connection.execute(
                    "UPDATE auth_users SET role = 'super_admin' WHERE role = 'professional_configurator'"
                )
            self._seed_defaults(connection)

    def list_catalog_items(
        self, scope: ScopeSelection, category: str, include_disabled: bool = False
    ) -> list[dict[str, Any]]:
        self.ensure_schema()
        if category in {"disciplines", "stations"}:
            with closing(self._connect()) as validation:
                if (
                    validation.execute(
                        "SELECT 1 FROM workspace_lines WHERE id = ? AND is_enabled = 1",
                        (scope.line_id,),
                    ).fetchone()
                    is None
                ):
                    raise BusinessError("线路不存在或已停用", "WORKSPACE_SCOPE_NOT_FOUND", status_code=404)
                if category == "disciplines" and (
                    validation.execute(
                        "SELECT 1 FROM workspace_professions WHERE id = ? AND is_enabled = 1",
                        (scope.profession_id,),
                    ).fetchone()
                    is None
                ):
                    raise BusinessError("专业不存在或已停用", "WORKSPACE_SCOPE_NOT_FOUND", status_code=404)
        else:
            self.get_scope(scope)
        with closing(self._connect()) as connection:
            query = "SELECT * FROM workspace_catalog_items WHERE category = ? AND line_id = ?"
            params: list[Any] = [category, scope.line_id]
            if category not in {"disciplines", "stations"}:
                query += " AND profession_id = ? AND project_id = ?"
                params.extend([scope.profession_id, scope.project_id])
            if not include_disabled:
                query += " AND is_enabled = 1"
            query += " ORDER BY sort_order, name COLLATE NOCASE, id"
            return [self._catalog_item(row) for row in connection.execute(query, params).fetchall()]

    def list_line_stations(self, line_id: int, include_disabled: bool = False) -> list[dict[str, Any]]:
        self.ensure_schema()
        query = "SELECT * FROM workspace_catalog_items WHERE category = 'stations' AND line_id = ?"
        if not include_disabled:
            query += " AND is_enabled = 1"
        query += " ORDER BY sort_order, name COLLATE NOCASE, id"
        with closing(self._connect()) as connection:
            return [
                self._catalog_item(row)
                for row in connection.execute(query, (line_id,)).fetchall()
            ]

    def save_catalog_item(self, payload: WorkspaceCatalogWriteRequest, item_id: str | None = None) -> dict[str, Any]:
        self.ensure_schema()
        if payload.category in {"disciplines", "stations"}:
            with closing(self._connect()) as validation:
                if (
                    validation.execute(
                        "SELECT 1 FROM workspace_lines WHERE id = ? AND is_enabled = 1",
                        (payload.scope.line_id,),
                    ).fetchone()
                    is None
                ):
                    raise BusinessError("线路不存在或已停用", "WORKSPACE_SCOPE_NOT_FOUND", status_code=404)
                if payload.category == "disciplines" and (
                    validation.execute(
                        "SELECT 1 FROM workspace_professions WHERE id = ? AND is_enabled = 1",
                        (payload.scope.profession_id,),
                    ).fetchone()
                    is None
                ):
                    raise BusinessError("专业不存在或已停用", "WORKSPACE_SCOPE_NOT_FOUND", status_code=404)
        else:
            self.get_scope(payload.scope)
        try:
            with closing(self._connect()) as connection, connection:
                shared_by_line = payload.category in {"disciplines", "stations"}
                project_id = payload.scope.project_id
                if payload.category == "disciplines":
                    valid_project = connection.execute(
                        "SELECT id FROM workspace_projects WHERE id = ?", (project_id,)
                    ).fetchone()
                    if valid_project is None:
                        fallback = connection.execute(
                            "SELECT id FROM workspace_projects ORDER BY id LIMIT 1"
                        ).fetchone()
                        if fallback is None:
                            raise BusinessError(
                                "请先建立一个联调项目后再管理责任专业目录",
                                "WORKSPACE_PROJECT_REQUIRED",
                                status_code=409,
                            )
                        project_id = int(fallback[0])
                if shared_by_line:
                    duplicate_query = (
                        "SELECT id FROM workspace_catalog_items WHERE category = ? AND line_id = ? "
                        "AND parent_id IS ? AND (name = ? COLLATE NOCASE OR (? <> '' AND code = ? COLLATE NOCASE))"
                    )
                    duplicate_params: list[Any] = [
                        payload.category,
                        payload.scope.line_id,
                        payload.parent_id,
                        payload.name,
                        payload.code,
                        payload.code,
                    ]
                    if item_id is not None:
                        duplicate_query += " AND id <> ?"
                        duplicate_params.append(item_id)
                    if connection.execute(duplicate_query, duplicate_params).fetchone():
                        raise BusinessError(
                            "同一线路下的名称或编码已存在",
                            "WORKSPACE_CATALOG_EXISTS",
                            status_code=409,
                        )
                    if payload.category == "disciplines" and payload.parent_id:
                        parent = connection.execute(
                            "SELECT parent_id FROM workspace_catalog_items WHERE id = ? "
                            "AND category = 'disciplines' AND line_id = ?",
                            (payload.parent_id, payload.scope.line_id),
                        ).fetchone()
                        if parent is None or parent["parent_id"] is not None or payload.parent_id == item_id:
                            raise BusinessError(
                                "父责任专业不存在或不能作为自身的父级",
                                "WORKSPACE_CATALOG_PARENT_INVALID",
                                status_code=422,
                            )
                if item_id is None:
                    item_id = uuid4().hex
                    connection.execute(
                        """INSERT INTO workspace_catalog_items
                        (id, category, line_id, profession_id, project_id, code, name,
                         description, sort_order, is_enabled, parent_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            item_id,
                            payload.category,
                            payload.scope.line_id,
                            payload.scope.profession_id,
                            project_id,
                            payload.code,
                            payload.name,
                            payload.description,
                            payload.sort_order,
                            int(payload.is_enabled),
                            payload.parent_id,
                        ),
                    )
                else:
                    update_scope = "id = ? AND category = ? AND line_id = ?"
                    update_params: list[Any] = [
                        payload.code,
                        payload.name,
                        payload.description,
                        payload.sort_order,
                        int(payload.is_enabled),
                        item_id,
                        payload.category,
                        payload.scope.line_id,
                    ]
                    if not shared_by_line:
                        update_scope += " AND profession_id = ? AND project_id = ?"
                        update_params.extend([payload.scope.profession_id, payload.scope.project_id])
                    cursor = connection.execute(
                        f"""UPDATE workspace_catalog_items SET code = ?, name = ?, description = ?,
                        sort_order = ?, is_enabled = ?, parent_id = ?,
                        updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        WHERE {update_scope}""",
                        [*update_params[:5], payload.parent_id, *update_params[5:]],
                    )
                    if cursor.rowcount == 0:
                        raise BusinessError(
                            "配置项目不存在或不属于当前范围",
                            "WORKSPACE_CATALOG_NOT_FOUND",
                            status_code=404,
                        )
                row = connection.execute("SELECT * FROM workspace_catalog_items WHERE id = ?", (item_id,)).fetchone()
                return self._catalog_item(row)
        except sqlite3.IntegrityError as exc:
            raise BusinessError("同一范围下的名称或编码已存在", "WORKSPACE_CATALOG_EXISTS", status_code=409) from exc

    def create_stations_batch(self, payload: WorkspaceStationsBatchWriteRequest) -> list[dict[str, Any]]:
        """Create several line-shared stations in one transaction."""
        self.ensure_schema()
        with closing(self._connect()) as validation:
            line = validation.execute(
                "SELECT 1 FROM workspace_lines WHERE id = ? AND is_enabled = 1",
                (payload.scope.line_id,),
            ).fetchone()
        if line is None:
            raise BusinessError("线路不存在或已停用", "WORKSPACE_SCOPE_NOT_FOUND", status_code=404)
        names = [name.strip() for name in payload.names]
        if len({name.casefold() for name in names}) != len(names):
            raise BusinessError("站点名称重复，请修改后再保存", "WORKSPACE_CATALOG_EXISTS", status_code=409)
        try:
            with closing(self._connect()) as connection, connection:
                created = []
                for index, name in enumerate(names):
                    duplicate = connection.execute(
                        """SELECT 1 FROM workspace_catalog_items
                        WHERE category = 'stations' AND line_id = ?
                        AND (name = ? COLLATE NOCASE OR code = ? COLLATE NOCASE)""",
                        (payload.scope.line_id, name, name),
                    ).fetchone()
                    if duplicate:
                        raise BusinessError(
                            f"站点“{name}”已存在，未新增任何站点",
                            "WORKSPACE_CATALOG_EXISTS",
                            status_code=409,
                        )
                    item_id = uuid4().hex
                    connection.execute(
                        """INSERT INTO workspace_catalog_items
                        (id, category, line_id, profession_id, project_id, code, name,
                         description, sort_order, is_enabled)
                        VALUES (?, 'stations', ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            item_id,
                            payload.scope.line_id,
                            payload.scope.profession_id,
                            payload.scope.project_id,
                            name,
                            name,
                            payload.description,
                            payload.sort_order + index,
                            int(payload.is_enabled),
                        ),
                    )
                    row = connection.execute(
                        "SELECT * FROM workspace_catalog_items WHERE id = ?", (item_id,)
                    ).fetchone()
                    created.append(self._catalog_item(row))
                return created
        except sqlite3.IntegrityError as exc:
            raise BusinessError(
                "站点名称重复或已存在，未新增任何站点", "WORKSPACE_CATALOG_EXISTS", status_code=409
            ) from exc

    @staticmethod
    def _catalog_item(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "category": row["category"],
            "lineId": int(row["line_id"]),
            "professionId": int(row["profession_id"]),
            "projectId": int(row["project_id"]),
            "code": row["code"],
            "name": row["name"],
            "parentId": row["parent_id"],
            "description": row["description"],
            "sortOrder": int(row["sort_order"]),
            "isEnabled": bool(row["is_enabled"]),
        }

    @staticmethod
    def _seed_defaults(connection: sqlite3.Connection) -> None:
        connection.execute("INSERT OR IGNORE INTO workspace_lines(code, name, sort_order) VALUES ('9', '9号线', 9)")
        connection.execute(
            "INSERT OR IGNORE INTO workspace_professions(code, name, sort_order) VALUES ('ZDH', '自动化', 1)"
        )
        profession = connection.execute(
            "SELECT id FROM workspace_professions WHERE code = 'ZDH' COLLATE NOCASE"
        ).fetchone()
        line = connection.execute("SELECT id FROM workspace_lines WHERE code = '9' COLLATE NOCASE").fetchone()
        if profession and line:
            legacy = connection.execute(
                "SELECT id FROM workspace_projects WHERE line_id = ? "
                "AND code = 'FAS' COLLATE NOCASE",
                (int(line[0]),),
            ).fetchone()
            t19 = connection.execute(
                "SELECT id FROM workspace_projects WHERE line_id = ? "
                "AND code = 'T19' COLLATE NOCASE",
                (int(line[0]),),
            ).fetchone()
            if legacy and not t19:
                # Preserve the old FAS processing engine and every attached
                # configuration while adopting the agreed project identifier.
                connection.execute(
                    "UPDATE workspace_projects SET code = 'T19', name = 'FAS系统测试' WHERE id = ?",
                    (int(legacy[0]),),
                )
            if not t19:
                connection.execute(
                    """INSERT INTO workspace_projects(
                        line_id, profession_id, code, name, description, engine_code, sort_order
                    ) VALUES (?, ?, 'T19', 'FAS系统测试', '火灾自动报警系统联调', 'T19', 1)""",
                    (int(line[0]), int(profession[0])),
                )
        connection.execute(
            "UPDATE workspace_projects SET line_id = COALESCE(line_id, ?) WHERE line_id IS NULL",
            (int(line[0]) if line else 1,),
        )
        discipline_groups = {
            "自动化": ("BAS", "FAS", "ACS", "IScS", "门禁", "安防", "防淹门", "ISP", "安检", "人防门", "智慧车站"),
            "风水电-正线": ("给排水", "通风空调", "低压配电"),
            "门梯": ("垂直电梯", "自动扶梯", "站台门"),
            "风水电-场段": ("通风空调-场段", "给排水-场段", "动照-场段"),
        }
        for parent_name, child_names in discipline_groups.items():
            parent = connection.execute(
                "SELECT id FROM workspace_professions WHERE name = ? COLLATE NOCASE", (parent_name,)
            ).fetchone()
            if parent:
                for child_name in child_names:
                    connection.execute(
                        "UPDATE workspace_professions SET parent_id = ? WHERE name = ? COLLATE NOCASE AND id <> ?",
                        (int(parent[0]), child_name, int(parent[0])),
                    )
        lines = connection.execute("SELECT id FROM workspace_lines").fetchall()
        for line_row in lines:
            for parent_name, child_names in discipline_groups.items():
                parent = connection.execute(
                "SELECT id FROM workspace_catalog_items WHERE category = 'disciplines' "
                "AND line_id = ? AND name = ? COLLATE NOCASE",
                    (int(line_row[0]), parent_name),
                ).fetchone()
                if not parent:
                    continue
                for child_name in child_names:
                    connection.execute(
                        "UPDATE workspace_catalog_items SET parent_id = ? "
                        "WHERE category = 'disciplines' AND line_id = ? "
                        "AND name = ? COLLATE NOCASE AND id <> ?",
                        (str(parent[0]), int(line_row[0]), child_name, str(parent[0])),
                    )

    def _row_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    def list_lines(self, include_disabled: bool = False) -> list[dict[str, Any]]:
        self.ensure_schema()
        with closing(self._connect()) as c:
            query = "SELECT * FROM workspace_lines"
            if not include_disabled:
                query += " WHERE is_enabled = 1"
            query += " ORDER BY sort_order, id"
            return [self._line(row) for row in c.execute(query).fetchall()]

    def list_professions(self, include_disabled: bool = False) -> list[dict[str, Any]]:
        self.ensure_schema()
        with closing(self._connect()) as c:
            query = "SELECT * FROM workspace_professions"
            if not include_disabled:
                query += " WHERE is_enabled = 1"
            query += " ORDER BY sort_order, id"
            return [self._profession(row) for row in c.execute(query).fetchall()]

    def list_projects(
        self,
        profession_id: int | None = None,
        include_disabled: bool = False,
        line_id: int | None = None,
    ) -> list[dict[str, Any]]:
        self.ensure_schema()
        with closing(self._connect()) as c:
            clauses: list[str] = []
            params: list[Any] = []
            # Projects belong to a line. profession_id is retained on the
            # record for compatibility with older data and callers.
            if line_id:
                clauses.append("line_id = ?")
                params.append(line_id)
            if not include_disabled:
                clauses.append("is_enabled = 1")
            query = "SELECT * FROM workspace_projects" + (" WHERE " + " AND ".join(clauses) if clauses else "")
            query += " ORDER BY sort_order, code COLLATE NOCASE, id"
            return [self._project(row) for row in c.execute(query, params).fetchall()]

    def create_line(self, payload: LineWriteRequest) -> dict[str, Any]:
        self.ensure_schema()
        try:
            with closing(self._connect()) as c, c:
                cur = c.execute(
                    "INSERT INTO workspace_lines(code, name, sort_order, is_enabled) VALUES (?, ?, ?, ?)",
                    (payload.code, payload.name, payload.sort_order, int(payload.is_enabled)),
                )
                return self._line(c.execute("SELECT * FROM workspace_lines WHERE id = ?", (cur.lastrowid,)).fetchone())
        except sqlite3.IntegrityError as exc:
            raise BusinessError("线路编码或名称已存在", "WORKSPACE_LINE_EXISTS", status_code=409) from exc

    def update_line(self, line_id: int, payload: LineWriteRequest) -> dict[str, Any]:
        self.ensure_schema()
        try:
            with closing(self._connect()) as c, c:
                cursor = c.execute(
                    "UPDATE workspace_lines SET code = ?, name = ?, sort_order = ?, is_enabled = ?, "
                    "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                    (
                        payload.code,
                        payload.name,
                        payload.sort_order,
                        int(payload.is_enabled),
                        line_id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise BusinessError("线路不存在", "WORKSPACE_LINE_NOT_FOUND", status_code=404)
                return self._line(c.execute("SELECT * FROM workspace_lines WHERE id = ?", (line_id,)).fetchone())
        except sqlite3.IntegrityError as exc:
            raise BusinessError("线路编码或名称已存在", "WORKSPACE_LINE_EXISTS", status_code=409) from exc

    def create_profession(self, payload: ProfessionWriteRequest) -> dict[str, Any]:
        self.ensure_schema()
        try:
            with closing(self._connect()) as c, c:
                self._ensure_profession_unique(c, payload)
                cur = c.execute(
                    "INSERT INTO workspace_professions(code, name, parent_id, sort_order, is_enabled) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (payload.code, payload.name, payload.parent_id, payload.sort_order, int(payload.is_enabled)),
                )
                return self._profession(
                    c.execute("SELECT * FROM workspace_professions WHERE id = ?", (cur.lastrowid,)).fetchone()
                )
        except sqlite3.IntegrityError as exc:
            raise BusinessError("专业编码或名称已存在", "WORKSPACE_PROFESSION_EXISTS", status_code=409) from exc

    def create_professions(self, payload: ProfessionBatchWriteRequest) -> list[dict[str, Any]]:
        """Create a set of professions atomically so partial imports are impossible."""
        self.ensure_schema()
        try:
            with closing(self._connect()) as connection, connection:
                created = []
                for item in payload.professions:
                    self._ensure_profession_unique(connection, item)
                    cursor = connection.execute(
                        "INSERT INTO workspace_professions(code, name, parent_id, sort_order, is_enabled) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (item.code, item.name, item.parent_id, item.sort_order, int(item.is_enabled)),
                    )
                    row = connection.execute(
                        "SELECT * FROM workspace_professions WHERE id = ?", (cursor.lastrowid,)
                    ).fetchone()
                    created.append(self._profession(row))
                return created
        except sqlite3.IntegrityError as exc:
            raise BusinessError(
                "专业编码或名称已存在，未新增任何专业", "WORKSPACE_PROFESSION_EXISTS", status_code=409
            ) from exc

    @staticmethod
    def _ensure_profession_unique(
        connection: sqlite3.Connection,
        payload: ProfessionWriteRequest,
        profession_id: int | None = None,
    ) -> None:
        if payload.parent_id is not None:
            parent = connection.execute(
                "SELECT parent_id FROM workspace_professions WHERE id = ?",
                (payload.parent_id,),
            ).fetchone()
            if parent is None or (profession_id is not None and payload.parent_id == profession_id):
                raise BusinessError(
                    "父级专业不存在或不能作为自身的父级",
                    "WORKSPACE_PROFESSION_PARENT_INVALID",
                    status_code=422,
                )
            if parent["parent_id"] is not None:
                raise BusinessError(
                    "专业层级仅支持父级和子级两层",
                    "WORKSPACE_PROFESSION_PARENT_INVALID",
                    status_code=422,
                )
            has_children = connection.execute(
                "SELECT 1 FROM workspace_professions WHERE parent_id = ? LIMIT 1",
                (profession_id,),
            ).fetchone() if profession_id is not None else None
            if has_children:
                raise BusinessError(
                    "该专业已有子专业，不能再设置为子专业",
                    "WORKSPACE_PROFESSION_PARENT_INVALID",
                    status_code=422,
                )
        query = "SELECT 1 FROM workspace_professions WHERE (code = ? COLLATE NOCASE OR name = ? COLLATE NOCASE)"
        params: list[Any] = [payload.code, payload.name]
        if profession_id is not None:
            query += " AND id != ?"
            params.append(profession_id)
        if connection.execute(query, params).fetchone():
            raise BusinessError("专业编码或名称已存在", "WORKSPACE_PROFESSION_EXISTS", status_code=409)

    def update_profession(self, profession_id: int, payload: ProfessionWriteRequest) -> dict[str, Any]:
        self.ensure_schema()
        try:
            with closing(self._connect()) as c, c:
                self._ensure_profession_unique(c, payload, profession_id)
                cursor = c.execute(
                    "UPDATE workspace_professions SET code = ?, name = ?, parent_id = ?, "
                    "sort_order = ?, is_enabled = ?, "
                    "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                    (
                        payload.code,
                        payload.name,
                        payload.parent_id,
                        payload.sort_order,
                        int(payload.is_enabled),
                        profession_id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise BusinessError("专业不存在", "WORKSPACE_PROFESSION_NOT_FOUND", status_code=404)
                return self._profession(
                    c.execute("SELECT * FROM workspace_professions WHERE id = ?", (profession_id,)).fetchone()
                )
        except sqlite3.IntegrityError as exc:
            raise BusinessError("专业编码或名称已存在", "WORKSPACE_PROFESSION_EXISTS", status_code=409) from exc

    def create_project(self, payload: ProjectWriteRequest) -> dict[str, Any]:
        self.ensure_schema()
        engine_code = payload.engine_code.strip().upper() or payload.code.strip().upper()
        try:
            with closing(self._connect()) as c, c:
                cur = c.execute(
                    """INSERT INTO workspace_projects(
                    line_id, profession_id, code, name, description, engine_code, sort_order, is_enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        payload.line_id or 1,
                        payload.profession_id,
                        payload.code,
                        payload.name,
                        payload.description,
                        engine_code,
                        payload.sort_order,
                        int(payload.is_enabled),
                    ),
                )
                return self._project(
                    c.execute("SELECT * FROM workspace_projects WHERE id = ?", (cur.lastrowid,)).fetchone()
                )
        except sqlite3.IntegrityError as exc:
            raise BusinessError("该线路下的联调项目编码已存在", "WORKSPACE_PROJECT_EXISTS", status_code=409) from exc

    def update_project(self, project_id: int, payload: ProjectWriteRequest) -> dict[str, Any]:
        self.ensure_schema()
        try:
            with closing(self._connect()) as c, c:
                existing = c.execute("SELECT * FROM workspace_projects WHERE id = ?", (project_id,)).fetchone()
                if existing is None:
                    raise BusinessError("联调项目不存在", "WORKSPACE_PROJECT_NOT_FOUND", status_code=404)
                previous_code = str(existing["code"] or "")
                previous_engine_code = str(existing["engine_code"] or "")
                engine_code = payload.engine_code.strip().upper() or payload.code.strip().upper()
                if (
                    previous_engine_code.casefold() == previous_code.casefold()
                    and payload.code.casefold() != previous_code.casefold()
                ):
                    engine_code = payload.code.strip().upper()
                new_line_id = payload.line_id or 1
                if int(existing["line_id"] or 1) != int(new_line_id):
                    # Keep all project-owned records attached when an authorized
                    # manager changes the project's scope. Config business IDs
                    # stay stable because they are persistent user-facing IDs.
                    for table in (
                        "workspace_configs",
                        "workspace_catalog_items",
                        "workspace_debug_items",
                    ):
                        c.execute(
                            f"UPDATE {table} SET line_id = ? WHERE project_id = ?",
                            (new_line_id, project_id),
                        )
                cursor = c.execute(
                    """UPDATE workspace_projects
                    SET line_id = ?, profession_id = ?, code = ?, name = ?, description = ?,
                        engine_code = ?, sort_order = ?, is_enabled = ?,
                        updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    WHERE id = ?""",
                    (
                        new_line_id,
                        payload.profession_id,
                        payload.code,
                        payload.name,
                        payload.description,
                        engine_code,
                        payload.sort_order,
                        int(payload.is_enabled),
                        project_id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise BusinessError("联调项目不存在", "WORKSPACE_PROJECT_NOT_FOUND", status_code=404)
                return self._project(
                    c.execute("SELECT * FROM workspace_projects WHERE id = ?", (project_id,)).fetchone()
                )
        except sqlite3.IntegrityError as exc:
            raise BusinessError("该线路下的联调项目编码已存在", "WORKSPACE_PROJECT_EXISTS", status_code=409) from exc

    def get_scope(self, selection: ScopeSelection) -> tuple[sqlite3.Row, sqlite3.Row, sqlite3.Row]:
        self.ensure_schema()
        with closing(self._connect()) as c:
            line = c.execute(
                "SELECT * FROM workspace_lines WHERE id = ? AND is_enabled = 1",
                (selection.line_id,),
            ).fetchone()
            profession = c.execute(
                "SELECT * FROM workspace_professions WHERE id = ? AND is_enabled = 1",
                (selection.profession_id,),
            ).fetchone()
            project = c.execute(
                "SELECT * FROM workspace_projects WHERE id = ? AND line_id = ? AND is_enabled = 1",
                (selection.project_id, selection.line_id),
            ).fetchone()
        if not line or not profession or not project:
            raise BusinessError("线路、专业或联调项目不存在", "WORKSPACE_SCOPE_NOT_FOUND", status_code=404)
        return line, profession, project

    def list_configs(self, selection: ScopeSelection, include_disabled: bool = False) -> list[dict[str, Any]]:
        self.get_scope(selection)
        with closing(self._connect()) as c:
            query = "SELECT * FROM workspace_configs WHERE line_id = ? AND profession_id = ? AND project_id = ?"
            params: list[Any] = [selection.line_id, selection.profession_id, selection.project_id]
            if selection.debug_subitem_id:
                query += (
                    " AND EXISTS (SELECT 1 FROM workspace_config_classifications cc "
                    "WHERE cc.config_id = workspace_configs.id AND cc.debug_subitem_id = ?)"
                )
                params.append(selection.debug_subitem_id)
            if selection.debug_division_id:
                query += (
                    " AND EXISTS (SELECT 1 FROM workspace_config_classifications cc "
                    "WHERE cc.config_id = workspace_configs.id AND cc.debug_division_id = ?)"
                )
                params.append(selection.debug_division_id)
            if not include_disabled:
                query += " AND is_enabled = 1"
            query += " ORDER BY business_id"
            rows = c.execute(query, params).fetchall()
            return [self._config(c, row) for row in rows]

    def list_config_copy_candidates(
        self, target: ScopeSelection
    ) -> list[dict[str, Any]]:
        """Load copy-dialog metadata in one lightweight query.

        The dialog only needs identifiers and labels. Avoid hydrating every
        rule tree (steps, results and aliases), which previously caused a
        query per project/profession and several child queries per rule.
        """
        self.get_scope(target)
        self.ensure_schema()
        query = """
            SELECT c.id, c.business_id, c.line_id, c.profession_id, c.project_id,
                   c.debug_subitem_id, c.debug_division_id, c.config_code,
                   c.device_type, c.description,
                   l.name AS source_line_name,
                   p.name AS source_profession_name,
                   j.code AS source_project_code,
                   j.name AS source_project_name
            FROM workspace_configs AS c
            JOIN workspace_lines AS l ON l.id = c.line_id AND l.is_enabled = 1
            JOIN workspace_professions AS p ON p.id = c.profession_id AND p.is_enabled = 1
            JOIN workspace_projects AS j
              ON j.id = c.project_id AND j.line_id = c.line_id AND j.is_enabled = 1
            WHERE c.is_enabled = 1
              AND NOT (
                c.line_id = ? AND c.profession_id = ? AND c.project_id = ?
              )
            ORDER BY c.line_id, j.sort_order, j.code COLLATE NOCASE,
                     c.profession_id, c.business_id
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(
                query,
                (target.line_id, target.profession_id, target.project_id),
            ).fetchall()
        return [
            {
                "id": str(row["id"]),
                "businessId": str(row["business_id"]),
                "lineId": int(row["line_id"]),
                "professionId": int(row["profession_id"]),
                "projectId": int(row["project_id"]),
                "debugSubitemId": row["debug_subitem_id"],
                "debugDivisionId": row["debug_division_id"],
                "configCode": str(row["config_code"]),
                "deviceType": str(row["device_type"]),
                "description": str(row["description"]),
                "isEnabled": True,
                "sourceLineName": str(row["source_line_name"]),
                "sourceProfessionName": str(row["source_profession_name"]),
                "sourceProjectCode": str(row["source_project_code"]),
                "sourceProjectName": str(row["source_project_name"]),
            }
            for row in rows
        ]

    def create_config(self, payload: ConfigWriteRequest, user_id: int) -> dict[str, Any]:
        line, profession, project = self.get_scope(payload.scope)
        self.ensure_schema()
        self._validate_debug_classification(
            payload.scope,
            payload.scope.debug_subitem_id or payload.debug_subitem_id,
            payload.scope.debug_division_id or payload.debug_division_id,
        )
        config_id = uuid4().hex
        business_id = self._next_business_id(line, profession, project)
        try:
            with closing(self._connect()) as c, c:
                c.execute(
                    """INSERT INTO workspace_configs(
                    id, business_id, line_id, profession_id, project_id, config_code,
                    debug_subitem_id, debug_division_id, device_type, description, is_enabled, created_by, updated_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        config_id,
                        business_id,
                        payload.scope.line_id,
                        payload.scope.profession_id,
                        payload.scope.project_id,
                        payload.config_code,
                        payload.debug_subitem_id or payload.scope.debug_subitem_id,
                        payload.debug_division_id or payload.scope.debug_division_id,
                        payload.device_type,
                        payload.description,
                        int(payload.is_enabled),
                        user_id,
                        user_id,
                    ),
                )
                self._replace_steps(c, config_id, payload.steps)
                self._add_alias(c, config_id, payload.config_code, True)
                c.execute("DELETE FROM workspace_config_classifications WHERE config_id = ?", (config_id,))
                self._save_config_classification(
                    c,
                    config_id,
                    payload.scope.debug_subitem_id or payload.debug_subitem_id,
                    payload.scope.debug_division_id or payload.debug_division_id,
                )
                return self._config(
                    c,
                    c.execute("SELECT * FROM workspace_configs WHERE id = ?", (config_id,)).fetchone(),
                )
        except sqlite3.IntegrityError as exc:
            raise BusinessError(
                "当前线路、专业和项目下的联调配置编码已存在",
                "WORKSPACE_CONFIG_EXISTS",
                status_code=409,
            ) from exc

    def update_config(self, config_id: str, payload: ConfigWriteRequest, user_id: int) -> dict[str, Any]:
        self.get_scope(payload.scope)
        self.ensure_schema()
        self._validate_debug_classification(
            payload.scope,
            payload.scope.debug_subitem_id or payload.debug_subitem_id,
            payload.scope.debug_division_id or payload.debug_division_id,
        )
        with closing(self._connect()) as c, c:
            old = c.execute("SELECT * FROM workspace_configs WHERE id = ?", (config_id,)).fetchone()
            if old is None:
                raise BusinessError("联调配置不存在", "WORKSPACE_CONFIG_NOT_FOUND", status_code=404)
            if (
                int(old["line_id"]) != payload.scope.line_id
                or int(old["profession_id"]) != payload.scope.profession_id
                or int(old["project_id"]) != payload.scope.project_id
            ):
                raise BusinessError(
                    "配置不能移动到其他线路或专业",
                    "WORKSPACE_CONFIG_SCOPE_IMMUTABLE",
                    status_code=409,
                )
            snapshot = self._config(c, old)
            revision = int(old["revision"]) + 1
            c.execute(
                """INSERT INTO workspace_config_history(
                    config_id, revision, snapshot, changed_by) VALUES (?, ?, ?, ?)""",
                (config_id, revision, json.dumps(snapshot, ensure_ascii=False), user_id),
            )
            try:
                c.execute(
                    """UPDATE workspace_configs SET config_code = ?, debug_subitem_id = ?,
                        debug_division_id = ?, device_type = ?, description = ?, is_enabled = ?,
                        revision = ?, updated_by = ?,
                        updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?""",
                    (
                        payload.config_code,
                        payload.debug_subitem_id or payload.scope.debug_subitem_id,
                        payload.debug_division_id or payload.scope.debug_division_id,
                        payload.device_type,
                        payload.description,
                        int(payload.is_enabled),
                        revision,
                        user_id,
                        config_id,
                    ),
                )
                self._replace_steps(c, config_id, payload.steps)
                self._add_alias(c, config_id, payload.config_code, True)
                c.execute("DELETE FROM workspace_config_classifications WHERE config_id = ?", (config_id,))
                self._save_config_classification(
                    c,
                    config_id,
                    payload.scope.debug_subitem_id or payload.debug_subitem_id,
                    payload.scope.debug_division_id or payload.debug_division_id,
                )
            except sqlite3.IntegrityError as exc:
                raise BusinessError(
                    "当前范围内的联调配置编码已存在", "WORKSPACE_CONFIG_EXISTS", status_code=409
                ) from exc
            return self._config(
                c,
                c.execute("SELECT * FROM workspace_configs WHERE id = ?", (config_id,)).fetchone(),
            )

    def copy_configs(self, payload: ConfigCopyRequest | BatchConfigCopyRequest, user_id: int) -> list[dict[str, Any]]:
        ids = [payload.source_config_id] if isinstance(payload, ConfigCopyRequest) else payload.source_config_ids
        result: list[dict[str, Any]] = []
        target_subitems: list[dict[str, Any]] | None = None
        target_divisions: dict[str, list[dict[str, Any]]] = {}
        target_scope = ScopeSelection(
            lineId=payload.target.line_id,
            professionId=payload.target.profession_id,
            projectId=payload.target.project_id,
        )
        self.get_scope(target_scope)
        target_subitems = self.list_debug_items(target_scope, "debug_subitems", None, True)
        target_subitem_by_name = {item["name"].casefold(): item for item in target_subitems}
        for source_id in ids:
            source = self.get_config(source_id, include_disabled=True)
            if source is None:
                raise BusinessError("待复制的联调配置不存在", "WORKSPACE_CONFIG_NOT_FOUND", status_code=404)
            with closing(self._connect()) as connection:
                classifications = connection.execute(
                    """SELECT debug_subitem_id, debug_division_id
                    FROM workspace_config_classifications WHERE config_id = ?""",
                    (source_id,),
                ).fetchall()
                if not classifications and source.get("debugSubitemId"):
                    classifications = [{
                        "debug_subitem_id": source["debugSubitemId"],
                        "debug_division_id": source.get("debugDivisionId"),
                    }]
                for classification in classifications:
                    subitem = connection.execute(
                        "SELECT name FROM workspace_debug_items WHERE id = ?",
                        (classification["debug_subitem_id"],),
                    ).fetchone()
                    if subitem is None or subitem["name"].casefold() not in target_subitem_by_name:
                        missing_name = subitem["name"] if subitem else "未知调试子项"
                        raise BusinessError(
                            f"目标项目缺少调试子项“{missing_name}”，请先复制调试子项和分项",
                            "WORKSPACE_COPY_DEBUG_HIERARCHY_REQUIRED",
                            status_code=409,
                        )
        for source_id in ids:
            source = self.get_config(source_id, include_disabled=True)
            if source is None:
                raise BusinessError("待复制的联调配置不存在", "WORKSPACE_CONFIG_NOT_FOUND", status_code=404)
            target_scope = ScopeSelection(
                lineId=payload.target.line_id,
                professionId=payload.target.profession_id,
                projectId=payload.target.project_id,
            )
            self.get_scope(target_scope)
            with closing(self._connect()) as connection:
                classifications = connection.execute(
                    """SELECT debug_subitem_id, debug_division_id
                    FROM workspace_config_classifications WHERE config_id = ?
                    ORDER BY debug_subitem_id, debug_division_id""",
                    (source_id,),
                ).fetchall()
                if not classifications and source.get("debugSubitemId"):
                    classifications = [
                        {
                            "debug_subitem_id": source["debugSubitemId"],
                            "debug_division_id": source.get("debugDivisionId"),
                        }
                    ]
                source_items = {
                    str(row["id"]): row
                    for row in connection.execute(
                        """SELECT id, category, name, description, sort_order
                        FROM workspace_debug_items WHERE id IN (
                            SELECT debug_subitem_id FROM workspace_config_classifications WHERE config_id = ?
                            UNION SELECT debug_division_id FROM workspace_config_classifications WHERE config_id = ?
                        )""",
                        (source_id, source_id),
                    ).fetchall()
                }
                if not source_items and source.get("debugSubitemId"):
                    rows = connection.execute(
                        """SELECT id, category, name, description, sort_order
                        FROM workspace_debug_items WHERE id IN (?, ?)""",
                        (source["debugSubitemId"], source.get("debugDivisionId")),
                    ).fetchall()
                    source_items = {str(row["id"]): row for row in rows}

            mapped_classifications: list[tuple[str, str | None]] = []
            if not classifications and len(target_subitems) == 1:
                mapped_classifications.append((target_subitems[0]["id"], None))
            for classification in classifications:
                source_subitem = source_items.get(str(classification["debug_subitem_id"]))
                if source_subitem is None or source_subitem["category"] != "debug_subitems":
                    continue
                if target_subitems is None:
                    target_subitems = self.list_debug_items(target_scope, "debug_subitems", None, True)
                target_subitem = next(
                    (item for item in target_subitems if item["name"].casefold() == source_subitem["name"].casefold()),
                    None,
                )
                if target_subitem is None:
                    raise BusinessError(
                        f"目标项目缺少调试子项“{source_subitem['name']}”，请先复制调试子项和分项",
                        "WORKSPACE_COPY_DEBUG_HIERARCHY_REQUIRED",
                        status_code=409,
                    )

                target_division_id = None
                source_division_id = classification["debug_division_id"]
                source_division = source_items.get(str(source_division_id)) if source_division_id else None
                if source_division is not None and source_division["category"] == "debug_divisions":
                    if target_subitem["id"] not in target_divisions:
                        target_divisions[target_subitem["id"]] = self.list_debug_items(
                            target_scope, "debug_divisions", target_subitem["id"], True
                        )
                    target_division = next(
                        (
                            item
                            for item in target_divisions[target_subitem["id"]]
                            if item["name"].casefold() == source_division["name"].casefold()
                        ),
                        None,
                    )
                    if target_division is not None:
                        target_division_id = target_division["id"]
                mapped_classifications.append((target_subitem["id"], target_division_id))

            existing = next(
                (
                    item
                    for item in self.list_configs(target_scope, include_disabled=True)
                    if item["configCode"].casefold() == source["configCode"].casefold()
                ),
                None,
            )
            if existing:
                # Earlier copies may have created the config before its debug
                # hierarchy was copied. Re-copying repairs the classification
                # without replacing user-edited steps or results.
                if mapped_classifications:
                    primary_subitem_id, primary_division_id = mapped_classifications[0]
                    with closing(self._connect()) as connection, connection:
                        connection.execute(
                            "UPDATE workspace_configs SET debug_subitem_id = ?, debug_division_id = ? "
                            "WHERE id = ?",
                            (primary_subitem_id, primary_division_id, existing["id"]),
                        )
                        connection.execute(
                            "DELETE FROM workspace_config_classifications WHERE config_id = ?",
                            (existing["id"],),
                        )
                        for subitem_id, division_id in mapped_classifications:
                            self._save_config_classification(
                                connection, existing["id"], subitem_id, division_id
                            )
                    existing = self.get_config(existing["id"], include_disabled=True) or existing
                result.append(existing)
                continue
            primary_subitem_id, primary_division_id = (
                mapped_classifications[0] if mapped_classifications else (None, None)
            )
            classified_scope = ScopeSelection(
                lineId=target_scope.line_id,
                professionId=target_scope.profession_id,
                projectId=target_scope.project_id,
                debugSubitemId=primary_subitem_id,
                debugDivisionId=primary_division_id,
            )
            copied_payload = ConfigWriteRequest(
                scope=classified_scope,
                configCode=source["configCode"],
                deviceType=source["deviceType"],
                description=source["description"],
                steps=[
                    ConfigStepWriteRequest(
                        description=step["description"],
                        ratioChange=step["ratioChange"],
                        sortOrder=step["sortOrder"],
                        isEnabled=step["isEnabled"],
                        results=[
                            ConfigResultWriteRequest(
                                description=result["description"],
                                responsibleDisciplines=result.get("responsibleDisciplines", []),
                            )
                            for result in step["results"]
                        ],
                    )
                    for step in source["steps"]
                ],
                isEnabled=source["isEnabled"],
                debugSubitemId=primary_subitem_id,
                debugDivisionId=primary_division_id,
            )
            copied = self.create_config(copied_payload, user_id)
            if mapped_classifications:
                with closing(self._connect()) as connection, connection:
                    for subitem_id, division_id in mapped_classifications:
                        self._save_config_classification(connection, copied["id"], subitem_id, division_id)
            result.append(self.get_config(copied["id"], include_disabled=True) or copied)
        return result

    def disable_config(self, config_id: str, enabled: bool, user_id: int) -> dict[str, Any]:
        self.ensure_schema()
        with closing(self._connect()) as c, c:
            row = c.execute("SELECT * FROM workspace_configs WHERE id = ?", (config_id,)).fetchone()
            if row is None:
                raise BusinessError("联调配置不存在", "WORKSPACE_CONFIG_NOT_FOUND", status_code=404)
            c.execute(
                "UPDATE workspace_configs SET is_enabled = ?, updated_by = ?, revision = revision + 1, "
                "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                (int(enabled), user_id, config_id),
            )
            return self._config(
                c,
                c.execute("SELECT * FROM workspace_configs WHERE id = ?", (config_id,)).fetchone(),
            )

    def list_debug_items(
        self,
        scope: ScopeSelection,
        category: str,
        parent_id: str | None = None,
        include_disabled: bool = False,
    ) -> list[dict[str, Any]]:
        self.get_scope(scope)
        self.ensure_schema()
        with closing(self._connect()) as c:
            query = """SELECT * FROM workspace_debug_items
                WHERE category = ? AND line_id = ? AND profession_id = ? AND project_id = ?
                  AND (parent_id = ? OR (parent_id IS NULL AND ? IS NULL))"""
            params: list[Any] = [
                category,
                scope.line_id,
                scope.profession_id,
                scope.project_id,
                parent_id,
                parent_id,
            ]
            if not include_disabled:
                query += " AND is_enabled = 1"
            query += " ORDER BY sort_order, name COLLATE NOCASE, id"
            return [self._debug_item(row) for row in c.execute(query, params).fetchall()]

    @staticmethod
    def _save_config_classification(
        connection: sqlite3.Connection,
        config_id: str,
        subitem_id: str | None,
        division_id: str | None,
    ) -> None:
        if not subitem_id:
            return
        connection.execute(
            "INSERT OR IGNORE INTO workspace_config_classifications("
            "config_id, debug_subitem_id, debug_division_id) VALUES (?, ?, ?)",
            (config_id, subitem_id, division_id),
        )

    def _validate_debug_classification(
        self, scope: ScopeSelection, subitem_id: str | None, division_id: str | None
    ) -> None:
        if not subitem_id:
            if division_id:
                raise BusinessError(
                    "选择调试分项时必须同时选择所属调试子项",
                    "WORKSPACE_DEBUG_CLASSIFICATION_REQUIRED",
                    status_code=422,
                )
            return
        with closing(self._connect()) as connection:
            if division_id:
                row = connection.execute(
                    """SELECT d.id FROM workspace_debug_items d
                JOIN workspace_debug_items s ON s.id = d.parent_id
                WHERE d.id = ? AND d.category = 'debug_divisions'
                  AND d.line_id = ? AND d.profession_id = ? AND d.project_id = ?
                  AND s.id = ? AND s.category = 'debug_subitems'
                  AND s.line_id = d.line_id AND s.profession_id = d.profession_id AND s.project_id = d.project_id""",
                    (division_id, scope.line_id, scope.profession_id, scope.project_id, subitem_id),
                ).fetchone()
            else:
                row = connection.execute(
                    """SELECT id FROM workspace_debug_items
                    WHERE id = ? AND category = 'debug_subitems'
                      AND line_id = ? AND profession_id = ? AND project_id = ?""",
                    (subitem_id, scope.line_id, scope.profession_id, scope.project_id),
                ).fetchone()
        if row is None:
            raise BusinessError(
                "选择的调试子项/分项不属于当前线路、专业和联调项目",
                "WORKSPACE_DEBUG_CLASSIFICATION_INVALID",
                status_code=422,
            )

    def save_debug_item(self, payload: DebugItemWriteRequest, item_id: str | None = None) -> dict[str, Any]:
        self.get_scope(payload.scope)
        if payload.category == "debug_divisions" and not payload.parent_id:
            raise BusinessError("调试分项必须归属于一个调试子项", "WORKSPACE_DEBUG_PARENT_REQUIRED", status_code=422)
        normalized_name = payload.name.strip()
        normalized_code = payload.code.strip()
        try:
            with closing(self._connect()) as c, c:
                if payload.category == "debug_divisions":
                    parent = c.execute(
                        """
                        SELECT id FROM workspace_debug_items
                        WHERE id = ? AND category = 'debug_subitems'
                          AND line_id = ? AND profession_id = ? AND project_id = ?
                        """,
                        (
                            payload.parent_id,
                            payload.scope.line_id,
                            payload.scope.profession_id,
                            payload.scope.project_id,
                        ),
                    ).fetchone()
                    if parent is None:
                        raise BusinessError(
                            "所属调试子项不存在或不属于当前线路、专业和项目",
                            "WORKSPACE_DEBUG_PARENT_INVALID",
                            status_code=422,
                        )
                # Check the scope explicitly before writing so a stale/disabled
                # record produces the same useful conflict response as SQLite's
                # unique constraint, without conflating unrelated constraints.
                conflict = c.execute(
                    """SELECT id FROM workspace_debug_items
                    WHERE category = ? AND line_id = ? AND profession_id = ? AND project_id = ?
                      AND parent_id IS ?
                      AND (name = ? COLLATE NOCASE OR (code <> '' AND code = ? COLLATE NOCASE))
                      AND (? IS NULL OR id <> ?)
                    LIMIT 1""",
                    (
                        payload.category,
                        payload.scope.line_id,
                        payload.scope.profession_id,
                        payload.scope.project_id,
                        payload.parent_id if payload.category == "debug_divisions" else None,
                        normalized_name,
                        normalized_code,
                        item_id,
                        item_id,
                    ),
                ).fetchone()
                if conflict is not None:
                    raise BusinessError(
                        "同一调试层级下名称或编码已存在",
                        "WORKSPACE_DEBUG_EXISTS",
                        status_code=409,
                    )
                if item_id is None:
                    item_id = uuid4().hex
                    generated_code = (
                        f"{'DSI' if payload.category == 'debug_subitems' else 'DDI'}-{uuid4().hex[:12].upper()}"
                    )
                    parent_id = payload.parent_id if payload.category == "debug_divisions" else None
                    sort_order = c.execute(
                        """SELECT COALESCE(MAX(sort_order), 0) + 1 FROM workspace_debug_items
                        WHERE category = ? AND line_id = ? AND profession_id = ? AND project_id = ?
                          AND parent_id IS ?""",
                        (
                            payload.category,
                            payload.scope.line_id,
                            payload.scope.profession_id,
                            payload.scope.project_id,
                            parent_id,
                        ),
                    ).fetchone()[0]
                    c.execute(
                        """INSERT INTO workspace_debug_items(
                        id, category, line_id, profession_id, project_id, parent_id,
                        code, name, description, sort_order, is_enabled
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            item_id,
                            payload.category,
                            payload.scope.line_id,
                            payload.scope.profession_id,
                            payload.scope.project_id,
                            parent_id,
                            generated_code,
                            normalized_name,
                            payload.description,
                            sort_order,
                            int(payload.is_enabled),
                        ),
                    )
                else:
                    existing = c.execute("SELECT * FROM workspace_debug_items WHERE id = ?", (item_id,)).fetchone()
                    if existing is None:
                        raise BusinessError(
                            "调试分类不存在或不属于当前范围",
                            "WORKSPACE_DEBUG_NOT_FOUND",
                            status_code=404,
                        )
                    if (
                        existing["category"] != payload.category
                        or int(existing["line_id"]) != payload.scope.line_id
                        or int(existing["profession_id"]) != payload.scope.profession_id
                        or int(existing["project_id"]) != payload.scope.project_id
                    ):
                        raise BusinessError(
                            "调试分类不存在或不属于当前范围",
                            "WORKSPACE_DEBUG_NOT_FOUND",
                            status_code=404,
                        )
                    if payload.category == "debug_subitems":
                        parent_id = None
                    code = str(existing["code"])
                    if normalized_code and str(existing["code"]).casefold() != normalized_code.casefold():
                        raise BusinessError(
                            "调试子项/分项编码创建后不可修改，只能修改名称",
                            "WORKSPACE_DEBUG_CODE_IMMUTABLE",
                            status_code=409,
                        )
                    cursor = c.execute(
                        """UPDATE workspace_debug_items SET parent_id = ?, code = ?, name = ?,
                            description = ?, sort_order = ?, is_enabled = ?,
                        updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        WHERE id = ? AND category = ? AND line_id = ? AND profession_id = ? AND project_id = ?""",
                        (
                            parent_id if payload.category == "debug_subitems" else payload.parent_id,
                            code,
                            normalized_name,
                            payload.description,
                            payload.sort_order,
                            int(payload.is_enabled),
                            item_id,
                            payload.category,
                            payload.scope.line_id,
                            payload.scope.profession_id,
                            payload.scope.project_id,
                        ),
                    )
                    if cursor.rowcount == 0:
                        raise BusinessError(
                            "调试分类不存在或不属于当前范围",
                            "WORKSPACE_DEBUG_NOT_FOUND",
                            status_code=404,
                        )
                row = c.execute("SELECT * FROM workspace_debug_items WHERE id = ?", (item_id,)).fetchone()
                return self._debug_item(row)
        except sqlite3.IntegrityError as exc:
            # Keep a stable public error for legacy databases whose unique
            # indexes may differ from the current schema.
            raise BusinessError("同一调试层级下名称或编码已存在", "WORKSPACE_DEBUG_EXISTS", status_code=409) from exc

    def save_debug_items_batch(self, payload: DebugItemsBatchWriteRequest) -> list[dict[str, Any]]:
        self.get_scope(payload.scope)
        names = [name.strip() for name in payload.names if name.strip()]
        if not names:
            raise BusinessError("请至少输入一个名称", "WORKSPACE_DEBUG_NAMES_REQUIRED", status_code=422)
        normalized_names = [name.casefold() for name in names]
        if len(normalized_names) != len(set(normalized_names)):
            raise BusinessError(
                "本次输入中存在重复名称，请检查后再保存",
                "WORKSPACE_DEBUG_DUPLICATE_BATCH",
                status_code=409,
            )
        if payload.category == "debug_divisions" and not payload.parent_id:
            raise BusinessError(
                "新增分项时必须指定所属调试子项",
                "WORKSPACE_DEBUG_PARENT_REQUIRED",
                status_code=422,
            )

        self.ensure_schema()
        with closing(self._connect()) as c, c:
            if payload.category == "debug_divisions":
                parent = c.execute(
                    """SELECT id FROM workspace_debug_items
                    WHERE id = ? AND category = 'debug_subitems'
                      AND line_id = ? AND profession_id = ? AND project_id = ?""",
                    (payload.parent_id, payload.scope.line_id, payload.scope.profession_id, payload.scope.project_id),
                ).fetchone()
                if parent is None:
                    raise BusinessError(
                        "所属调试子项不存在或不属于当前线路、专业和项目",
                        "WORKSPACE_DEBUG_PARENT_INVALID",
                        status_code=422,
                    )
            parent_id = payload.parent_id if payload.category == "debug_divisions" else None
            placeholders = ",".join("?" for _ in normalized_names)
            conflicts = c.execute(
                f"""SELECT name FROM workspace_debug_items
                WHERE category = ? AND line_id = ? AND profession_id = ? AND project_id = ?
                  AND parent_id IS ? AND name COLLATE NOCASE IN ({placeholders})""",
                (
                    payload.category,
                    payload.scope.line_id,
                    payload.scope.profession_id,
                    payload.scope.project_id,
                    parent_id,
                    *names,
                ),
            ).fetchall()
            if conflicts:
                conflict_names = "、".join(str(row["name"]) for row in conflicts)
                raise BusinessError(
                    f"以下名称已存在：{conflict_names}",
                    "WORKSPACE_DEBUG_EXISTS",
                    status_code=409,
                )
            next_sort_order = c.execute(
                """SELECT COALESCE(MAX(sort_order), 0) + 1 FROM workspace_debug_items
                WHERE category = ? AND line_id = ? AND profession_id = ? AND project_id = ?
                  AND parent_id IS ?""",
                (
                    payload.category,
                    payload.scope.line_id,
                    payload.scope.profession_id,
                    payload.scope.project_id,
                    parent_id,
                ),
            ).fetchone()[0]
            created = []
            for offset, name in enumerate(names):
                item_id = uuid4().hex
                code_prefix = "DSI" if payload.category == "debug_subitems" else "DDI"
                code = f"{code_prefix}-{uuid4().hex[:12].upper()}"
                c.execute(
                    """INSERT INTO workspace_debug_items(
                    id, category, line_id, profession_id, project_id, parent_id,
                    code, name, description, sort_order, is_enabled
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (
                        item_id,
                        payload.category,
                        payload.scope.line_id,
                        payload.scope.profession_id,
                        payload.scope.project_id,
                        parent_id,
                        code,
                        name,
                        payload.description,
                        next_sort_order + offset,
                    ),
                )
                row = c.execute("SELECT * FROM workspace_debug_items WHERE id = ?", (item_id,)).fetchone()
                created.append(self._debug_item(row))
            return created

    def delete_debug_item(self, item_id: str, scope: ScopeSelection, category: str) -> None:
        self.get_scope(scope)
        self.ensure_schema()
        with closing(self._connect()) as c, c:
            item = c.execute(
                """SELECT * FROM workspace_debug_items
                WHERE id = ? AND category = ? AND line_id = ? AND profession_id = ? AND project_id = ?""",
                (item_id, category, scope.line_id, scope.profession_id, scope.project_id),
            ).fetchone()
            if item is None:
                raise BusinessError("调试分类不存在或不属于当前范围", "WORKSPACE_DEBUG_NOT_FOUND", status_code=404)

            ids = [item_id]
            if category == "debug_subitems":
                children = c.execute(
                    "SELECT id FROM workspace_debug_items WHERE category = 'debug_divisions' AND parent_id = ?",
                    (item_id,),
                ).fetchall()
                ids.extend(str(row["id"]) for row in children)
            placeholders = ",".join("?" for _ in ids)
            references = c.execute(
                f"""SELECT 1 FROM workspace_configs
                WHERE debug_subitem_id IN ({placeholders}) OR debug_division_id IN ({placeholders})
                UNION ALL
                SELECT 1 FROM workspace_config_classifications
                WHERE debug_subitem_id IN ({placeholders}) OR debug_division_id IN ({placeholders})
                LIMIT 1""",
                (*ids, *ids, *ids, *ids),
            ).fetchone()
            if references:
                raise BusinessError(
                    "该分类已被联调配置使用，不能删除；可以在编辑中停用",
                    "WORKSPACE_DEBUG_IN_USE",
                    status_code=409,
                )
            if category == "debug_subitems":
                c.execute("DELETE FROM workspace_debug_items WHERE parent_id = ?", (item_id,))
            c.execute("DELETE FROM workspace_debug_items WHERE id = ?", (item_id,))

    def set_debug_item_status(
        self, item_id: str, scope: ScopeSelection, category: str, enabled: bool
    ) -> dict[str, Any]:
        self.get_scope(scope)
        self.ensure_schema()
        with closing(self._connect()) as c, c:
            cursor = c.execute(
                """UPDATE workspace_debug_items SET is_enabled = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                WHERE id = ? AND category = ? AND line_id = ? AND profession_id = ? AND project_id = ?""",
                (
                    int(enabled),
                    item_id,
                    category,
                    scope.line_id,
                    scope.profession_id,
                    scope.project_id,
                ),
            )
            if cursor.rowcount == 0:
                raise BusinessError("调试分类不存在或不属于当前范围", "WORKSPACE_DEBUG_NOT_FOUND", status_code=404)
            return self._debug_item(
                c.execute("SELECT * FROM workspace_debug_items WHERE id = ?", (item_id,)).fetchone()
            )

    @staticmethod
    def _debug_item(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "category": str(row["category"]),
            "lineId": int(row["line_id"]),
            "professionId": int(row["profession_id"]),
            "projectId": int(row["project_id"]),
            "parentId": row["parent_id"],
            "code": str(row["code"]),
            "name": str(row["name"]),
            "description": str(row["description"]),
            "sortOrder": int(row["sort_order"]),
            "isEnabled": bool(row["is_enabled"]),
        }

    def import_configs(self, payload: ConfigImportRequest, user_id: int) -> list[dict[str, Any]]:
        """Import a flattened configuration sheet.

        Each row represents one expected result.  Rows are grouped by config
        code and step number, so one step can contain any number of results.
        ``步骤序号`` is preferred; for older sheets without that column, a
        non-empty operation-step description starts a step and an empty one
        continues the preceding step. Repeating the same description also
        continues the same step for backwards compatibility.
        """
        self.get_scope(payload.scope)
        discipline_names = {
            str(item["name"]).strip().casefold(): str(item["name"]).strip()
            for item in self.list_catalog_items(payload.scope, "disciplines")
        }
        grouped: dict[str, dict[str, Any]] = {}
        current_config_key = ""
        for row_number, raw_values in enumerate(payload.rows, start=2):
            raw = {str(key).replace("\ufeff", "").strip(): value for key, value in raw_values.items()}
            code = str(raw.get("联调配置编码", raw.get("configCode", ""))).strip()
            if code:
                current_config_key = code.casefold()
            elif current_config_key:
                code = grouped[current_config_key]["code"]
            else:
                raise BusinessError(
                    f"第 {row_number} 行没有联调配置编码，且前面没有可沿用的配置编码",
                    "WORKSPACE_IMPORT_INVALID",
                    status_code=422,
                )
            business_id = str(raw.get("业务显示ID", raw.get("businessId", ""))).strip()
            step_text = str(raw.get("操作步骤", raw.get("stepDescription", ""))).strip()
            result_text = str(raw.get("预期结果", raw.get("resultDescription", ""))).strip()
            discipline_text = str(
                raw.get(
                    "责任专业",
                    raw.get("responsibleDiscipline", raw.get("responsibleDisciplines", "")),
                )
                or ""
            ).strip()
            responsible_disciplines = [
                name.strip() for name in re.split(r"[,，、;；/]+", discipline_text) if name.strip()
            ]
            unknown_disciplines = [name for name in responsible_disciplines if name.casefold() not in discipline_names]
            if unknown_disciplines:
                raise BusinessError(
                    f"第 {row_number} 行的责任专业未在线路责任专业目录中配置：{'、'.join(unknown_disciplines)}",
                    "WORKSPACE_IMPORT_DISCIPLINE_INVALID",
                    status_code=422,
                )
            responsible_disciplines = list(
                dict.fromkeys(discipline_names[name.casefold()] for name in responsible_disciplines)
            )
            step_number_raw = raw.get(
                "步骤序号", raw.get("操作步骤序号", raw.get("stepOrder", raw.get("stepIndex", "")))
            )
            step_number_text = str(step_number_raw or "").strip()
            result_number_raw = raw.get("输出序号", raw.get("结果序号", raw.get("resultOrder", "")))
            result_number_text = str(result_number_raw or "").strip()
            if not code or not result_text:
                raise BusinessError(
                    f"第 {row_number} 行的联调配置编码和预期结果不能为空",
                    "WORKSPACE_IMPORT_INVALID",
                    status_code=422,
                )
            step_number = None
            if step_number_text:
                try:
                    step_number = int(step_number_text)
                except ValueError as error:
                    raise BusinessError(
                        f"第 {row_number} 行的步骤序号必须是正整数",
                        "WORKSPACE_IMPORT_INVALID",
                        status_code=422,
                    ) from error
                if step_number <= 0:
                    raise BusinessError(
                        f"第 {row_number} 行的步骤序号必须是正整数",
                        "WORKSPACE_IMPORT_INVALID",
                        status_code=422,
                    )
            if not step_text and not step_number_text:
                prior_steps = grouped.get(current_config_key, {}).get("steps", [])
                step_number_text = str(prior_steps[-1]["number"]) if prior_steps else "1"
            result_number = None
            if result_number_text:
                try:
                    result_number = int(result_number_text)
                except ValueError as error:
                    raise BusinessError(
                        f"第 {row_number} 行的输出序号必须是正整数",
                        "WORKSPACE_IMPORT_INVALID",
                        status_code=422,
                    ) from error
                if result_number <= 0:
                    raise BusinessError(
                        f"第 {row_number} 行的输出序号必须是正整数",
                        "WORKSPACE_IMPORT_INVALID",
                        status_code=422,
                    )
            key = code.casefold()
            current_item = grouped.get(key)
            item = grouped.setdefault(
                key,
                {
                    "code": code,
                    "businessId": business_id,
                    "deviceType": "",
                    "description": "",
                    "debugAssignments": [],
                    "classificationRows": {},
                    "steps": [],
                    "nextStepNumber": 1,
                },
            )
            device_type = str(raw.get("设备类型", raw.get("deviceType", ""))).strip()
            description = str(raw.get("说明", raw.get("description", ""))).strip()
            previous_device_type = item["deviceType"]
            previous_description = item["description"]
            if current_item is not None:
                if device_type and previous_device_type and device_type != previous_device_type:
                    raise BusinessError(
                        f"第 {row_number} 行同一配置编码对应了不同的设备类型",
                        "WORKSPACE_IMPORT_INVALID",
                        status_code=422,
                    )
                if description and previous_description and description != previous_description:
                    raise BusinessError(
                        f"第 {row_number} 行同一配置编码对应了不同的说明",
                        "WORKSPACE_IMPORT_INVALID",
                        status_code=422,
                    )
            if device_type:
                item["deviceType"] = device_type
            if description:
                item["description"] = description
            subitem_name = str(raw.get("调试子项", raw.get("debugSubitem", "")) or "").strip()
            division_name = str(raw.get("调试分项", raw.get("debugDivision", "")) or "").strip()
            previous_classification = next(
                (
                    assignment
                    for assignment in reversed(item["debugAssignments"])
                    if assignment["division"] or assignment["subitem"]
                ),
                None,
            )
            subitem_name = subitem_name or (previous_classification["subitem"] if previous_classification else "")
            division_name = division_name or (previous_classification["division"] if previous_classification else "")
            if subitem_name or division_name:
                assignment = {"subitem": subitem_name, "division": division_name}
                if assignment not in item["debugAssignments"]:
                    item["debugAssignments"].append(assignment)
            else:
                assignment = None
            if business_id and item["businessId"] and business_id != item["businessId"]:
                raise BusinessError(
                    f"第 {row_number} 行同一编码对应了多个业务显示 ID",
                    "WORKSPACE_IMPORT_INVALID",
                    status_code=422,
                )
            steps = item["steps"]
            if step_number is None:
                if not steps:
                    step_number = 1
                elif step_text and steps[-1]["description"] != step_text:
                    step_number = item["nextStepNumber"]
                else:
                    step_number = steps[-1]["number"]
            step = next((candidate for candidate in steps if candidate["number"] == step_number), None)
            if step is None:
                if not step_text:
                    raise BusinessError(
                        f"第 {row_number} 行没有操作步骤；新步骤必须填写操作步骤或步骤序号",
                        "WORKSPACE_IMPORT_INVALID",
                        status_code=422,
                    )
                step = {"number": step_number, "description": step_text, "results": []}
                steps.append(step)
            elif step_text and step["description"] != step_text:
                raise BusinessError(
                    f"第 {row_number} 行的步骤序号 {step_number} 对应了不同的操作步骤",
                    "WORKSPACE_IMPORT_INVALID",
                    status_code=422,
                )
            result_row = (result_number, result_text, responsible_disciplines, row_number)
            if not any(existing_result[:3] == result_row[:3] for existing_result in step["results"]):
                step["results"].append(result_row)
            if assignment is not None:
                assignment_key = (
                    assignment["subitem"].casefold(),
                    assignment["division"].casefold(),
                )
                item["classificationRows"].setdefault(assignment_key, []).append(
                    (
                        step_number,
                        step["description"],
                        result_number,
                        result_text,
                        tuple(responsible_disciplines),
                    )
                )
            item["nextStepNumber"] = max(item["nextStepNumber"], step_number + 1)

        for item in grouped.values():
            signatures = [tuple(rows) for rows in item["classificationRows"].values()]
            if len(signatures) > 1 and any(signature != signatures[0] for signature in signatures[1:]):
                raise BusinessError(
                    f"联调配置编码“{item['code']}”被分配到多个调试分类，但对应步骤/输出不一致；同编码必须使用完全相同的规则，不同规则请使用不同编码",
                    "WORKSPACE_IMPORT_CLASSIFICATION_RULE_MISMATCH",
                    status_code=422,
                )

        existing = {
            item["configCode"].casefold(): item for item in self.list_configs(payload.scope, include_disabled=True)
        }
        for item in grouped.values():
            current = existing.get(item["code"].casefold())
            if item["businessId"] and current and item["businessId"] != current["businessId"]:
                raise BusinessError(
                    "业务显示 ID 与当前配置不一致，不能修改 ID",
                    "WORKSPACE_IMPORT_ID_IMMUTABLE",
                    status_code=422,
                )
            if item["businessId"] and not current:
                by_id = self.get_config(item["businessId"], include_disabled=True)
                if by_id is None or any(
                    int(by_id[field]) != getattr(payload.scope, field.replace("Id", "_id"))
                    for field in ("lineId", "professionId", "projectId")
                ):
                    raise BusinessError(
                        "导入表中的业务显示 ID 不属于当前范围",
                        "WORKSPACE_IMPORT_ID_INVALID",
                        status_code=422,
                    )

        result = []
        for item in grouped.values():
            current = existing.get(item["code"].casefold())
            if current and payload.decisions.get(item["code"].casefold()) == "skip":
                continue
            steps = []
            for index, step in enumerate(sorted(item["steps"], key=lambda value: value["number"]), start=1):
                ordered_results = sorted(
                    step["results"],
                    key=lambda value: (value[0] is None, value[0] or 0, value[3]),
                )
                steps.append(
                    ConfigStepWriteRequest(
                        description=step["description"],
                        ratioChange="否",
                        sortOrder=index,
                        results=[
                            ConfigResultWriteRequest(description=value[1], responsibleDisciplines=value[2])
                            for value in ordered_results
                        ],
                    )
                )
            debug_subitem_id = payload.scope.debug_subitem_id
            debug_division_id = payload.scope.debug_division_id
            resolved_assignments = []
            for assignment in item.get("debugAssignments", []):
                assigned_subitem_id = debug_subitem_id
                assigned_division_id = debug_division_id
                if assignment["subitem"]:
                    # An explicit subitem with an empty division means this
                    # configuration belongs directly to the subitem. Do not
                    # inherit a stale division selected in the page picker.
                    assigned_division_id = None
                    matches = self.list_debug_items(payload.scope, "debug_subitems", None, True)
                    match = next(
                        (row for row in matches if row["name"].casefold() == assignment["subitem"].casefold()),
                        None,
                    )
                    if match is None:
                        match = self.save_debug_item(
                            DebugItemWriteRequest(
                                scope=payload.scope,
                                category="debug_subitems",
                                name=assignment["subitem"],
                                code=assignment["subitem"][:100],
                            )
                        )
                    assigned_subitem_id = match["id"]
                if assignment["division"]:
                    if not assigned_subitem_id:
                        raise BusinessError(
                            "调试分项必须填写调试子项，或在页面选择调试子项",
                            "WORKSPACE_IMPORT_DEBUG_PARENT_REQUIRED",
                            status_code=422,
                        )
                    division_scope = ScopeSelection(
                        lineId=payload.scope.line_id,
                        professionId=payload.scope.profession_id,
                        projectId=payload.scope.project_id,
                    )
                    matches = self.list_debug_items(division_scope, "debug_divisions", assigned_subitem_id, True)
                    match = next(
                        (row for row in matches if row["name"].casefold() == assignment["division"].casefold()),
                        None,
                    )
                    if match is None:
                        match = self.save_debug_item(
                            DebugItemWriteRequest(
                                scope=division_scope,
                                category="debug_divisions",
                                parentId=assigned_subitem_id,
                                name=assignment["division"],
                                code=assignment["division"][:100],
                            )
                        )
                    assigned_division_id = match["id"]
                if assigned_subitem_id:
                    resolved_assignments.append((assigned_subitem_id, assigned_division_id))
            if resolved_assignments:
                debug_subitem_id, debug_division_id = resolved_assignments[0]
            elif debug_subitem_id:
                resolved_assignments.append((debug_subitem_id, debug_division_id))
            config_scope = payload.scope
            if resolved_assignments:
                # A classification written in the import sheet takes
                # precedence over any stale subitem/division selected in the
                # page toolbar. Keep the scope limited to line/profession/
                # project so validation uses the resolved row classification.
                config_scope = ScopeSelection(
                    lineId=payload.scope.line_id,
                    professionId=payload.scope.profession_id,
                    projectId=payload.scope.project_id,
                )
            request = ConfigWriteRequest(
                scope=config_scope,
                configCode=item["code"],
                deviceType=item["deviceType"],
                description=item["description"],
                steps=steps,
                isEnabled=True,
                debugSubitemId=debug_subitem_id,
                debugDivisionId=debug_division_id,
            )
            saved = (
                self.update_config(current["id"], request, user_id) if current else self.create_config(request, user_id)
            )
            with closing(self._connect()) as connection, connection:
                for assigned_subitem_id, assigned_division_id in resolved_assignments:
                    self._save_config_classification(connection, saved["id"], assigned_subitem_id, assigned_division_id)
            result.append(saved)
        return result

    def preview_import(self, payload: ConfigImportRequest) -> dict[str, Any]:
        """Return a non-mutating conflict summary for an import batch.

        The preview deliberately accepts the same compact sheet used by the
        existing importer.  The caller can then send per-code decisions on
        the commit request; non-conflicting codes are always eligible for
        import.
        """
        self.get_scope(payload.scope)
        existing = {
            item["configCode"].casefold(): item for item in self.list_configs(payload.scope, include_disabled=True)
        }
        incoming: dict[str, list[dict[str, object]]] = {}
        current = ""
        for index, raw_row in enumerate(payload.rows, start=2):
            row = {str(key).replace("\ufeff", "").strip(): value for key, value in raw_row.items()}
            code = str(row.get("联调配置编码", row.get("configCode", "")) or "").strip()
            if code:
                current = code
            if not current:
                continue
            incoming.setdefault(current.casefold(), []).append({"rowNumber": index, **row, "联调配置编码": current})
        conflicts = []
        for key, rows in incoming.items():
            old = existing.get(key)
            if old:
                conflicts.append(
                    {
                        "configCode": old["configCode"],
                        "existing": old,
                        "incomingRows": rows,
                        "defaultDecision": "skip",
                    }
                )
        return {
            "newCodes": [rows[0]["联调配置编码"] for key, rows in incoming.items() if key not in existing],
            "conflicts": conflicts,
            "totalCodes": len(incoming),
        }

    def get_config(self, config_id: str, include_disabled: bool = False) -> dict[str, Any] | None:
        self.ensure_schema()
        with closing(self._connect()) as c:
            row = c.execute(
                "SELECT * FROM workspace_configs WHERE id = ?" + ("" if include_disabled else " AND is_enabled = 1"),
                (config_id,),
            ).fetchone()
            return self._config(c, row) if row else None

    def resolve_config(self, selection: ScopeSelection, code: str) -> dict[str, Any] | None:
        self.get_scope(selection)
        self.ensure_schema()
        with closing(self._connect()) as c:
            row = c.execute(
                """SELECT c.* FROM workspace_configs c
                LEFT JOIN workspace_config_aliases a ON a.config_id = c.id
                WHERE c.line_id = ? AND c.profession_id = ? AND c.project_id = ?
                  AND c.is_enabled = 1 AND (c.config_code = ? COLLATE NOCASE OR a.alias = ? COLLATE NOCASE)
                ORDER BY CASE WHEN c.config_code = ? COLLATE NOCASE THEN 0 ELSE 1 END LIMIT 1""",
                (
                    selection.line_id,
                    selection.profession_id,
                    selection.project_id,
                    code.strip(),
                    code.strip(),
                    code.strip(),
                ),
            ).fetchone()
            return self._config(c, row) if row else None

    def project_engine_code(self, project_id: int) -> str:
        self.ensure_schema()
        with closing(self._connect()) as c:
            row = c.execute("SELECT engine_code FROM workspace_projects WHERE id = ?", (project_id,)).fetchone()
        return str(row[0]) if row and row[0] else ""

    def list_users(self) -> list[dict[str, Any]]:
        self.ensure_schema()
        with closing(self._connect()) as c:
            rows = c.execute(
                """
                SELECT u.id, u.username, u.display_name, u.role, u.line_id, u.profession_id, u.is_enabled,
                       l.name AS line_name, p.name AS profession_name
                FROM auth_users u
                LEFT JOIN workspace_lines l ON l.id = u.line_id
                LEFT JOIN workspace_professions p ON p.id = u.profession_id
                ORDER BY u.id
                """
            ).fetchall()
        return [
            {
                "id": int(r["id"]),
                "username": str(r["username"]),
                "displayName": str(r["display_name"]),
                "role": str(r["role"]),
                "lineId": r["line_id"],
                "professionId": r["profession_id"],
                "lineName": r["line_name"],
                "professionName": r["profession_name"],
                "isEnabled": bool(r["is_enabled"]),
            }
            for r in rows
        ]

    def create_user(self, payload: UserWriteRequest) -> dict[str, Any]:
        self.ensure_schema()
        self._validate_role_scope(payload.role, payload.line_id, payload.profession_id)
        if payload.password is None:
            raise BusinessError("请填写初始密码", "AUTH_PASSWORD_REQUIRED", status_code=422)
        try:
            with closing(self._connect()) as c, c:
                cur = c.execute(
                    """
                    INSERT INTO auth_users(
                        username, password_hash, display_name, role, line_id, profession_id, is_enabled
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.username,
                        hash_password(payload.password),
                        payload.display_name,
                        payload.role,
                        payload.line_id,
                        payload.profession_id,
                        int(payload.is_enabled),
                    ),
                )
                row = c.execute(
                    """
                    SELECT id, username, display_name, role, line_id, profession_id, is_enabled
                    FROM auth_users
                    WHERE id = ?
                    """,
                    (cur.lastrowid,),
                ).fetchone()
            return {
                "id": int(row["id"]),
                "username": str(row["username"]),
                "displayName": str(row["display_name"]),
                "role": str(row["role"]),
                "lineId": row["line_id"],
                "professionId": row["profession_id"],
                "isEnabled": bool(row["is_enabled"]),
            }
        except sqlite3.IntegrityError as exc:
            raise BusinessError("用户名已存在", "AUTH_USERNAME_EXISTS", status_code=409) from exc

    def update_user(self, user_id: int, payload: UserWriteRequest) -> dict[str, Any]:
        self.ensure_schema()
        self._validate_role_scope(payload.role, payload.line_id, payload.profession_id)
        try:
            with closing(self._connect()) as c, c:
                existing = c.execute("SELECT id FROM auth_users WHERE id = ?", (user_id,)).fetchone()
                if existing is None:
                    raise BusinessError("账号不存在", "AUTH_USER_NOT_FOUND", status_code=404)
                if payload.password is None:
                    c.execute(
                        """UPDATE auth_users SET username = ?, display_name = ?, role = ?, line_id = ?,
                           profession_id = ?, is_enabled = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                           WHERE id = ?""",
                        (
                            payload.username,
                            payload.display_name,
                            payload.role,
                            payload.line_id,
                            payload.profession_id,
                            int(payload.is_enabled),
                            user_id,
                        ),
                    )
                else:
                    c.execute(
                        """
                        UPDATE auth_users
                        SET username = ?, password_hash = ?, display_name = ?, role = ?,
                            line_id = ?, profession_id = ?, is_enabled = ?,
                            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        WHERE id = ?
                        """,
                        (
                            payload.username,
                            hash_password(payload.password),
                            payload.display_name,
                            payload.role,
                            payload.line_id,
                            payload.profession_id,
                            int(payload.is_enabled),
                            user_id,
                        ),
                    )
                    c.execute(
                        """
                        UPDATE auth_sessions
                        SET revoked_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        WHERE user_id = ? AND revoked_at IS NULL
                        """,
                        (user_id,),
                    )
                row = c.execute(
                    """
                    SELECT id, username, display_name, role, line_id, profession_id, is_enabled
                    FROM auth_users
                    WHERE id = ?
                    """,
                    (user_id,),
                ).fetchone()
            return {
                "id": int(row["id"]),
                "username": str(row["username"]),
                "displayName": str(row["display_name"]),
                "role": str(row["role"]),
                "lineId": row["line_id"],
                "professionId": row["profession_id"],
                "isEnabled": bool(row["is_enabled"]),
            }
        except sqlite3.IntegrityError as exc:
            raise BusinessError("用户名已存在", "AUTH_USERNAME_EXISTS", status_code=409) from exc

    @staticmethod
    def _validate_role_scope(role: str, line_id: int | None, profession_id: int | None) -> None:
        if role == ROLE_SUPER_ADMIN and (line_id or profession_id):
            raise BusinessError("超级管理员不能绑定线路或专业", "AUTH_SCOPE_INVALID", status_code=422)
        if role == ROLE_LINE_ADMIN and not line_id:
            raise BusinessError("线路管理员必须绑定线路", "AUTH_SCOPE_REQUIRED", status_code=422)
        if role == ROLE_PROFESSIONAL_CONFIGURATOR and (not line_id or not profession_id):
            raise BusinessError("专业配置员必须绑定线路和专业", "AUTH_SCOPE_REQUIRED", status_code=422)

    def _next_business_id(self, line: sqlite3.Row, profession: sqlite3.Row, project: sqlite3.Row) -> str:
        prefix = f"{line['code']}-{profession['code']}-{project['code']}"
        with closing(self._connect()) as c:
            rows = c.execute(
                "SELECT business_id FROM workspace_configs WHERE line_id = ? AND profession_id = ? AND project_id = ?",
                (line["id"], profession["id"], project["id"]),
            ).fetchall()
        numbers = []
        for row in rows:
            match = re.search(r"-(\d+)$", str(row[0]))
            if match:
                numbers.append(int(match.group(1)))
        return f"{prefix}-{max(numbers, default=0) + 1:03d}"

    def _replace_steps(self, c: sqlite3.Connection, config_id: str, steps: list[Any]) -> None:
        c.execute(
            """
            DELETE FROM workspace_config_results
            WHERE step_id IN (
                SELECT id FROM workspace_config_steps WHERE config_id = ?
            )
            """,
            (config_id,),
        )
        c.execute("DELETE FROM workspace_config_steps WHERE config_id = ?", (config_id,))
        for step in steps:
            cur = c.execute(
                """
                INSERT INTO workspace_config_steps(
                    config_id, sort_order, description, ratio_change, is_enabled
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    config_id,
                    step.sort_order,
                    step.description,
                    step.ratio_change,
                    int(step.is_enabled),
                ),
            )
            for result_order, result in enumerate(step.results, start=1):
                disciplines = getattr(result, "responsible_disciplines", None)
                if disciplines is None and isinstance(result, dict):
                    disciplines = result.get("responsibleDisciplines", [])
                description = (
                    result.description if hasattr(result, "description") else str(result.get("description", ""))
                )
                c.execute(
                    """
                    INSERT INTO workspace_config_results(
                        step_id, sort_order, description, responsible_disciplines
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        cur.lastrowid,
                        result_order,
                        description,
                        json.dumps(disciplines or [], ensure_ascii=False),
                    ),
                )

    def _add_alias(self, c: sqlite3.Connection, config_id: str, alias: str, current: bool) -> None:
        c.execute("UPDATE workspace_config_aliases SET is_current = 0 WHERE config_id = ?", (config_id,))
        c.execute(
            "INSERT OR IGNORE INTO workspace_config_aliases(config_id, alias, is_current) VALUES (?, ?, ?)",
            (config_id, alias.strip(), int(current)),
        )

    def _config(self, c: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
        row_keys = set(row.keys())
        steps = []
        for step in c.execute(
            "SELECT * FROM workspace_config_steps WHERE config_id = ? ORDER BY sort_order, id",
            (row["id"],),
        ).fetchall():
            results = []
            for result in c.execute(
                "SELECT * FROM workspace_config_results WHERE step_id = ? ORDER BY sort_order, id",
                (step["id"],),
            ).fetchall():
                try:
                    disciplines = json.loads(str(result["responsible_disciplines"]))
                except json.JSONDecodeError:
                    disciplines = []
                results.append(
                    {
                        "id": int(result["id"]),
                        "sortOrder": int(result["sort_order"]),
                        "description": str(result["description"]),
                        "responsibleDisciplines": disciplines,
                    }
                )
            steps.append(
                {
                    "id": int(step["id"]),
                    "sortOrder": int(step["sort_order"]),
                    "description": str(step["description"]),
                    "ratioChange": str(step["ratio_change"]),
                    "isEnabled": bool(step["is_enabled"]),
                    "results": results,
                }
            )
        aliases = [
            str(r["alias"])
            for r in c.execute(
                "SELECT alias FROM workspace_config_aliases WHERE config_id = ? ORDER BY id",
                (row["id"],),
            ).fetchall()
        ]
        return {
            "id": str(row["id"]),
            "businessId": str(row["business_id"]),
            "lineId": int(row["line_id"]),
            "professionId": int(row["profession_id"]),
            "projectId": int(row["project_id"]),
            "debugSubitemId": row["debug_subitem_id"] if "debug_subitem_id" in row_keys else None,
            "debugDivisionId": row["debug_division_id"] if "debug_division_id" in row_keys else None,
            "configCode": str(row["config_code"]),
            "aliases": aliases,
            "deviceType": str(row["device_type"]),
            "description": str(row["description"]),
            "isEnabled": bool(row["is_enabled"]),
            "revision": int(row["revision"]),
            "steps": steps,
        }

    @staticmethod
    def _line(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "code": str(row["code"]),
            "name": str(row["name"]),
            "sortOrder": int(row["sort_order"]),
            "isEnabled": bool(row["is_enabled"]),
        }

    @staticmethod
    def _profession(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "code": str(row["code"]),
            "name": str(row["name"]),
            "parentId": int(row["parent_id"]) if row["parent_id"] is not None else None,
            "sortOrder": int(row["sort_order"]),
            "isEnabled": bool(row["is_enabled"]),
        }

    @staticmethod
    def _project(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "lineId": int(row["line_id"]) if row["line_id"] is not None else None,
            "professionId": int(row["profession_id"]),
            "code": str(row["code"]),
            "name": str(row["name"]),
            "description": str(row["description"]),
            "engineCode": str(row["engine_code"]),
            "sortOrder": int(row["sort_order"]),
            "isEnabled": bool(row["is_enabled"]),
        }
