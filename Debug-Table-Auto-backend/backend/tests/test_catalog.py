from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.db.catalog import SCHEMA_VERSION, CatalogRepository
from app.main import create_app


def _client(database_path: Path) -> TestClient:
    client = TestClient(create_app(Settings(mode="formal", database_path=database_path)))
    response = client.post(
        "/api/auth/register",
        json={"username": "admin", "password": "secret123", "confirmPassword": "secret123", "displayName": "管理员", "agree": True},
    )
    if response.status_code == 200:
        client.headers.update({"Authorization": f"Bearer {response.json()['data']['token']}"})
    return client


def _seed_catalog(database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            INSERT INTO equipment_types(id, code, name, sort_order, is_enabled)
            VALUES
                (1, 'SMOKE', '烟感', 2, 1),
                (2, 'TEMP', '温感', 1, 0);

            INSERT INTO test_contents(
                id, code, equipment_type_id, content, sort_order, is_enabled
            ) VALUES
                (1, 'SMOKE_STANDARD', 1, '站厅B端车控室烟感', 1, 1),
                (2, 'SMOKE_DISABLED', 1, '停用烟感规则', 2, 0),
                (3, 'TEMP_STANDARD', 2, '温感规则', 1, 1);

            INSERT INTO operation_steps(
                id, test_content_id, description, ratio_change, sort_order, is_enabled
            ) VALUES
                (1, 1, '触发设备报警', '否', 2, 1),
                (2, 1, '停用操作步骤', '是', 1, 0);

            INSERT INTO result_outputs(
                id, operation_step_id, description, sort_order, is_enabled
            ) VALUES
                (1, 1, '系统正确显示报警', 1, 1),
                (2, 1, '停用结果', 2, 0);

            INSERT INTO disciplines(id, code, name, sort_order, is_enabled)
            VALUES
                (1, 'FAS', 'FAS', 2, 1),
                (2, 'ISCS', '综合监控', 1, 1),
                (3, 'DISABLED', '停用专业', 3, 0);

            INSERT INTO result_output_disciplines(
                result_output_id, discipline_id, sort_order
            ) VALUES
                (1, 2, 1),
                (1, 1, 2),
                (1, 3, 3);
            """
        )


def test_catalog_first_request_creates_empty_versioned_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "catalog.sqlite3"
    assert not database_path.exists()

    with _client(database_path) as client:
        response = client.get("/api/catalog/test-contents")

    assert response.status_code == 200
    assert response.json() == {"data": [], "meta": {"count": 0}}
    assert database_path.is_file()
    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        version = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
        columns = {
            table: {
                row[1] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
            }
            for table in (
                "equipment_types",
                "test_contents",
                "operation_steps",
                "result_outputs",
                "disciplines",
                "result_output_disciplines",
                "generation_runs",
                "generation_test_contents",
                "generation_operation_steps",
                "generation_result_outputs",
                "generation_result_disciplines",
            )
        }

    assert {
        "schema_migrations",
        "equipment_types",
        "test_contents",
        "operation_steps",
        "result_outputs",
        "disciplines",
        "result_output_disciplines",
        "generation_runs",
        "generation_test_contents",
        "generation_operation_steps",
        "generation_result_outputs",
        "generation_result_disciplines",
    }.issubset(table_names)
    assert version == SCHEMA_VERSION
    assert columns == {
        "equipment_types": {
            "integration_code",
            "id",
            "code",
            "name",
            "description",
            "sort_order",
            "is_enabled",
            "created_at",
            "updated_at",
        },
        "test_contents": {
            "integration_code",
            "id",
            "code",
            "equipment_type_id",
            "equipment_subtype",
            "equipment_status",
            "content",
            "description",
            "revision",
            "sort_order",
            "is_enabled",
            "created_at",
            "updated_at",
        },
        "operation_steps": {
            "id",
            "test_content_id",
            "description",
            "ratio_change",
            "sort_order",
            "is_enabled",
            "created_at",
            "updated_at",
        },
        "result_outputs": {
            "id",
            "operation_step_id",
            "description",
            "sort_order",
            "is_enabled",
            "created_at",
            "updated_at",
        },
        "disciplines": {
            "integration_code",
            "id",
            "code",
            "name",
            "description",
            "sort_order",
            "is_enabled",
            "created_at",
            "updated_at",
        },
        "result_output_disciplines": {
            "result_output_id",
            "discipline_id",
            "sort_order",
        },
        "generation_runs": {
            "id",
            "integration_code",
            "request_id",
            "generated_at",
            "filename",
            "output_sha256",
            "output_blob",
            "location_type",
            "direction",
            "start_station",
            "end_station",
            "test_content_count",
            "operation_step_count",
            "result_output_count",
            "discipline_count",
            "created_at",
        },
        "generation_test_contents": {
            "id",
            "generation_id",
            "sequence_index",
            "sort_index",
            "generated_content",
            "equipment_code",
            "equipment_type",
            "excel_row_number",
        },
        "generation_operation_steps": {
            "id",
            "generation_test_content_id",
            "sequence_index",
            "description",
            "ratio_change",
            "excel_row_number",
        },
        "generation_result_outputs": {
            "id",
            "generation_operation_step_id",
            "sequence_index",
            "description",
            "excel_row_number",
        },
        "generation_result_disciplines": {
            "generation_result_output_id",
            "sequence_index",
            "discipline_name",
        },
    }


def test_catalog_upgrades_existing_database_without_losing_rules(tmp_path: Path) -> None:
    database_path = tmp_path / "catalog.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO schema_migrations(version) VALUES (1);
            CREATE TABLE preserved_rule (value TEXT NOT NULL);
            INSERT INTO preserved_rule(value) VALUES ('保留');
            """
        )

    with _client(database_path) as client:
        response = client.get("/api/generations")

    assert response.status_code == 200
    with sqlite3.connect(database_path) as connection:
        version = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
        preserved = connection.execute("SELECT value FROM preserved_rule").fetchone()[0]
    assert version == SCHEMA_VERSION
    assert preserved == "保留"


