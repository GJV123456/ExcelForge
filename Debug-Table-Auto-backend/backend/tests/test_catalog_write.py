from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _client(tmp_path: Path) -> TestClient:
    client = TestClient(create_app(Settings(mode="formal", database_path=tmp_path / "catalog.sqlite3")))
    response = client.post(
        "/api/auth/register",
        json={
            "username": "admin",
            "password": "secret123",
            "confirmPassword": "secret123",
            "displayName": "管理员",
            "agree": True,
        },
    )
    if response.status_code == 200:
        client.headers.update({"Authorization": f"Bearer {response.json()['data']['token']}"})
    return client


def test_catalog_write_cycle(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        eq = client.post(
            "/api/catalog/equipment-types",
            json={
                "code": "SMOKE",
                "name": "烟感",
                "description": "",
                "sortOrder": 1,
                "isEnabled": True,
            },
        )
        assert eq.status_code == 200
        eq_id = eq.json()["data"]["id"]

        fas = client.post(
            "/api/catalog/disciplines",
            json={
                "code": "FAS",
                "name": "FAS",
                "description": "",
                "sortOrder": 1,
                "isEnabled": True,
            },
        )
        iscs = client.post(
            "/api/catalog/disciplines",
            json={
                "code": "ISCS",
                "name": "综合监控",
                "description": "",
                "sortOrder": 2,
                "isEnabled": True,
            },
        )
        assert fas.status_code == 200
        assert iscs.status_code == 200
        fas_id = fas.json()["data"]["id"]

        content = client.post(
            "/api/catalog/test-contents",
            json={
                "equipmentTypeId": eq_id,
                "equipmentSubtype": "",
                "code": "SMOKE_STANDARD",
                "content": "站厅B端车控室烟感",
                "description": "",
                "revision": 1,
                "sortOrder": 1,
                "isEnabled": True,
                "operationSteps": [
                    {
                        "description": "现场用烟枪吹烟，触发烟感报警",
                        "ratioChange": "否",
                        "sortOrder": 1,
                        "isEnabled": True,
                        "results": [
                            {
                                "description": "现场：烟感灯亮红色",
                                "sortOrder": 1,
                                "isEnabled": True,
                                "responsibleDisciplineIds": [fas_id],
                            }
                        ],
                    }
                ],
            },
        )
        assert content.status_code == 200
        content_id = content.json()["data"]["id"]
        assert content.json()["data"]["equipmentTypeId"] == eq_id
        assert content.json()["data"]["equipmentSubtype"] == ""

        fetched = client.get(f"/api/catalog/test-contents/{content_id}")
        assert fetched.status_code == 200
        assert fetched.json()["data"]["operationSteps"][0]["results"][0]["responsibleDisciplines"][0]["code"] == "FAS"

        duplicate = client.post(
            "/api/catalog/test-contents",
            json={
                "equipmentTypeId": eq_id,
                "equipmentSubtype": "",
                "code": "SMOKE_DUP",
                "content": "重复结果测试",
                "description": "",
                "revision": 1,
                "sortOrder": 2,
                "isEnabled": True,
                "operationSteps": [
                    {
                        "description": "步骤",
                        "ratioChange": "否",
                        "sortOrder": 1,
                        "isEnabled": True,
                        "results": [
                            {
                                "description": "结果",
                                "sortOrder": 1,
                                "isEnabled": True,
                                "responsibleDisciplineIds": [fas_id, fas_id],
                            }
                        ],
                    }
                ],
            },
        )
        assert duplicate.status_code == 422

        delete_used = client.delete(f"/api/catalog/disciplines/{fas_id}")
        assert delete_used.status_code == 409
        assert delete_used.json()["code"] == "CATALOG_DISCIPLINE_IN_USE"

        delete_content = client.delete(f"/api/catalog/test-contents/{content_id}")
        assert delete_content.status_code == 204

        delete_discipline = client.delete(f"/api/catalog/disciplines/{fas_id}")
    assert delete_discipline.status_code == 204


def test_new_equipment_type_generates_codes_and_saves_nested_catalog(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        response = client.post(
            "/api/catalog/equipment-types",
            json={
                "name": "新型设备",
                "description": "用于验证层级配置",
                "sortOrder": 1,
                "isEnabled": True,
                "subtypes": [
                    {
                        "name": "主机",
                        "sortOrder": 1,
                        "isEnabled": True,
                        "statuses": ["预警", "故障"],
                    },
                    {
                        "name": "探测器",
                        "sortOrder": 2,
                        "isEnabled": True,
                        "statuses": [],
                    },
                ],
            },
        )
        assert response.status_code == 200
        equipment = response.json()["data"]
        assert equipment["code"].startswith("TYPE_")

        hierarchy = client.get("/api/catalog/equipment-hierarchy")
        assert hierarchy.status_code == 200
        created = next(item for item in hierarchy.json()["data"] if item["id"] == equipment["id"])
        assert [item["name"] for item in created["subtypes"]] == ["主机", "探测器"]
        assert created["subtypes"][0]["code"].startswith(f"{equipment['code']}_SUBTYPE_")
        assert created["subtypes"][0]["statuses"] == ["预警", "故障"]

        discipline = client.post(
            "/api/catalog/disciplines",
            json={"name": "自动化", "sortOrder": 1, "isEnabled": True},
        )
        assert discipline.status_code == 200
        assert discipline.json()["data"]["code"].startswith("DISC_")
        rule = client.post(
            "/api/catalog/test-contents",
            json={
                "equipmentTypeId": equipment["id"],
                "content": "新型设备测试",
                "sortOrder": 1,
                "isEnabled": True,
                "operationSteps": [
                    {
                        "description": "执行测试",
                        "ratioChange": "否",
                        "sortOrder": 1,
                        "results": [
                            {
                                "description": "收到反馈",
                                "sortOrder": 1,
                                "responsibleDisciplineIds": [discipline.json()["data"]["id"]],
                            }
                        ],
                    }
                ],
            },
        )
        assert rule.status_code == 200
        assert rule.json()["data"]["code"].startswith("RULE_")

        missing_name = client.post(
            "/api/catalog/equipment-types",
            json={
                "name": "不完整设备",
                "sortOrder": 2,
                "isEnabled": True,
                "subtypes": [{"name": "", "sortOrder": 1, "statuses": []}],
            },
        )
        assert missing_name.status_code == 422
        assert not any(item["name"] == "不完整设备" for item in hierarchy.json()["data"])


def test_equipment_hierarchy_can_be_edited_and_deletes_are_protected(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        created = client.post(
            "/api/catalog/equipment-types",
            json={
                "name": "可编辑设备",
                "sortOrder": 1,
                "subtypes": [
                    {
                        "name": "旧子类型",
                        "sortOrder": 1,
                        "statuses": ["旧状态", "保留状态"],
                    },
                    {"name": "待删除子类型", "sortOrder": 2, "statuses": []},
                ],
            },
        ).json()["data"]
        hierarchy = client.get("/api/catalog/equipment-hierarchy").json()["data"]
        item = next(value for value in hierarchy if value["id"] == created["id"])
        subtype = item["subtypes"][0]
        updated = client.put(
            f"/api/catalog/equipment-types/{created['id']}",
            json={
                "name": "可编辑设备",
                "sortOrder": 1,
                "subtypes": [
                    {
                        "id": subtype["id"],
                        "name": "新子类型",
                        "sortOrder": 1,
                        "statuses": ["保留状态", "新状态"],
                    }
                ],
            },
        )
        assert updated.status_code == 200
        refreshed = next(
            value
            for value in client.get("/api/catalog/equipment-hierarchy").json()["data"]
            if value["id"] == created["id"]
        )
        assert [value["name"] for value in refreshed["subtypes"]] == ["新子类型"]
        assert refreshed["subtypes"][0]["statuses"] == ["保留状态", "新状态"]

        discipline = client.post(
            "/api/catalog/disciplines",
            json={"name": "自动化", "sortOrder": 1},
        ).json()["data"]
        rule = client.post(
            "/api/catalog/test-contents",
            json={
                "equipmentTypeId": created["id"],
                "content": "新子类型规则",
                "equipmentSubtype": "新子类型",
                "equipmentStatus": "保留状态",
                "sortOrder": 1,
                "operationSteps": [
                    {
                        "description": "执行",
                        "ratioChange": "否",
                        "sortOrder": 1,
                        "results": [
                            {
                                "description": "结果",
                                "sortOrder": 1,
                                "responsibleDisciplineIds": [discipline["id"]],
                            }
                        ],
                    }
                ],
            },
        ).json()["data"]
        protected = client.delete(f"/api/catalog/equipment-subtypes/{subtype['id']}")
        assert protected.status_code == 409
        assert protected.json()["code"] == "CATALOG_EQUIPMENT_SUBTYPE_IN_USE"
        rename = client.put(
            f"/api/catalog/equipment-types/{created['id']}",
            json={
                "name": "可编辑设备",
                "sortOrder": 1,
                "subtypes": [
                    {
                        "id": subtype["id"],
                        "name": "不能重命名",
                        "sortOrder": 1,
                        "statuses": ["保留状态"],
                    }
                ],
            },
        )
        assert rename.status_code == 200
        assert rule["equipmentStatus"] == "保留状态"
        refreshed_rule = client.get(f"/api/catalog/test-contents/{rule['id']}").json()["data"]
        assert refreshed_rule["equipmentSubtype"] == "不能重命名"


def test_subtype_and_status_rules_are_independent(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        equipment = client.post(
            "/api/catalog/equipment-types",
            json={
                "code": "MONITOR",
                "name": "监视模块",
                "description": "",
                "sortOrder": 1,
                "isEnabled": True,
            },
        )
        assert equipment.status_code == 200
        equipment_id = equipment.json()["data"]["id"]

        discipline = client.post(
            "/api/catalog/disciplines",
            json={
                "code": "AUTO",
                "name": "自动化",
                "description": "",
                "sortOrder": 1,
                "isEnabled": True,
            },
        )
        assert discipline.status_code == 200
        discipline_id = discipline.json()["data"]["id"]

        def create_rule(code: str, status: str, description: str) -> dict:
            response = client.post(
                "/api/catalog/test-contents",
                json={
                    "equipmentTypeId": equipment_id,
                    "code": code,
                    "content": description,
                    "equipmentSubtype": "吸气式主机",
                    "equipmentStatus": status,
                    "description": "",
                    "revision": 1,
                    "sortOrder": 1,
                    "isEnabled": True,
                    "operationSteps": [
                        {
                            "description": f"测试{status}",
                            "ratioChange": "否",
                            "sortOrder": 1,
                            "isEnabled": True,
                            "results": [
                                {
                                    "description": f"结果{status}",
                                    "sortOrder": 1,
                                    "isEnabled": True,
                                    "responsibleDisciplineIds": [discipline_id],
                                }
                            ],
                        }
                    ],
                },
            )
            assert response.status_code == 200
            return response.json()["data"]

        rule = create_rule("ASPIRATION_WARNING", "预警", "吸气式主机预警测试")
        fire_rule = create_rule("ASPIRATION_FIRE", "火警", "吸气式主机火警测试")

        assert rule["equipmentType"]["name"] == "监视模块"
        assert rule["equipmentSubtype"] == "吸气式主机"
        assert rule["equipmentStatus"] == "预警"
        assert fire_rule["equipmentStatus"] == "火警"

        rules = client.get("/api/catalog/test-contents?equipmentType=监视模块")
        assert rules.status_code == 200
        assert {item["equipmentStatus"] for item in rules.json()["data"]} == {"预警", "火警"}

        filtered = client.get(
            "/api/catalog/test-contents",
            params={
                "equipmentType": "监视模块",
                "equipmentSubtype": "吸气式主机",
                "equipmentStatus": "火警",
            },
        )
        assert filtered.status_code == 200
        assert [item["id"] for item in filtered.json()["data"]] == [fire_rule["id"]]

        updated_payload = {
            "code": fire_rule["code"],
            "content": fire_rule["content"],
            "description": fire_rule["description"],
            "revision": fire_rule["revision"],
            "sortOrder": fire_rule["sortOrder"],
            "isEnabled": fire_rule["isEnabled"],
            "equipmentTypeId": equipment_id,
            "equipmentSubtype": "吸气式主机",
            "equipmentStatus": "火警",
            "operationSteps": [
                {
                    "description": "修改后的火警步骤",
                    "ratioChange": "否",
                    "sortOrder": 1,
                    "isEnabled": True,
                    "results": [
                        {
                            "description": "修改后的火警结果",
                            "sortOrder": 1,
                            "isEnabled": True,
                            "responsibleDisciplineIds": [discipline_id],
                        }
                    ],
                }
            ],
        }
        updated = client.put(f"/api/catalog/test-contents/{fire_rule['id']}", json=updated_payload)
        assert updated.status_code == 200
        assert updated.json()["data"]["equipmentStatus"] == "火警"

        warning = client.get(f"/api/catalog/test-contents/{rule['id']}")
        assert warning.status_code == 200
        assert warning.json()["data"]["equipmentStatus"] == "预警"
    assert warning.json()["data"]["operationSteps"][0]["description"] == "测试预警"


def test_subtype_statuses_can_be_updated_without_deleting_used_rules(tmp_path: Path) -> None:
    database_path = tmp_path / "catalog.sqlite3"
    with _client(tmp_path) as client:
        client.get("/api/catalog/test-contents")
        equipment = client.post(
            "/api/catalog/equipment-types",
            json={"code": "CONTROL", "name": "控制模块", "sortOrder": 1, "isEnabled": True},
        )
        equipment_id = equipment.json()["data"]["id"]
        connection = sqlite3.connect(database_path)
        connection.execute(
            "INSERT INTO equipment_type_subtypes(parent_equipment_type_id, code, name, sort_order) VALUES (?, ?, ?, ?)",
            (equipment_id, "CONTROL_01", "主机手自动、人工确认", 1),
        )
        subtype_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.commit()
        connection.close()

        updated = client.put(
            f"/api/catalog/equipment-subtypes/{subtype_id}/statuses",
            json={"statuses": ["FAS主机人工确定按钮", "FAS主机自动状态按钮"]},
        )
        assert updated.status_code == 200
        assert updated.json()["data"]["statuses"] == [
            "FAS主机人工确定按钮",
            "FAS主机自动状态按钮",
        ]

        duplicate = client.put(
            f"/api/catalog/equipment-subtypes/{subtype_id}/statuses",
            json={"statuses": ["FAS主机人工确定按钮", "fas主机人工确定按钮"]},
        )
        assert duplicate.status_code == 422
