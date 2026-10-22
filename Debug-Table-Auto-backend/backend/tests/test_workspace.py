from __future__ import annotations

import sqlite3
from pathlib import Path

import xlrd
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _login(client: TestClient, username: str, password: str = "secret123") -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password, "agree": True, "remember": False},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['token']}"}


def test_workspace_config_ids_aliases_and_scope_permissions(tmp_path: Path) -> None:
    with TestClient(create_app(Settings(mode="formal", database_path=tmp_path / "workspace.sqlite3"))) as client:
        registered = client.post(
            "/api/auth/register",
            json={
                "username": "admin",
                "password": "secret123",
                "confirmPassword": "secret123",
                "displayName": "管理员",
                "agree": True,
            },
        )
        admin = {"Authorization": f"Bearer {registered.json()['data']['token']}"}
        context = client.get("/api/workspace/context", headers=admin).json()["data"]
        line = context["lines"][0]
        profession = context["professions"][0]
        project = context["projects"][0]
        assert context["currentUser"]["role"] == "super_admin"
        assert (
            client.put(
                f"/api/workspace/lines/{line['id']}",
                headers=admin,
                json={"code": line["code"], "name": "线路名称测试", "sortOrder": 1},
            ).status_code
            == 200
        )
        assert (
            client.put(
                f"/api/workspace/professions/{profession['id']}",
                headers=admin,
                json={"code": profession["code"], "name": "专业名称测试", "sortOrder": 1},
            ).status_code
            == 200
        )
        assert (
            client.put(
                f"/api/workspace/projects/{project['id']}",
                headers=admin,
                json={
                    "professionId": profession["id"],
                    "code": project["code"],
                    "name": "项目名称测试",
                    "engineCode": project["engineCode"],
                    "sortOrder": 1,
                },
            ).status_code
            == 200
        )
        scope = {"lineId": line["id"], "professionId": profession["id"], "projectId": project["id"]}
        source_subitem = client.post(
            "/api/workspace/debug-items",
            headers=admin,
            json={"scope": scope, "category": "debug_subitems", "name": "FAS设备信息监视"},
        )
        assert source_subitem.status_code == 200, source_subitem.text
        source_division = client.post(
            "/api/workspace/debug-items",
            headers=admin,
            json={
                "scope": scope,
                "category": "debug_divisions",
                "parentId": source_subitem.json()["data"]["id"],
                "name": "吸气式主机",
            },
        )
        assert source_division.status_code == 200, source_division.text
        payload = {
            "scope": scope,
            "configCode": "FAS-垂梯-状态反馈",
            "deviceType": "垂梯",
            "debugSubitemId": source_subitem.json()["data"]["id"],
            "debugDivisionId": source_division.json()["data"]["id"],
            "steps": [
                {
                    "description": "模拟状态",
                    "ratioChange": "否",
                    "results": [{"description": "显示状态", "responsibleDisciplines": ["自动化"]}],
                }
            ],
        }
        created = client.post("/api/workspace/configs", headers=admin, json=payload)
        assert created.status_code == 200
        assert created.json()["data"]["businessId"] == "9-ZDH-T19-001"
        config_id = created.json()["data"]["id"]

        # The configuration editor sends result descriptions and discipline
        # names, while ordering and enabled state belong to steps/configs.
        frontend_shape = {
            **payload,
            "configCode": "FAS-垂梯-归首控制",
            "steps": [
                {
                    "description": "发送归首控制",
                    "ratioChange": "否",
                    "sortOrder": 1,
                    "isEnabled": True,
                    "results": [{"description": "垂梯返回归首状态", "responsibleDisciplines": []}],
                }
            ],
        }
        created_from_editor = client.post("/api/workspace/configs", headers=admin, json=frontend_shape)
        assert created_from_editor.status_code == 200, created_from_editor.text
        assert created_from_editor.json()["data"]["steps"][0]["results"][0]["description"] == "垂梯返回归首状态"
        disabled = client.post(
            f"/api/workspace/configs/{created_from_editor.json()['data']['id']}/status",
            headers=admin,
            params={"enabled": False},
        )
        assert disabled.status_code == 200
        assert disabled.json()["data"]["isEnabled"] is False
        listed_configs = client.get(
            "/api/workspace/configs",
            headers=admin,
            params={**scope, "includeDisabled": True},
        ).json()["data"]
        disabled_config = next(
            item for item in listed_configs if item["id"] == created_from_editor.json()["data"]["id"]
        )
        assert disabled_config["isEnabled"] is False
        reenabled = client.post(
            f"/api/workspace/configs/{created_from_editor.json()['data']['id']}/status",
            headers=admin,
            params={"enabled": True},
        )
        assert reenabled.status_code == 200
        assert reenabled.json()["data"]["isEnabled"] is True

        updated = {**payload, "configCode": "FAS-垂梯-运行状态反馈"}
        assert client.put(f"/api/workspace/configs/{config_id}", headers=admin, json=updated).status_code == 200
        resolved = client.get("/api/workspace/configs", headers=admin, params=scope).json()["data"][0]
        assert "FAS-垂梯-状态反馈" in resolved["aliases"]

        line_two = client.post("/api/workspace/lines", headers=admin, json={"code": "2", "name": "2号线"}).json()[
            "data"
        ]
        target_project = client.post(
            "/api/workspace/projects",
            headers=admin,
            json={
                "lineId": line_two["id"],
                "professionId": profession["id"],
                "code": project["code"],
                "name": project["name"],
                "engineCode": project["engineCode"],
                "sortOrder": 1,
            },
        ).json()["data"]
        target = {**scope, "lineId": line_two["id"], "projectId": target_project["id"]}
        missing_hierarchy_copy = client.post(
            "/api/workspace/configs/copy",
            headers=admin,
            json={"sourceConfigId": config_id, "target": target},
        )
        assert missing_hierarchy_copy.status_code == 409
        assert missing_hierarchy_copy.json()["code"] == "WORKSPACE_COPY_DEBUG_HIERARCHY_REQUIRED"
        target_subitem_seed = client.post(
            "/api/workspace/debug-items",
            headers=admin,
            json={"scope": target, "category": "debug_subitems", "name": "FAS设备信息监视"},
        )
        assert target_subitem_seed.status_code == 200, target_subitem_seed.text
        copied_without_division = client.post(
            "/api/workspace/configs/copy",
            headers=admin,
            json={"sourceConfigId": config_id, "target": target},
        )
        assert copied_without_division.status_code == 200, copied_without_division.text
        copied_config = copied_without_division.json()["data"][0]
        assert copied_config["debugSubitemId"] == target_subitem_seed.json()["data"]["id"]
        assert copied_config["debugDivisionId"] is None
        target_division_seed = client.post(
            "/api/workspace/debug-items",
            headers=admin,
            json={
                "scope": target,
                "category": "debug_divisions",
                "parentId": target_subitem_seed.json()["data"]["id"],
                "name": "吸气式主机",
            },
        )
        assert target_division_seed.status_code == 200, target_division_seed.text
        copied = client.post(
            "/api/workspace/configs/copy",
            headers=admin,
            json={"sourceConfigId": config_id, "target": target},
        )
        assert copied.status_code == 200
        assert copied.json()["data"][0]["businessId"] == "2-ZDH-T19-001"
        copied_config = copied.json()["data"][0]
        assert copied_config["debugSubitemId"]
        assert copied_config["debugDivisionId"]
        with sqlite3.connect(client.app.state.workspace_repository.database_path) as connection:
            connection.execute(
                "UPDATE workspace_configs SET debug_subitem_id = NULL, debug_division_id = NULL WHERE id = ?",
                (copied_config["id"],),
            )
            connection.execute(
                "DELETE FROM workspace_config_classifications WHERE config_id = ?", (copied_config["id"],)
            )
        repaired_copy = client.post(
            "/api/workspace/configs/copy",
            headers=admin,
            json={"sourceConfigId": config_id, "target": target},
        )
        assert repaired_copy.status_code == 200, repaired_copy.text
        assert repaired_copy.json()["data"][0]["id"] == copied_config["id"]
        assert repaired_copy.json()["data"][0]["debugSubitemId"] == copied_config["debugSubitemId"]
        assert repaired_copy.json()["data"][0]["debugDivisionId"] == copied_config["debugDivisionId"]
        unclassified_source = client.post(
            "/api/workspace/configs",
            headers=admin,
            json={
                "scope": scope,
                "configCode": "legacy-without-debug-subitem",
                "steps": [{"description": "step", "results": [{"description": "result"}]}],
            },
        )
        assert unclassified_source.status_code == 200, unclassified_source.text
        rejected_unclassified_copy = client.post(
            "/api/workspace/configs/copy",
            headers=admin,
            json={"sourceConfigId": unclassified_source.json()["data"]["id"], "target": target},
        )
        assert rejected_unclassified_copy.status_code == 409
        assert rejected_unclassified_copy.json()["code"] == "WORKSPACE_COPY_SOURCE_CLASSIFICATION_REQUIRED"
        target_subitems = client.get(
            "/api/workspace/debug-items",
            headers=admin,
            params={**target, "category": "debug_subitems"},
        ).json()["data"]
        assert [item["name"] for item in target_subitems] == ["FAS设备信息监视"]
        target_divisions = client.get(
            "/api/workspace/debug-items",
            headers=admin,
            params={**target, "category": "debug_divisions", "parentId": copied_config["debugSubitemId"]},
        ).json()["data"]
        assert [item["name"] for item in target_divisions] == ["吸气式主机"]
        filtered_copy = client.get(
            "/api/workspace/configs",
            headers=admin,
            params={
                **target,
                "debugSubitemId": copied_config["debugSubitemId"],
                "debugDivisionId": copied_config["debugDivisionId"],
            },
        ).json()["data"]
        assert [item["id"] for item in filtered_copy] == [copied_config["id"]]

        created_user = client.post(
            "/api/workspace/users",
            headers=admin,
            json={
                "username": "line-admin",
                "password": "secret123",
                "displayName": "线路管理员",
                "role": "line_admin",
                "lineId": line["id"],
            },
        )
        assert created_user.status_code == 200
        short_password_user = client.post(
            "/api/workspace/users",
            headers=admin,
            json={
                "username": "short-pass",
                "password": "x",
                "displayName": "短密码",
                "role": "super_admin",
            },
        )
        assert short_password_user.status_code == 200, short_password_user.text
        changed_user = client.put(
            f"/api/workspace/users/{short_password_user.json()['data']['id']}",
            headers=admin,
            json={
                "username": "short-pass",
                "password": "",
                "displayName": "更新名称",
                "role": "super_admin",
            },
        )
        assert changed_user.status_code == 200, changed_user.text
        assert changed_user.json()["data"]["displayName"] == "更新名称"
        line_admin = _login(client, "line-admin")
        # Project codes belong to a line and cannot be duplicated by profession.
        other_profession = client.post(
            "/api/workspace/professions",
            headers=admin,
            json={"code": "TX", "name": "通信", "sortOrder": 2},
        ).json()["data"]
        parallel_project = client.post(
            "/api/workspace/projects",
            headers=admin,
            json={
                "lineId": line["id"],
                "professionId": other_profession["id"],
                "code": "T19",
                "name": "通信专业测试",
                "sortOrder": 1,
            },
        )
        assert parallel_project.status_code == 409, parallel_project.text
        parallel_project = client.post(
            "/api/workspace/projects",
            headers=admin,
            json={
                "lineId": line["id"],
                "professionId": other_profession["id"],
                "code": "T20",
                "name": "通信专业测试",
                "sortOrder": 1,
            },
        )
        assert parallel_project.status_code == 200, parallel_project.text
        assert parallel_project.json()["data"]["name"] == "通信专业测试"
        line_projects = client.get(
            "/api/workspace/projects",
            headers=admin,
            params={"lineId": line["id"], "professionId": profession["id"]},
        ).json()["data"]
        assert any(item["id"] == parallel_project.json()["data"]["id"] for item in line_projects)
        managed_project = client.post(
            "/api/workspace/projects",
            headers=line_admin,
            json={
                "lineId": line["id"],
                "professionId": other_profession["id"],
                "code": "T21",
                "name": "线路管理员新增项目",
                "sortOrder": 1,
            },
        )
        assert managed_project.status_code == 200, managed_project.text
        managed_project_id = managed_project.json()["data"]["id"]
        edited_managed_project = client.put(
            f"/api/workspace/projects/{managed_project_id}",
            headers=line_admin,
            json={
                "lineId": line["id"],
                "professionId": other_profession["id"],
                "code": "T22",
                "name": "线路管理员修改项目",
                "sortOrder": 1,
            },
        )
        assert edited_managed_project.status_code == 200, edited_managed_project.text
        assert edited_managed_project.json()["data"]["code"] == "T22"
        moved_out_of_scope = client.put(
            f"/api/workspace/projects/{managed_project_id}",
            headers=line_admin,
            json={
                "lineId": line_two["id"],
                "professionId": other_profession["id"],
                "code": "T22",
                "name": "越权移动",
                "sortOrder": 1,
            },
        )
        assert moved_out_of_scope.status_code == 403
        forbidden = client.post(
            "/api/workspace/configs",
            headers=line_admin,
            json={**payload, "configCode": "FAS-其他-001", "scope": target},
        )
        assert forbidden.status_code == 403
        professional_created = client.post(
            "/api/workspace/users",
            headers=admin,
            json={
                "username": "profession-editor",
                "password": "x",
                "displayName": "专业配置员",
                "role": "professional_configurator",
                "lineId": line["id"],
                "professionId": profession["id"],
            },
        )
        assert professional_created.status_code == 200, professional_created.text
        professional = _login(client, "profession-editor", "x")
        other_scope = {
            "lineId": line["id"],
            "professionId": other_profession["id"],
            "projectId": parallel_project.json()["data"]["id"],
        }
        other_subitem = client.post(
            "/api/workspace/debug-items",
            headers=admin,
            json={"scope": other_scope, "category": "debug_subitems", "name": "FAS设备信息监视"},
        )
        assert other_subitem.status_code == 200, other_subitem.text
        other_division = client.post(
            "/api/workspace/debug-items",
            headers=admin,
            json={
                "scope": other_scope,
                "category": "debug_divisions",
                "parentId": other_subitem.json()["data"]["id"],
                "name": "吸气式主机",
            },
        )
        assert other_division.status_code == 200, other_division.text
        other_config = client.post(
            "/api/workspace/configs",
            headers=admin,
            json={
                **payload,
                "scope": other_scope,
                "configCode": "跨专业复制测试",
                "debugSubitemId": other_subitem.json()["data"]["id"],
                "debugDivisionId": other_division.json()["data"]["id"],
            },
        )
        assert other_config.status_code == 200, other_config.text
        cross_profession_copy = client.post(
            "/api/workspace/configs/batch-copy",
            headers=professional,
            json={"sourceConfigIds": [other_config.json()["data"]["id"]], "target": scope},
        )
        assert cross_profession_copy.status_code == 200, cross_profession_copy.text
        cross_profession_result = cross_profession_copy.json()["data"][0]
        assert cross_profession_result["professionId"] == profession["id"]
        assert cross_profession_result["debugSubitemId"] == source_subitem.json()["data"]["id"]
        assert cross_profession_result["debugDivisionId"] == source_division.json()["data"]["id"]
        created_subitem = client.post(
            "/api/workspace/debug-items",
            headers=professional,
            json={"scope": scope, "category": "debug_subitems", "name": "自动生成编码的调试子项"},
        )
        assert created_subitem.status_code == 200, created_subitem.text
        assert created_subitem.json()["data"]["code"].startswith("DSI-")
        created_division = client.post(
            "/api/workspace/debug-items",
            headers=professional,
            json={
                "scope": scope,
                "category": "debug_divisions",
                "parentId": created_subitem.json()["data"]["id"],
                "name": "自动生成编码的调试分项",
            },
        )
        assert created_division.status_code == 200, created_division.text
        assert created_division.json()["data"]["code"].startswith("DDI-")
        assert created_division.json()["data"]["parentId"] == created_subitem.json()["data"]["id"]
        imported_with_stale_picker = client.post(
            "/api/workspace/configs/import",
            headers=professional,
            json={
                "scope": {
                    **scope,
                    "debugSubitemId": created_subitem.json()["data"]["id"],
                    "debugDivisionId": created_division.json()["data"]["id"],
                },
                "rows": [
                    {
                        "联调配置编码": "T19-导入分类优先",
                        "调试子项": "导入子项",
                        "调试分项": "导入分项",
                        "步骤序号": 1,
                        "操作步骤": "执行测试",
                        "输出序号": 1,
                        "预期结果": "测试通过",
                    }
                ],
            },
        )
        assert imported_with_stale_picker.status_code == 200, imported_with_stale_picker.text
        imported_classification = imported_with_stale_picker.json()["data"][0]
        assert imported_classification["debugSubitemId"] != created_subitem.json()["data"]["id"]
        assert imported_classification["debugDivisionId"] != created_division.json()["data"]["id"]
        direct_subitem_import = client.post(
            "/api/workspace/configs/import",
            headers=professional,
            json={
                "scope": {
                    **scope,
                    "debugSubitemId": created_subitem.json()["data"]["id"],
                    "debugDivisionId": created_division.json()["data"]["id"],
                },
                "rows": [
                    {
                        "联调配置编码": "T19-气灭测试",
                        "调试子项": "自动生成编码的调试子项",
                        "调试分项": "",
                        "步骤序号": 1,
                        "操作步骤": "执行气灭手自动状态测试",
                        "输出序号": 1,
                        "预期结果": "FAS主机收到正确手动状态报警信息",
                    }
                ],
            },
        )
        assert direct_subitem_import.status_code == 200, direct_subitem_import.text
        direct_subitem_config = direct_subitem_import.json()["data"][0]
        assert direct_subitem_config["debugSubitemId"]
        assert direct_subitem_config["debugDivisionId"] is None
        direct_subitem_list = client.get(
            "/api/workspace/configs",
            headers=professional,
            params={**scope, "debugSubitemId": direct_subitem_config["debugSubitemId"]},
        )
        assert any(item["id"] == direct_subitem_config["id"] for item in direct_subitem_list.json()["data"])
        classified_config = client.put(
            f"/api/workspace/configs/{config_id}",
            headers=professional,
            json={
                **payload,
                "configCode": "FAS-垂梯-运行状态反馈",
                "debugSubitemId": created_subitem.json()["data"]["id"],
                "debugDivisionId": created_division.json()["data"]["id"],
            },
        )
        assert classified_config.status_code == 200, classified_config.text
        protected_delete = client.delete(
            f"/api/workspace/debug-items/{created_division.json()['data']['id']}",
            headers=professional,
            params={**scope, "category": "debug_divisions"},
        )
        assert protected_delete.status_code == 409
        assert protected_delete.json()["code"] == "WORKSPACE_DEBUG_IN_USE"
        protected_parent_delete = client.delete(
            f"/api/workspace/debug-items/{created_subitem.json()['data']['id']}",
            headers=professional,
            params={**scope, "category": "debug_subitems"},
        )
        assert protected_parent_delete.status_code == 409
        batch_subitems = client.post(
            "/api/workspace/debug-items/batch",
            headers=professional,
            json={"scope": scope, "category": "debug_subitems", "names": ["批量子项甲", "批量子项乙"]},
        )
        assert batch_subitems.status_code == 200, batch_subitems.text
        assert [item["name"] for item in batch_subitems.json()["data"]] == ["批量子项甲", "批量子项乙"]
        assert [item["sortOrder"] for item in batch_subitems.json()["data"]] == [4, 5]
        batch_parent_id = batch_subitems.json()["data"][0]["id"]
        batch_divisions = client.post(
            "/api/workspace/debug-items/batch",
            headers=professional,
            json={
                "scope": scope,
                "category": "debug_divisions",
                "parentId": batch_parent_id,
                "names": ["吸气式主机", "感温电缆", "感温光纤"],
            },
        )
        assert batch_divisions.status_code == 200, batch_divisions.text
        assert len(batch_divisions.json()["data"]) == 3
        assert [item["sortOrder"] for item in batch_divisions.json()["data"]] == [1, 2, 3]
        assert all(item["parentId"] == batch_parent_id for item in batch_divisions.json()["data"])
        duplicate_batch = client.post(
            "/api/workspace/debug-items/batch",
            headers=professional,
            json={
                "scope": scope,
                "category": "debug_divisions",
                "parentId": batch_parent_id,
                "names": ["全新分项", "吸气式主机"],
            },
        )
        assert duplicate_batch.status_code == 409
        assert duplicate_batch.json()["code"] == "WORKSPACE_DEBUG_EXISTS"
        deleted_batch_parent = client.delete(
            f"/api/workspace/debug-items/{batch_parent_id}",
            headers=professional,
            params={**scope, "category": "debug_subitems"},
        )
        assert deleted_batch_parent.status_code == 200, deleted_batch_parent.text
        listed_divisions = client.get(
            "/api/workspace/debug-items",
            headers=professional,
            params={
                **scope,
                "category": "debug_divisions",
                "parentId": created_subitem.json()["data"]["id"],
            },
        )
        assert listed_divisions.status_code == 200
        assert [item["id"] for item in listed_divisions.json()["data"]] == [created_division.json()["data"]["id"]]
        duplicate_division = client.post(
            "/api/workspace/debug-items",
            headers=professional,
            json={
                "scope": scope,
                "category": "debug_divisions",
                "parentId": created_subitem.json()["data"]["id"],
                "name": "自动生成编码的调试分项",
            },
        )
        assert duplicate_division.status_code == 409
        assert duplicate_division.json()["code"] == "WORKSPACE_DEBUG_EXISTS"
        other_subitem = client.post(
            "/api/workspace/debug-items",
            headers=professional,
            json={"scope": scope, "category": "debug_subitems", "name": "另一个调试子项"},
        )
        assert other_subitem.status_code == 200, other_subitem.text
        same_name_other_parent = client.post(
            "/api/workspace/debug-items",
            headers=professional,
            json={
                "scope": scope,
                "category": "debug_divisions",
                "parentId": other_subitem.json()["data"]["id"],
                "name": "自动生成编码的调试分项",
            },
        )
        assert same_name_other_parent.status_code == 200, same_name_other_parent.text
        invalid_parent = client.post(
            "/api/workspace/debug-items",
            headers=professional,
            json={
                "scope": scope,
                "category": "debug_divisions",
                "parentId": "not-a-subitem-in-this-scope",
                "name": "非法归属分项",
            },
        )
        assert invalid_parent.status_code == 422
        assert invalid_parent.json()["code"] == "WORKSPACE_DEBUG_PARENT_INVALID"
        editable_config = client.put(
            f"/api/workspace/configs/{config_id}",
            headers=professional,
            json={
                **payload,
                "configCode": "FAS-编辑后的规则",
                "steps": [
                    {
                        "description": "专业员编辑的步骤",
                        "results": [{"description": "专业员编辑的输出结果"}],
                    }
                ],
            },
        )
        assert editable_config.status_code == 200, editable_config.text
        assert editable_config.json()["data"]["steps"][0]["description"] == "专业员编辑的步骤"
        assert editable_config.json()["data"]["steps"][0]["results"][0]["description"] == "专业员编辑的输出结果"

        moved_project = client.put(
            f"/api/workspace/projects/{project['id']}",
            headers=admin,
            json={
                "lineId": line_two["id"],
                "professionId": profession["id"],
                "code": "T19-MOVED",
                "name": "超级管理员调整范围后的项目",
                "engineCode": project["engineCode"],
                "sortOrder": 1,
            },
        )
        assert moved_project.status_code == 200, moved_project.text
        assert moved_project.json()["data"]["lineId"] == line_two["id"]
        assert moved_project.json()["data"]["code"] == "T19-MOVED"
        moved_scope = {**scope, "lineId": line_two["id"]}
        moved_configs = client.get("/api/workspace/configs", headers=admin, params=moved_scope).json()["data"]
        assert any(item["id"] == config_id for item in moved_configs)
        assert next(item for item in moved_configs if item["id"] == config_id)["businessId"] == "9-ZDH-T19-001"