def test_catalog_migrates_t19_door_release_names_to_door_access(tmp_path: Path) -> None:
    database_path = tmp_path / "catalog.sqlite3"
    repository = CatalogRepository(database_path)
    repository.ensure_schema()
    with sqlite3.connect(database_path) as connection:
        connection.execute("DELETE FROM schema_migrations WHERE version = 9")
        connection.execute("DELETE FROM schema_migrations WHERE version = 10")
        connection.executemany(
            "INSERT INTO equipment_types(code, name, integration_code) VALUES (?, ?, 'T19')",
            [
                ("MONITOR", "监视模块"),
                ("CONTROL", "控制模块"),
                ("DOOR", "门禁释放"),
            ],
        )
        parent_ids = dict(connection.execute(
            "SELECT name, id FROM equipment_types WHERE name IN ('监视模块', '控制模块')"
        ).fetchall())
        connection.executemany(
            "INSERT INTO equipment_type_subtypes(parent_equipment_type_id, code, name) "
            "VALUES (?, ?, '门禁释放')",
            [
                (parent_ids["监视模块"], "MONITOR_DOOR"),
                (parent_ids["控制模块"], "CONTROL_DOOR"),
            ],
        )
        door_type_id = connection.execute(
            "SELECT id FROM equipment_types WHERE code = 'DOOR'"
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO test_contents(code, equipment_type_id, content, equipment_subtype, integration_code) "
            "VALUES ('DOOR_RULE', ?, '门禁规则', '门禁释放', 'T19')",
            (door_type_id,),
        )
        test_content_id = connection.execute(
            "SELECT id FROM test_contents WHERE code = 'DOOR_RULE'"
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO test_content_selectors(test_content_id, equipment_type, equipment_subtype) "
            "VALUES (?, '监视模块', '门禁释放')",
            (test_content_id,),
        )

    repository.ensure_schema()
    with sqlite3.connect(database_path) as connection:
        renamed_type = connection.execute(
            "SELECT name FROM equipment_types WHERE code = 'DOOR'"
        ).fetchone()[0]
        renamed_children = connection.execute(
            "SELECT COUNT(*) FROM equipment_type_subtypes WHERE name = '门禁'"
        ).fetchone()[0]
        renamed_rule_subtype = connection.execute(
            "SELECT equipment_subtype FROM test_contents WHERE code = 'DOOR_RULE'"
        ).fetchone()[0]
        renamed_selector = connection.execute(
            "SELECT equipment_type, equipment_subtype FROM test_content_selectors "
            "WHERE test_content_id = ?",
            (test_content_id,),
        ).fetchone()

    assert renamed_type == "门禁"
    assert renamed_children == 2
    assert renamed_rule_subtype == "门禁"
    assert tuple(renamed_selector) == ("监视模块", "门禁")


