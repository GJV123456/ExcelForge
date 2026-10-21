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
    LineWriteRequest,
    ProfessionWriteRequest,
    ProjectWriteRequest,
    ScopeSelection,
    UserWriteRequest,
    WorkspaceCatalogWriteRequest,
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
            connection.execute("""
                CREATE TABLE IF NOT EXISTS workspace_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    UNIQUE (profession_id, code)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS workspace_configs (
                    id TEXT PRIMARY KEY,
                    business_id TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    line_id INTEGER NOT NULL,
                    profession_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
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
                "CREATE INDEX IF NOT EXISTS ix_workspace_configs_scope ON workspace_configs(line_id, profession_id, project_id)",
                "CREATE INDEX IF NOT EXISTS ix_workspace_aliases_alias ON workspace_config_aliases(alias)",
                "CREATE INDEX IF NOT EXISTS ix_workspace_steps_config ON workspace_config_steps(config_id, sort_order)",
                "CREATE INDEX IF NOT EXISTS ix_workspace_catalog_scope ON workspace_catalog_items(category, line_id, profession_id, project_id)",
            ):
                connection.execute(statement)
            columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(auth_users)")}
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

    def list_catalog_items(self, scope: ScopeSelection, category: str, include_disabled: bool = False) -> list[dict[str, Any]]:
        self.get_scope(scope)
        self.ensure_schema()
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

    def save_catalog_item(self, payload: WorkspaceCatalogWriteRequest, item_id: str | None = None) -> dict[str, Any]:
        self.get_scope(payload.scope)
        self.ensure_schema()
        try:
            with closing(self._connect()) as connection, connection:
                shared_by_line = payload.category in {"disciplines", "stations"}
                if shared_by_line:
                    duplicate_query = "SELECT id FROM workspace_catalog_items WHERE category = ? AND line_id = ? AND (name = ? COLLATE NOCASE OR (? <> '' AND code = ? COLLATE NOCASE))"
                    duplicate_params: list[Any] = [payload.category, payload.scope.line_id, payload.name, payload.code, payload.code]
                    if item_id is not None:
                        duplicate_query += " AND id <> ?"
                        duplicate_params.append(item_id)
                    if connection.execute(duplicate_query, duplicate_params).fetchone():
                        raise BusinessError("同一线路下的名称或编码已存在", "WORKSPACE_CATALOG_EXISTS", status_code=409)
                if item_id is None:
                    item_id = uuid4().hex
                    connection.execute("""INSERT INTO workspace_catalog_items
                        (id, category, line_id, profession_id, project_id, code, name, description, sort_order, is_enabled)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (item_id, payload.category, payload.scope.line_id, payload.scope.profession_id,
                         payload.scope.project_id, payload.code, payload.name, payload.description,
                         payload.sort_order, int(payload.is_enabled)))
                else:
                    update_scope = "id = ? AND category = ? AND line_id = ?"
                    update_params: list[Any] = [payload.code, payload.name, payload.description, payload.sort_order,
                        int(payload.is_enabled), item_id, payload.category, payload.scope.line_id]
                    if not shared_by_line:
                        update_scope += " AND profession_id = ? AND project_id = ?"
                        update_params.extend([payload.scope.profession_id, payload.scope.project_id])
                    cursor = connection.execute(f"""UPDATE workspace_catalog_items SET code = ?, name = ?, description = ?,
                        sort_order = ?, is_enabled = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        WHERE {update_scope}""", update_params)
                    if cursor.rowcount == 0:
                        raise BusinessError("配置项目不存在或不属于当前范围", "WORKSPACE_CATALOG_NOT_FOUND", status_code=404)
                row = connection.execute("SELECT * FROM workspace_catalog_items WHERE id = ?", (item_id,)).fetchone()
                return self._catalog_item(row)
        except sqlite3.IntegrityError as exc:
            raise BusinessError("同一范围下的名称或编码已存在", "WORKSPACE_CATALOG_EXISTS", status_code=409) from exc

    @staticmethod
    def _catalog_item(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "category": row["category"], "lineId": int(row["line_id"]),
                "professionId": int(row["profession_id"]), "projectId": int(row["project_id"]),
                "code": row["code"], "name": row["name"], "description": row["description"],
                "sortOrder": int(row["sort_order"]), "isEnabled": bool(row["is_enabled"])}

    @staticmethod
    def _seed_defaults(connection: sqlite3.Connection) -> None:
        connection.execute(
            "INSERT OR IGNORE INTO workspace_lines(code, name, sort_order) VALUES ('9', '9号线', 9)"
        )
        connection.execute(
            "INSERT OR IGNORE INTO workspace_professions(code, name, sort_order) VALUES ('ZDH', '自动化', 1)"
        )
        profession = connection.execute(
            "SELECT id FROM workspace_professions WHERE code = 'ZDH' COLLATE NOCASE"
        ).fetchone()
        if profession:
            connection.execute(
                """INSERT OR IGNORE INTO workspace_projects(
                    profession_id, code, name, description, engine_code, sort_order
                ) VALUES (?, 'FAS', 'FAS', '火灾自动报警系统联调', 'T19', 1)""",
                (int(profession[0]),),
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
        self, profession_id: int | None = None, include_disabled: bool = False
    ) -> list[dict[str, Any]]:
        self.ensure_schema()
        with closing(self._connect()) as c:
            clauses: list[str] = []
            params: list[Any] = []
            if profession_id:
                clauses.append("profession_id = ?")
                params.append(profession_id)
            if not include_disabled:
                clauses.append("is_enabled = 1")
            query = "SELECT * FROM workspace_projects" + (
                " WHERE " + " AND ".join(clauses) if clauses else ""
            )
            query += " ORDER BY sort_order, id"
            return [self._project(row) for row in c.execute(query, params).fetchall()]

    def create_line(self, payload: LineWriteRequest) -> dict[str, Any]:
        self.ensure_schema()
        try:
            with closing(self._connect()) as c, c:
                cur = c.execute(
                    "INSERT INTO workspace_lines(code, name, sort_order, is_enabled) VALUES (?, ?, ?, ?)",
                    (payload.code, payload.name, payload.sort_order, int(payload.is_enabled)),
                )
                return self._line(
                    c.execute(
                        "SELECT * FROM workspace_lines WHERE id = ?", (cur.lastrowid,)
                    ).fetchone()
                )
        except sqlite3.IntegrityError as exc:
            raise BusinessError(
                "线路编码或名称已存在", "WORKSPACE_LINE_EXISTS", status_code=409
            ) from exc

    def update_line(self, line_id: int, payload: LineWriteRequest) -> dict[str, Any]:
        self.ensure_schema()
        try:
            with closing(self._connect()) as c, c:
                cursor = c.execute(
                    "UPDATE workspace_lines SET code = ?, name = ?, sort_order = ?, is_enabled = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                    (payload.code, payload.name, payload.sort_order, int(payload.is_enabled), line_id),
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
                cur = c.execute(
                    "INSERT INTO workspace_professions(code, name, sort_order, is_enabled) VALUES (?, ?, ?, ?)",
                    (payload.code, payload.name, payload.sort_order, int(payload.is_enabled)),
                )
                return self._profession(
                    c.execute(
                        "SELECT * FROM workspace_professions WHERE id = ?", (cur.lastrowid,)
                    ).fetchone()
                )
        except sqlite3.IntegrityError as exc:
            raise BusinessError(
                "专业编码或名称已存在", "WORKSPACE_PROFESSION_EXISTS", status_code=409
            ) from exc

    def update_profession(self, profession_id: int, payload: ProfessionWriteRequest) -> dict[str, Any]:
        self.ensure_schema()
        try:
            with closing(self._connect()) as c, c:
                cursor = c.execute(
                    "UPDATE workspace_professions SET code = ?, name = ?, sort_order = ?, is_enabled = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                    (payload.code, payload.name, payload.sort_order, int(payload.is_enabled), profession_id),
                )
                if cursor.rowcount == 0:
                    raise BusinessError("专业不存在", "WORKSPACE_PROFESSION_NOT_FOUND", status_code=404)
                return self._profession(c.execute("SELECT * FROM workspace_professions WHERE id = ?", (profession_id,)).fetchone())
        except sqlite3.IntegrityError as exc:
            raise BusinessError("专业编码或名称已存在", "WORKSPACE_PROFESSION_EXISTS", status_code=409) from exc

    def create_project(self, payload: ProjectWriteRequest) -> dict[str, Any]:
        self.ensure_schema()
        engine_code = payload.engine_code.strip().upper() or payload.code.strip().upper()
        try:
            with closing(self._connect()) as c, c:
                cur = c.execute(
                    """INSERT INTO workspace_projects(
                    profession_id, code, name, description, engine_code, sort_order, is_enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
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
                    c.execute(
                        "SELECT * FROM workspace_projects WHERE id = ?", (cur.lastrowid,)
                    ).fetchone()
                )
        except sqlite3.IntegrityError as exc:
            raise BusinessError(
                "该专业下的联调项目已存在", "WORKSPACE_PROJECT_EXISTS", status_code=409
            ) from exc

    def update_project(self, project_id: int, payload: ProjectWriteRequest) -> dict[str, Any]:
        self.ensure_schema()
        engine_code = payload.engine_code.strip().upper() or payload.code.strip().upper()
        try:
            with closing(self._connect()) as c, c:
                cursor = c.execute(
                    """UPDATE workspace_projects
                    SET profession_id = ?, code = ?, name = ?, description = ?, engine_code = ?, sort_order = ?, is_enabled = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    WHERE id = ?""",
                    (payload.profession_id, payload.code, payload.name, payload.description, engine_code, payload.sort_order, int(payload.is_enabled), project_id),
                )
                if cursor.rowcount == 0:
                    raise BusinessError("联调项目不存在", "WORKSPACE_PROJECT_NOT_FOUND", status_code=404)
                return self._project(c.execute("SELECT * FROM workspace_projects WHERE id = ?", (project_id,)).fetchone())
        except sqlite3.IntegrityError as exc:
            raise BusinessError("该专业下的联调项目已存在", "WORKSPACE_PROJECT_EXISTS", status_code=409) from exc

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
                "SELECT * FROM workspace_projects WHERE id = ? AND profession_id = ? AND is_enabled = 1",
                (selection.project_id, selection.profession_id),
            ).fetchone()
        if not line or not profession or not project:
            raise BusinessError(
                "线路、专业或联调项目不存在", "WORKSPACE_SCOPE_NOT_FOUND", status_code=404
            )
        return line, profession, project

    def list_configs(
        self, selection: ScopeSelection, include_disabled: bool = False
    ) -> list[dict[str, Any]]:
        self.get_scope(selection)
        with closing(self._connect()) as c:
            query = "SELECT * FROM workspace_configs WHERE line_id = ? AND profession_id = ? AND project_id = ?"
            params: list[Any] = [selection.line_id, selection.profession_id, selection.project_id]
            if not include_disabled:
                query += " AND is_enabled = 1"
            query += " ORDER BY business_id"
            rows = c.execute(query, params).fetchall()
            return [self._config(c, row) for row in rows]

    def create_config(self, payload: ConfigWriteRequest, user_id: int) -> dict[str, Any]:
        line, profession, project = self.get_scope(payload.scope)
        self.ensure_schema()
        config_id = uuid4().hex
        business_id = self._next_business_id(line, profession, project)
        try:
            with closing(self._connect()) as c, c:
                c.execute(
                    """INSERT INTO workspace_configs(
                    id, business_id, line_id, profession_id, project_id, config_code,
                    device_type, description, is_enabled, created_by, updated_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        config_id,
                        business_id,
                        payload.scope.line_id,
                        payload.scope.profession_id,
                        payload.scope.project_id,
                        payload.config_code,
                        payload.device_type,
                        payload.description,
                        int(payload.is_enabled),
                        user_id,
                        user_id,
                    ),
                )
                self._replace_steps(c, config_id, payload.steps)
                self._add_alias(c, config_id, payload.config_code, True)
                return self._config(
                    c,
                    c.execute(
                        "SELECT * FROM workspace_configs WHERE id = ?", (config_id,)
                    ).fetchone(),
                )
        except sqlite3.IntegrityError as exc:
            raise BusinessError(
                "当前线路、专业和项目下的联调配置编码已存在",
                "WORKSPACE_CONFIG_EXISTS",
                status_code=409,
            ) from exc

    def update_config(
        self, config_id: str, payload: ConfigWriteRequest, user_id: int
    ) -> dict[str, Any]:
        self.get_scope(payload.scope)
        self.ensure_schema()
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
                """INSERT INTO workspace_config_history(config_id, revision, snapshot, changed_by) VALUES (?, ?, ?, ?)""",
                (config_id, revision, json.dumps(snapshot, ensure_ascii=False), user_id),
            )
            try:
                c.execute(
                    """UPDATE workspace_configs SET config_code = ?, device_type = ?, description = ?, is_enabled = ?, revision = ?, updated_by = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?""",
                    (
                        payload.config_code,
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
            except sqlite3.IntegrityError as exc:
                raise BusinessError(
                    "当前范围内的联调配置编码已存在", "WORKSPACE_CONFIG_EXISTS", status_code=409
                ) from exc
            return self._config(
                c,
                c.execute("SELECT * FROM workspace_configs WHERE id = ?", (config_id,)).fetchone(),
            )

    def copy_configs(
        self, payload: ConfigCopyRequest | BatchConfigCopyRequest, user_id: int
    ) -> list[dict[str, Any]]:
        self.get_scope(payload.target)
        ids = (
            [payload.source_config_id]
            if isinstance(payload, ConfigCopyRequest)
            else payload.source_config_ids
        )
        result: list[dict[str, Any]] = []
        for source_id in ids:
            source = self.get_config(source_id, include_disabled=True)
            if source is None:
                raise BusinessError(
                    "待复制的联调配置不存在", "WORKSPACE_CONFIG_NOT_FOUND", status_code=404
                )
            source_scope = ScopeSelection(
                lineId=source["lineId"],
                professionId=source["professionId"],
                projectId=source["projectId"],
            )
            if source_scope.profession_id != payload.target.profession_id:
                raise BusinessError(
                    "专业配置员只能复制相同专业的配置",
                    "WORKSPACE_COPY_PROFESSION_MISMATCH",
                    status_code=403,
                )
            if source["configCode"] in {
                item["configCode"]
                for item in self.list_configs(payload.target, include_disabled=True)
            }:
                continue
            copied_payload = ConfigWriteRequest(
                scope=payload.target,
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
            )
            result.append(self.create_config(copied_payload, user_id))
        return result

    def disable_config(self, config_id: str, enabled: bool, user_id: int) -> dict[str, Any]:
        self.ensure_schema()
        with closing(self._connect()) as c, c:
            row = c.execute("SELECT * FROM workspace_configs WHERE id = ?", (config_id,)).fetchone()
            if row is None:
                raise BusinessError("联调配置不存在", "WORKSPACE_CONFIG_NOT_FOUND", status_code=404)
            c.execute(
                "UPDATE workspace_configs SET is_enabled = ?, updated_by = ?, revision = revision + 1, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                (int(enabled), user_id, config_id),
            )
            return self._config(
                c,
                c.execute("SELECT * FROM workspace_configs WHERE id = ?", (config_id,)).fetchone(),
            )

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
        for row_number, raw in enumerate(payload.rows, start=2):
            code = str(raw.get("联调配置编码", raw.get("configCode", ""))).strip()
            if code:
                current_config_key = code.casefold()
            elif current_config_key:
                code = grouped[current_config_key]["code"]
            else:
                raise BusinessError(
                    f"第 {row_number} 行没有联调配置编码，且前面没有可沿用的配置编码",
                    "WORKSPACE_IMPORT_INVALID", status_code=422,
                )
            business_id = str(raw.get("业务显示ID", raw.get("businessId", ""))).strip()
            step_text = str(raw.get("操作步骤", raw.get("stepDescription", ""))).strip()
            result_text = str(raw.get("预期结果", raw.get("resultDescription", ""))).strip()
            discipline_text = str(raw.get("责任专业", raw.get("responsibleDiscipline", raw.get("responsibleDisciplines", ""))) or "").strip()
            responsible_disciplines = [
                name.strip() for name in re.split(r"[,，、;；/]+", discipline_text) if name.strip()
            ]
            unknown_disciplines = [name for name in responsible_disciplines if name.casefold() not in discipline_names]
            if unknown_disciplines:
                raise BusinessError(
                    f"第 {row_number} 行的责任专业未在线路责任专业目录中配置：{'、'.join(unknown_disciplines)}",
                    "WORKSPACE_IMPORT_DISCIPLINE_INVALID", status_code=422,
                )
            responsible_disciplines = list(dict.fromkeys(discipline_names[name.casefold()] for name in responsible_disciplines))
            step_number_raw = raw.get("步骤序号", raw.get("操作步骤序号", raw.get("stepOrder", raw.get("stepIndex", ""))))
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
                    raise BusinessError(f"第 {row_number} 行的步骤序号必须是正整数", "WORKSPACE_IMPORT_INVALID", status_code=422) from error
                if step_number <= 0:
                    raise BusinessError(f"第 {row_number} 行的步骤序号必须是正整数", "WORKSPACE_IMPORT_INVALID", status_code=422)
            result_number = None
            if result_number_text:
                try:
                    result_number = int(result_number_text)
                except ValueError as error:
                    raise BusinessError(f"第 {row_number} 行的输出序号必须是正整数", "WORKSPACE_IMPORT_INVALID", status_code=422) from error
                if result_number <= 0:
                    raise BusinessError(f"第 {row_number} 行的输出序号必须是正整数", "WORKSPACE_IMPORT_INVALID", status_code=422)
            key = code.casefold()
            current_item = grouped.get(key)
            item = grouped.setdefault(
                key,
                {
                    "code": code,
                    "businessId": business_id,
                    "deviceType": "",
                    "description": "",
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
                        "WORKSPACE_IMPORT_INVALID", status_code=422,
                    )
                if description and previous_description and description != previous_description:
                    raise BusinessError(
                        f"第 {row_number} 行同一配置编码对应了不同的说明",
                        "WORKSPACE_IMPORT_INVALID", status_code=422,
                    )
            if device_type:
                item["deviceType"] = device_type
            if description:
                item["description"] = description
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
                        "WORKSPACE_IMPORT_INVALID", status_code=422,
                    )
                step = {"number": step_number, "description": step_text, "results": []}
                steps.append(step)
            elif step_text and step["description"] != step_text:
                raise BusinessError(
                    f"第 {row_number} 行的步骤序号 {step_number} 对应了不同的操作步骤",
                    "WORKSPACE_IMPORT_INVALID", status_code=422,
                )
            step["results"].append((result_number, result_text, responsible_disciplines, row_number))
            item["nextStepNumber"] = max(item["nextStepNumber"], step_number + 1)

        existing = {
            item["configCode"].casefold(): item
            for item in self.list_configs(payload.scope, include_disabled=True)
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
            steps = []
            for index, step in enumerate(sorted(item["steps"], key=lambda value: value["number"]), start=1):
                ordered_results = sorted(
                    step["results"],
                    key=lambda value: (value[0] is None, value[0] or 0, value[3]),
                )
                steps.append(ConfigStepWriteRequest(
                    description=step["description"],
                    ratioChange="否",
                    sortOrder=index,
                    results=[ConfigResultWriteRequest(description=value[1], responsibleDisciplines=value[2]) for value in ordered_results],
                ))
            request = ConfigWriteRequest(
                scope=payload.scope,
                configCode=item["code"],
                deviceType=item["deviceType"],
                description=item["description"],
                steps=steps,
                isEnabled=True,
            )
            current = existing.get(item["code"].casefold())
            result.append(
                self.update_config(current["id"], request, user_id)
                if current
                else self.create_config(request, user_id)
            )
        return result

    def get_config(self, config_id: str, include_disabled: bool = False) -> dict[str, Any] | None:
        self.ensure_schema()
        with closing(self._connect()) as c:
            row = c.execute(
                "SELECT * FROM workspace_configs WHERE id = ?"
                + ("" if include_disabled else " AND is_enabled = 1"),
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
            row = c.execute(
                "SELECT engine_code FROM workspace_projects WHERE id = ?", (project_id,)
            ).fetchone()
        return str(row[0]) if row and row[0] else ""

    def list_users(self) -> list[dict[str, Any]]:
        self.ensure_schema()
        with closing(self._connect()) as c:
            rows = c.execute("""SELECT u.id, u.username, u.display_name, u.role, u.line_id, u.profession_id, u.is_enabled,
                l.name AS line_name, p.name AS profession_name
                FROM auth_users u LEFT JOIN workspace_lines l ON l.id = u.line_id
                LEFT JOIN workspace_professions p ON p.id = u.profession_id ORDER BY u.id""").fetchall()
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
                    """INSERT INTO auth_users(username, password_hash, display_name, role, line_id, profession_id, is_enabled) VALUES (?, ?, ?, ?, ?, ?, ?)""",
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
                    "SELECT id, username, display_name, role, line_id, profession_id, is_enabled FROM auth_users WHERE id = ?",
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
                        (payload.username, payload.display_name, payload.role, payload.line_id,
                         payload.profession_id, int(payload.is_enabled), user_id),
                    )
                else:
                    c.execute(
                        """UPDATE auth_users SET username = ?, password_hash = ?, display_name = ?, role = ?,
                           line_id = ?, profession_id = ?, is_enabled = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                           WHERE id = ?""",
                        (payload.username, hash_password(payload.password), payload.display_name, payload.role,
                         payload.line_id, payload.profession_id, int(payload.is_enabled), user_id),
                    )
                    c.execute(
                        "UPDATE auth_sessions SET revoked_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE user_id = ? AND revoked_at IS NULL",
                        (user_id,),
                    )
                row = c.execute(
                    "SELECT id, username, display_name, role, line_id, profession_id, is_enabled FROM auth_users WHERE id = ?",
                    (user_id,),
                ).fetchone()
            return {
                "id": int(row["id"]), "username": str(row["username"]),
                "displayName": str(row["display_name"]), "role": str(row["role"]),
                "lineId": row["line_id"], "professionId": row["profession_id"],
                "isEnabled": bool(row["is_enabled"]),
            }
        except sqlite3.IntegrityError as exc:
            raise BusinessError("用户名已存在", "AUTH_USERNAME_EXISTS", status_code=409) from exc

    @staticmethod
    def _validate_role_scope(role: str, line_id: int | None, profession_id: int | None) -> None:
        if role == ROLE_SUPER_ADMIN and (line_id or profession_id):
            raise BusinessError(
                "超级管理员不能绑定线路或专业", "AUTH_SCOPE_INVALID", status_code=422
            )
        if role == ROLE_LINE_ADMIN and not line_id:
            raise BusinessError("线路管理员必须绑定线路", "AUTH_SCOPE_REQUIRED", status_code=422)
        if role == ROLE_PROFESSIONAL_CONFIGURATOR and (not line_id or not profession_id):
            raise BusinessError(
                "专业配置员必须绑定线路和专业", "AUTH_SCOPE_REQUIRED", status_code=422
            )

    def _next_business_id(
        self, line: sqlite3.Row, profession: sqlite3.Row, project: sqlite3.Row
    ) -> str:
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
            "DELETE FROM workspace_config_results WHERE step_id IN (SELECT id FROM workspace_config_steps WHERE config_id = ?)",
            (config_id,),
        )
        c.execute("DELETE FROM workspace_config_steps WHERE config_id = ?", (config_id,))
        for step in steps:
            cur = c.execute(
                "INSERT INTO workspace_config_steps(config_id, sort_order, description, ratio_change, is_enabled) VALUES (?, ?, ?, ?, ?)",
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
                    result.description
                    if hasattr(result, "description")
                    else str(result.get("description", ""))
                )
                c.execute(
                    "INSERT INTO workspace_config_results(step_id, sort_order, description, responsible_disciplines) VALUES (?, ?, ?, ?)",
                    (
                        cur.lastrowid,
                        result_order,
                        description,
                        json.dumps(disciplines or [], ensure_ascii=False),
                    ),
                )

    def _add_alias(self, c: sqlite3.Connection, config_id: str, alias: str, current: bool) -> None:
        c.execute(
            "UPDATE workspace_config_aliases SET is_current = 0 WHERE config_id = ?", (config_id,)
        )
        c.execute(
            "INSERT OR IGNORE INTO workspace_config_aliases(config_id, alias, is_current) VALUES (?, ?, ?)",
            (config_id, alias.strip(), int(current)),
        )

    def _config(self, c: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
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
            "sortOrder": int(row["sort_order"]),
            "isEnabled": bool(row["is_enabled"]),
        }

    @staticmethod
    def _project(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "professionId": int(row["profession_id"]),
            "code": str(row["code"]),
            "name": str(row["name"]),
            "description": str(row["description"]),
            "engineCode": str(row["engine_code"]),
            "sortOrder": int(row["sort_order"]),
            "isEnabled": bool(row["is_enabled"]),
        }