def test_line_admin_can_view_disabled_projects_and_edit_project_scope(tmp_path: Path) -> None:
    with TestClient(create_app(Settings(mode="formal", database_path=tmp_path / "workspace.sqlite3"))) as client:
        registered = client.post(
            "/api/auth/register",
            json={
                "username": "admin",
                "password": "secret123",
                "confirmPassword": "secret123",
                "displayName": "管理员",
                "agree": True,
            },
        )
        admin = {"Authorization": f"Bearer {registered.json()['data']['token']}"}
        context = client.get("/api/workspace/context", headers=admin).json()["data"]
        line = context["lines"][0]
        profession = context["professions"][0]
        project = context["projects"][0]
        line_admin_user = client.post(
            "/api/workspace/users",
            headers=admin,
            json={
                "username": "line-admin",
                "password": "secret123",
                "displayName": "线路管理员",
                "role": "line_admin",
                "lineId": line["id"],
            },
        )
        assert line_admin_user.status_code == 200, line_admin_user.text
        line_admin = _login(client, "line-admin")
        other_profession = client.post(
            "/api/workspace/professions",
            headers=admin,
            json={"code": "TX", "name": "通信", "sortOrder": 2},
        ).json()["data"]
        disabled_project = client.put(
            f"/api/workspace/projects/{project['id']}",
            headers=admin,
            json={
                "lineId": line["id"],
                "professionId": profession["id"],
                "code": project["code"],
                "name": project["name"],
                "engineCode": project["engineCode"],
                "isEnabled": False,
            },
        )
        assert disabled_project.status_code == 200
        assert client.get("/api/workspace/context", headers=line_admin).json()["data"]["projects"] == []
        management_context = client.get("/api/workspace/context", headers=line_admin, params={"includeDisabled": True})
        assert management_context.status_code == 200, management_context.text
        assert management_context.json()["data"]["projects"][0]["isEnabled"] is False

        updated = client.put(
            f"/api/workspace/projects/{project['id']}",
            headers=line_admin,
            json={
                "lineId": line["id"],
                "professionId": other_profession["id"],
                "code": "T20",
                "name": "更新后的联调项目",
                "engineCode": project["engineCode"],
                "isEnabled": True,
            },
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["data"]["code"] == "T20"
        assert updated.json()["data"]["professionId"] == other_profession["id"]
        assert updated.json()["data"]["engineCode"] == "T20"
        assert updated.json()["data"]["isEnabled"] is True


def test_workspace_config_import_groups_results_into_steps(tmp_path: Path) -> None:
    with TestClient(create_app(Settings(mode="formal", database_path=tmp_path / "import.sqlite3"))) as client:
        registered = client.post(
            "/api/auth/register",
            json={
                "username": "admin",
                "password": "x",
                "confirmPassword": "x",
                "displayName": "管理员",
                "agree": True,
            },
        )
        admin = {"Authorization": f"Bearer {registered.json()['data']['token']}"}
        context = client.get("/api/workspace/context", headers=admin).json()["data"]
        scope = {
            "lineId": context["lines"][0]["id"],
            "professionId": context["professions"][0]["id"],
            "projectId": context["projects"][0]["id"],
        }
        rows = [
            {
                "联调配置编码": "FAS-400V-切非反馈",
                "设备类型": "400V",
                "步骤序号": 1,
                "操作步骤": "触发切非",
                "输出序号": 1,
                "预期结果": "现场动作",
            },
            {
                "联调配置编码": "FAS-400V-切非反馈",
                "设备类型": "400V",
                "步骤序号": 1,
                "操作步骤": "",
                "输出序号": 2,
                "预期结果": "主机收到反馈",
            },
            {
                "联调配置编码": "FAS-400V-切非反馈",
                "设备类型": "400V",
                "步骤序号": 2,
                "操作步骤": "检查恢复",
                "输出序号": 1,
                "预期结果": "系统恢复",
            },
        ]
        response = client.post("/api/workspace/configs/import", headers=admin, json={"scope": scope, "rows": rows})
        assert response.status_code == 200, response.text
        imported = response.json()["data"][0]
        assert len(imported["steps"]) == 2
        assert len(imported["steps"][0]["results"]) == 2
        assert imported["steps"][1]["description"] == "检查恢复"

        for name in ("变电", "自动化", "通信"):
            created_discipline = client.post(
                "/api/workspace/catalog",
                headers=admin,
                json={
                    "scope": scope,
                    "category": "disciplines",
                    "code": name,
                    "name": name,
                    "sortOrder": 1,
                },
            )
            assert created_discipline.status_code == 200, created_discipline.text
        discipline_rows = [
            {
                "联调配置编码": "FAS-责任专业样例",
                "步骤序号": 1,
                "操作步骤": "触发测试",
                "输出序号": 1,
                "预期结果": "现场动作",
                "责任专业": "变电",
            },
            {
                "联调配置编码": "FAS-责任专业样例",
                "步骤序号": 1,
                "操作步骤": "",
                "输出序号": 2,
                "预期结果": "主机反馈",
                "责任专业": "自动化、通信",
            },
        ]
        assigned = client.post(
            "/api/workspace/configs/import",
            headers=admin,
            json={"scope": scope, "rows": discipline_rows},
        )
        assert assigned.status_code == 200, assigned.text
        assert assigned.json()["data"][0]["steps"][0]["results"][0]["responsibleDisciplines"] == ["变电"]
        assert assigned.json()["data"][0]["steps"][0]["results"][1]["responsibleDisciplines"] == [
            "自动化",
            "通信",
        ]

        compact_rows = [
            {
                "联调配置编码": "FAS-紧凑样例",
                "设备类型": "声光报警器",
                "步骤序号": 1,
                "操作步骤": "启动设备",
                "输出序号": 1,
                "预期结果": "设备启动",
                "责任专业": "自动化",
            },
            {
                "联调配置编码": "",
                "设备类型": "",
                "步骤序号": "",
                "操作步骤": "",
                "输出序号": 2,
                "预期结果": "主机收到反馈",
                "责任专业": "自动化",
            },
        ]
        compact = client.post(
            "/api/workspace/configs/import",
            headers=admin,
            json={"scope": scope, "rows": compact_rows},
        )
        assert compact.status_code == 200, compact.text
        assert compact.json()["data"][0]["configCode"] == "FAS-紧凑样例"
        assert len(compact.json()["data"][0]["steps"][0]["results"]) == 2


def test_workspace_download_templates_have_samples_and_descriptive_names(tmp_path: Path) -> None:
    with TestClient(create_app(Settings(mode="formal", database_path=tmp_path / "templates.sqlite3"))) as client:
        registered = client.post(
            "/api/auth/register",
            json={
                "username": "admin",
                "password": "x",
                "confirmPassword": "x",
                "displayName": "管理员",
                "agree": True,
            },
        )
        admin = {"Authorization": f"Bearer {registered.json()['data']['token']}"}
        data_template = client.get("/api/workspace/template", headers=admin)
        assert data_template.status_code == 200
        assert "excelforge-data-import-template.xls" in data_template.headers["content-disposition"]
        data_book = xlrd.open_workbook(file_contents=data_template.content)
        assert data_book.sheet_names() == ["数据导入模板", "填写说明"]
        assert data_book.sheet_by_name("数据导入模板").cell_value(1, 0) == "DT-001"

        context = client.get("/api/workspace/context", headers=admin).json()["data"]
        scope = {
            "lineId": context["lines"][0]["id"],
            "professionId": context["professions"][0]["id"],
            "projectId": context["projects"][0]["id"],
        }
        config_template = client.get("/api/workspace/config-template", headers=admin, params=scope)
        assert config_template.status_code == 200
        assert "excelforge-config-spec-template.xls" in config_template.headers["content-disposition"]
        config_book = xlrd.open_workbook(file_contents=config_template.content)
        sheet = config_book.sheet_by_name("配置规范模板")
        assert sheet.nrows == 17
        assert sheet.cell_value(0, 2) == "调试子项"
        assert sheet.cell_value(0, 3) == "调试分项"
        assert sheet.cell_value(0, 9) == "责任专业"
        assert sheet.cell_value(1, 1) == "FAS-400V-切非"
        assert sheet.cell_value(2, 1) == ""
        assert sheet.cell_value(1, 5) == 1
        assert sheet.cell_value(5, 5) == 2
        assert config_book.sheet_by_name("填写说明").nrows >= 2


def test_catalog_stations_are_isolated_by_line(tmp_path: Path) -> None:
    with TestClient(create_app(Settings(mode="formal", database_path=tmp_path / "stations.sqlite3"))) as client:
        registered = client.post(
            "/api/auth/register",
            json={
                "username": "admin",
                "password": "secret123",
                "confirmPassword": "secret123",
                "displayName": "管理员",
                "agree": True,
            },
        )
        admin = {"Authorization": f"Bearer {registered.json()['data']['token']}"}
        context = client.get("/api/workspace/context", headers=admin).json()["data"]
        line_nine = next(line for line in context["lines"] if line["code"] == "9")
        line_two = client.post("/api/workspace/lines", headers=admin, json={"code": "2", "name": "2号线"}).json()[
            "data"
        ]

        def create_station(line_id: int) -> dict[str, object]:
            response = client.post(
                "/api/catalog/stations",
                headers=admin,
                params={"integrationCode": "T19", "lineId": line_id},
                json={"name": "同名站点", "sortOrder": 1, "isEnabled": True},
            )
            assert response.status_code == 200, response.text
            return response.json()["data"]

        station_nine = create_station(line_nine["id"])
        station_two = create_station(line_two["id"])
        assert station_nine["name"] == station_two["name"]
        assert station_nine["id"] != station_two["id"]
        listed_nine = client.get(
            "/api/catalog/stations",
            headers=admin,
            params={"integrationCode": "T19", "lineId": line_nine["id"]},
        ).json()["data"]
        listed_two = client.get(
            "/api/catalog/stations",
            headers=admin,
            params={"integrationCode": "T19", "lineId": line_two["id"]},
        ).json()["data"]
        assert [item["id"] for item in listed_nine] == [station_nine["id"]]
        assert [item["id"] for item in listed_two] == [station_two["id"]]


def test_workspace_catalog_is_scoped_and_independent(tmp_path: Path) -> None:
    with TestClient(
        create_app(Settings(mode="formal", database_path=tmp_path / "workspace-catalog.sqlite3"))
    ) as client:
        registered = client.post(
            "/api/auth/register",
            json={
                "username": "admin",
                "password": "secret123",
                "confirmPassword": "secret123",
                "displayName": "管理员",
                "agree": True,
            },
        )
        admin = {"Authorization": f"Bearer {registered.json()['data']['token']}"}
        context = client.get("/api/workspace/context", headers=admin).json()["data"]
        line = context["lines"][0]
        profession = context["professions"][0]
        project = context["projects"][0]
        scope = {"lineId": line["id"], "professionId": profession["id"], "projectId": project["id"]}
        payload = {
            "scope": scope,
            "category": "equipment_types",
            "code": "VERTICAL_LIFT",
            "name": "垂梯",
            "sortOrder": 1,
        }
        created = client.post("/api/workspace/catalog", headers=admin, json=payload)
        assert created.status_code == 200, created.text
        item = created.json()["data"]
        assert item["name"] == "垂梯"
        assert item["lineId"] == line["id"]
        listed = client.get("/api/workspace/catalog", headers=admin, params={**scope, "category": "equipment_types"})
        assert [row["id"] for row in listed.json()["data"]] == [item["id"]]
        updated = client.put(
            f"/api/workspace/catalog/{item['id']}",
            headers=admin,
            json={**payload, "name": "垂直电梯"},
        )
        assert updated.status_code == 200, updated.text
        disabled = client.post(
            f"/api/workspace/catalog/{item['id']}/status",
            headers=admin,
            params={**scope, "category": "equipment_types", "enabled": False},
        )
        assert disabled.status_code == 200, disabled.text
        assert disabled.json()["data"]["isEnabled"] is False
        assert (
            client.get(
                "/api/workspace/catalog",
                headers=admin,
                params={**scope, "category": "equipment_types"},
            ).json()["data"]
            == []
        )
        assert (
            len(
                client.get(
                    "/api/workspace/catalog",
                    headers=admin,
                    params={**scope, "category": "equipment_types", "includeDisabled": True},
                ).json()["data"]
            )
            == 1
        )

        shared_station = client.post(
            "/api/workspace/catalog",
            headers=admin,
            json={
                "scope": scope,
                "category": "stations",
                "code": "STATION_A",
                "name": "嘉庚体育馆站",
                "sortOrder": 1,
            },
        )
        shared_discipline = client.post(
            "/api/workspace/catalog",
            headers=admin,
            json={
                "scope": scope,
                "category": "disciplines",
                "code": "ZDH",
                "name": "自动化",
                "sortOrder": 1,
            },
        )
        assert shared_station.status_code == shared_discipline.status_code == 200
        second_profession = client.post(
            "/api/workspace/professions",
            headers=admin,
            json={
                "code": "TX",
                "name": "通信",
                "sortOrder": 2,
            },
        ).json()["data"]
        second_project = client.post(
            "/api/workspace/projects",
            headers=admin,
            json={
                "professionId": second_profession["id"],
                "code": "ISCS",
                "name": "ISCS",
                "sortOrder": 1,
            },
        ).json()["data"]
        second_scope = {
            "lineId": line["id"],
            "professionId": second_profession["id"],
            "projectId": second_project["id"],
        }
        for category in ("stations", "disciplines"):
            shared = client.get(
                "/api/workspace/catalog",
                headers=admin,
                params={**second_scope, "category": category},
            )
            assert [row["name"] for row in shared.json()["data"]] == [
                "嘉庚体育馆站" if category == "stations" else "自动化"
            ]
        other_line = client.post(
            "/api/workspace/lines",
            headers=admin,
            json={
                "code": "10",
                "name": "10号线",
                "sortOrder": 10,
            },
        ).json()["data"]
        other_scope = {
            "lineId": other_line["id"],
            "professionId": profession["id"],
            "projectId": project["id"],
        }
        assert (
            client.get(
                "/api/workspace/catalog",
                headers=admin,
                params={**other_scope, "category": "stations"},
            ).status_code
            == 404
        )