def test_catalog_returns_enabled_nested_rules_in_database_order(tmp_path: Path) -> None:
    database_path = tmp_path / "catalog.sqlite3"
    with _client(database_path) as client:
        assert client.get("/api/catalog/test-contents").status_code == 200
        _seed_catalog(database_path)
        response = client.get("/api/catalog/test-contents")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"] == {"count": 1}
    content = body["data"][0]
    assert content["code"] == "SMOKE_STANDARD"
    assert content["equipmentTypeId"] == 1
    assert content["equipmentSubtype"] == ""
    assert content["equipmentType"] == {"id": 1, "code": "SMOKE", "name": "烟感"}
    assert content["sortOrder"] == 1
    assert [step["description"] for step in content["operationSteps"]] == ["触发设备报警"]
    result = content["operationSteps"][0]["results"][0]
    assert result["description"] == "系统正确显示报警"
    assert [item["code"] for item in result["responsibleDisciplines"]] == ["ISCS", "FAS"]


def test_catalog_filters_by_equipment_code_or_name(tmp_path: Path) -> None:
    database_path = tmp_path / "catalog.sqlite3"
    with _client(database_path) as client:
        client.get("/api/catalog/test-contents")
        _seed_catalog(database_path)
        by_code = client.get(
            "/api/catalog/test-contents", params={"equipmentType": "smoke"}
        )
        disabled_by_name = client.get(
            "/api/catalog/test-contents", params={"equipmentType": "温感"}
        )
        all_by_name = client.get(
            "/api/catalog/test-contents",
            params={"equipmentType": "温感", "includeDisabled": "true"},
        )

    assert [item["code"] for item in by_code.json()["data"]] == ["SMOKE_STANDARD"]
    assert disabled_by_name.json()["data"] == []
    assert [item["code"] for item in all_by_name.json()["data"]] == ["TEMP_STANDARD"]


def test_catalog_can_include_disabled_records_explicitly(tmp_path: Path) -> None:
    database_path = tmp_path / "catalog.sqlite3"
    with _client(database_path) as client:
        client.get("/api/catalog/test-contents")
        _seed_catalog(database_path)
        types_response = client.get(
            "/api/catalog/equipment-types", params={"includeDisabled": "true"}
        )
        contents_response = client.get(
            "/api/catalog/test-contents",
            params={"equipmentType": "SMOKE", "includeDisabled": "true"},
        )

    assert [item["code"] for item in types_response.json()["data"]] == ["TEMP", "SMOKE"]
    contents = contents_response.json()["data"]
    assert [item["code"] for item in contents] == ["SMOKE_STANDARD", "SMOKE_DISABLED"]
    assert [step["description"] for step in contents[0]["operationSteps"]] == [
        "停用操作步骤",
        "触发设备报警",
    ]
    enabled_step = contents[0]["operationSteps"][1]
    assert contents[0]["operationSteps"][0]["isEnabled"] is False
    assert enabled_step["isEnabled"] is True
    assert [result["description"] for result in enabled_step["results"]] == [
        "系统正确显示报警",
        "停用结果",
    ]
    assert enabled_step["results"][1]["isEnabled"] is False
    assert [
        discipline["code"]
        for discipline in enabled_step["results"][0]["responsibleDisciplines"]
    ] == ["ISCS", "FAS", "DISABLED"]


def test_equipment_hierarchy_returns_parent_and_subtypes(tmp_path: Path) -> None:
    database_path = tmp_path / "catalog.sqlite3"
    with _client(database_path) as client:
        client.get("/api/catalog/test-contents")
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                """
                INSERT INTO equipment_types(id, code, name, sort_order, is_enabled)
                VALUES (10, 'FIRE', '防火阀', 1, 1)
                """
            )
            connection.execute(
                """
                INSERT INTO equipment_type_subtypes(
                    parent_equipment_type_id, code, name, sort_order, is_enabled
                ) VALUES (10, 'MANUAL', '手动防火阀', 1, 1)
                """
            )
        response = client.get("/api/catalog/equipment-hierarchy")
        subtype_response = client.get("/api/catalog/equipment-types/10/subtypes")

    assert response.status_code == 200
    parent = next(item for item in response.json()["data"] if item["name"] == "防火阀")
    assert [item["name"] for item in parent["subtypes"]] == ["手动防火阀"]
    assert subtype_response.json()["meta"] == {"count": 1}


def test_renaming_equipment_subtype_updates_existing_rule_references(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "catalog.sqlite3"
    with _client(database_path) as client:
        client.get("/api/catalog/test-contents")
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "INSERT INTO equipment_types(id, code, name) VALUES (10, 'GAS', '特殊模块')"
            )
            connection.execute(
                """
                INSERT INTO equipment_type_subtypes(
                    id, parent_equipment_type_id, code, name
                ) VALUES (20, 10, 'GAS_TEST', '气灭测试')
                """
            )
            connection.execute(
                """
                INSERT INTO test_contents(
                    code, equipment_type_id, content, equipment_subtype
                ) VALUES ('GAS_RULE', 10, '气灭测试步骤', '气灭测试')
                """
            )
            rule_id = connection.execute(
                "SELECT id FROM test_contents WHERE code = 'GAS_RULE'"
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO test_content_selectors(
                    test_content_id, equipment_type, equipment_subtype
                ) VALUES (?, '特殊模块', '气灭测试')
                """,
                (rule_id,),
            )

        response = client.put(
            "/api/catalog/equipment-types/10",
            json={
                "name": "特殊模块",
                "description": "",
                "sortOrder": 1,
                "isEnabled": True,
                "subtypes": [
                    {
                        "id": 20,
                        "name": "气灭房功能测试",
                        "sortOrder": 1,
                        "isEnabled": True,
                        "statuses": [],
                    }
                ],
            },
        )

    assert response.status_code == 200
    with sqlite3.connect(database_path) as connection:
        rule_subtype = connection.execute(
            "SELECT equipment_subtype FROM test_contents WHERE code = 'GAS_RULE'"
        ).fetchone()[0]
        selector_subtype = connection.execute(
            "SELECT equipment_subtype FROM test_content_selectors WHERE test_content_id = ?",
            (rule_id,),
        ).fetchone()[0]
    assert rule_subtype == "气灭房功能测试"
    assert selector_subtype == "气灭房功能测试"


def test_catalog_detail_returns_one_rule_or_404(tmp_path: Path) -> None:
    database_path = tmp_path / "catalog.sqlite3"
    with _client(database_path) as client:
        client.get("/api/catalog/test-contents")
        _seed_catalog(database_path)
        found = client.get("/api/catalog/test-contents/1")
        missing = client.get("/api/catalog/test-contents/999")
        disabled = client.get("/api/catalog/test-contents/2")

    assert found.status_code == 200
    assert found.json()["data"]["code"] == "SMOKE_STANDARD"
    assert missing.status_code == 404
    assert missing.json()["code"] == "CATALOG_TEST_CONTENT_NOT_FOUND"
    assert disabled.status_code == 404


def test_catalog_data_isolated_by_integration_database(tmp_path: Path) -> None:
    database_path = tmp_path / "catalog.sqlite3"
    with _client(database_path) as client:
        created = client.post(
            "/api/catalog/equipment-types",
            params={"integrationCode": "T20"},
            json={
                "code": "ONLY_T20",
                "name": "仅T20设备",
                "description": "",
                "sortOrder": 1,
                "isEnabled": True,
            },
        )
        assert created.status_code == 200
        t20 = client.get(
            "/api/catalog/equipment-types", params={"integrationCode": "T20"}
        )
        t19 = client.get(
            "/api/catalog/equipment-types", params={"integrationCode": "T19"}
        )

    assert any(item["code"] == "ONLY_T20" for item in t20.json()["data"])
    assert all(item["code"] != "ONLY_T20" for item in t19.json()["data"])
    assert (tmp_path / "catalog.T20.sqlite3").is_file()


def test_legacy_catalog_is_limited_to_nine_line_automation_accounts(tmp_path: Path) -> None:
    database_path = tmp_path / "catalog.sqlite3"
    with _client(database_path) as client:
        with sqlite3.connect(database_path) as connection:
            line_id = connection.execute(
                "SELECT id FROM workspace_lines WHERE code = '9' COLLATE NOCASE"
            ).fetchone()[0]
            profession_id = connection.execute(
                "SELECT id FROM workspace_professions WHERE code = 'ZDH' COLLATE NOCASE"
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO workspace_lines(code, name) VALUES ('10', '10号线')"
            )
            other_line_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
            connection.execute(
                "INSERT INTO workspace_professions(code, name) VALUES ('TX', '通信')"
            )
            other_profession_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
            connection.execute(
                "UPDATE auth_users SET role = 'line_admin', line_id = ? WHERE username = 'admin'",
                (line_id,),
            )

        permitted_scope = {"lineId": line_id, "professionId": profession_id}
        assert client.get("/api/catalog/equipment-types", params=permitted_scope).status_code == 200
        assert client.get(
            "/api/catalog/equipment-types",
            params={"lineId": other_line_id, "professionId": profession_id},
        ).status_code == 403
        assert client.get(
            "/api/catalog/equipment-types",
            params={"lineId": line_id, "professionId": other_profession_id},
        ).status_code == 403

        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "UPDATE auth_users SET role = 'professional_configurator', profession_id = ? WHERE username = 'admin'",
                (profession_id,),
            )
            connection.commit()
        assert client.get("/api/catalog/equipment-types", params=permitted_scope).status_code == 200
        assert client.get(
            "/api/catalog/equipment-types",
            params={"lineId": other_line_id, "professionId": profession_id},
        ).status_code == 403



