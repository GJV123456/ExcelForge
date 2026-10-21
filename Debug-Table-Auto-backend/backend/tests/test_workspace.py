from __future__ import annotations

from pathlib import Path
from io import BytesIO

from fastapi.testclient import TestClient
import xlrd

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
        assert client.put(
            f"/api/workspace/lines/{line['id']}",
            headers=admin,
            json={"code": line["code"], "name": "线路名称测试", "sortOrder": 1},
        ).status_code == 200
        assert client.put(
            f"/api/workspace/professions/{profession['id']}",
            headers=admin,
            json={"code": profession["code"], "name": "专业名称测试", "sortOrder": 1},
        ).status_code == 200
        assert client.put(
            f"/api/workspace/projects/{project['id']}",
            headers=admin,
            json={
                "professionId": profession["id"],
                "code": project["code"],
                "name": "项目名称测试",
                "engineCode": project["engineCode"],
                "sortOrder": 1,
            },
        ).status_code == 200
        scope = {"lineId": line["id"], "professionId": profession["id"], "projectId": project["id"]}
        payload = {
            "scope": scope,
            "configCode": "FAS-垂梯-状态反馈",
            "deviceType": "垂梯",
            "steps": [{"description": "模拟状态", "ratioChange": "否", "results": [{"description": "显示状态", "responsibleDisciplines": ["自动化"]}]}],
        }
        created = client.post("/api/workspace/configs", headers=admin, json=payload)
        assert created.status_code == 200
        assert created.json()["data"]["businessId"] == "9-ZDH-FAS-001"
        config_id = created.json()["data"]["id"]

        # The configuration editor sends result descriptions and discipline
        # names, while ordering and enabled state belong to steps/configs.
        frontend_shape = {
            **payload,
            "configCode": "FAS-垂梯-归首控制",
            "steps": [{
                "description": "发送归首控制",
                "ratioChange": "否",
                "sortOrder": 1,
                "isEnabled": True,
                "results": [{"description": "垂梯返回归首状态", "responsibleDisciplines": []}],
            }],
        }
        created_from_editor = client.post("/api/workspace/configs", headers=admin, json=frontend_shape)
        assert created_from_editor.status_code == 200, created_from_editor.text
        assert created_from_editor.json()["data"]["steps"][0]["results"][0]["description"] == "垂梯返回归首状态"
        disabled = client.post(f"/api/workspace/configs/{created_from_editor.json()['data']['id']}/status", headers=admin, params={"enabled": False})
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

        line_two = client.post("/api/workspace/lines", headers=admin, json={"code": "2", "name": "2号线"}).json()["data"]
        target = {**scope, "lineId": line_two["id"]}
        copied = client.post("/api/workspace/configs/copy", headers=admin, json={"sourceConfigId": config_id, "target": target})
        assert copied.status_code == 200
        assert copied.json()["data"][0]["businessId"] == "2-ZDH-FAS-001"

        created_user = client.post(
            "/api/workspace/users",
            headers=admin,
            json={"username": "line-admin", "password": "secret123", "displayName": "线路管理员", "role": "line_admin", "lineId": line["id"]},
        )
        assert created_user.status_code == 200
        short_password_user = client.post(
            "/api/workspace/users",
            headers=admin,
            json={"username": "short-pass", "password": "x", "displayName": "短密码", "role": "super_admin"},
        )
        assert short_password_user.status_code == 200, short_password_user.text
        changed_user = client.put(
            f"/api/workspace/users/{short_password_user.json()['data']['id']}",
            headers=admin,
            json={"username": "short-pass", "password": "", "displayName": "更新名称", "role": "super_admin"},
        )
        assert changed_user.status_code == 200, changed_user.text
        assert changed_user.json()["data"]["displayName"] == "更新名称"
        line_admin = _login(client, "line-admin")
        forbidden = client.post("/api/workspace/configs", headers=line_admin, json={**payload, "configCode": "FAS-其他-001", "scope": target})
        assert forbidden.status_code == 403
        professional_created = client.post(
            "/api/workspace/users",
            headers=admin,
            json={"username": "profession-editor", "password": "x", "displayName": "专业配置员", "role": "professional_configurator", "lineId": line["id"], "professionId": profession["id"]},
        )
        assert professional_created.status_code == 200, professional_created.text
        professional = _login(client, "profession-editor", "x")
        editable_config = client.put(
            f"/api/workspace/configs/{config_id}",
            headers=professional,
            json={**payload, "configCode": "FAS-编辑后的规则", "steps": [{"description": "专业员编辑的步骤", "results": [{"description": "专业员编辑的输出结果"}]}]},
        )
        assert editable_config.status_code == 200, editable_config.text
        assert editable_config.json()["data"]["steps"][0]["description"] == "专业员编辑的步骤"
        assert editable_config.json()["data"]["steps"][0]["results"][0]["description"] == "专业员编辑的输出结果"


def test_workspace_config_import_groups_results_into_steps(tmp_path: Path) -> None:
    with TestClient(create_app(Settings(mode="formal", database_path=tmp_path / "import.sqlite3"))) as client:
        registered = client.post(
            "/api/auth/register",
            json={"username": "admin", "password": "x", "confirmPassword": "x", "displayName": "管理员", "agree": True},
        )
        admin = {"Authorization": f"Bearer {registered.json()['data']['token']}"}
        context = client.get("/api/workspace/context", headers=admin).json()["data"]
        scope = {"lineId": context["lines"][0]["id"], "professionId": context["professions"][0]["id"], "projectId": context["projects"][0]["id"]}
        rows = [
            {"联调配置编码": "FAS-400V-切非反馈", "设备类型": "400V", "步骤序号": 1, "操作步骤": "触发切非", "输出序号": 1, "预期结果": "现场动作"},
            {"联调配置编码": "FAS-400V-切非反馈", "设备类型": "400V", "步骤序号": 1, "操作步骤": "", "输出序号": 2, "预期结果": "主机收到反馈"},
            {"联调配置编码": "FAS-400V-切非反馈", "设备类型": "400V", "步骤序号": 2, "操作步骤": "检查恢复", "输出序号": 1, "预期结果": "系统恢复"},
        ]
        response = client.post("/api/workspace/configs/import", headers=admin, json={"scope": scope, "rows": rows})
        assert response.status_code == 200, response.text
        imported = response.json()["data"][0]
        assert len(imported["steps"]) == 2
        assert len(imported["steps"][0]["results"]) == 2
        assert imported["steps"][1]["description"] == "检查恢复"

        for name in ("变电", "自动化", "通信"):
            created_discipline = client.post("/api/workspace/catalog", headers=admin, json={
                "scope": scope, "category": "disciplines", "code": name, "name": name, "sortOrder": 1,
            })
            assert created_discipline.status_code == 200, created_discipline.text
        discipline_rows = [
            {"联调配置编码": "FAS-责任专业样例", "步骤序号": 1, "操作步骤": "触发测试", "输出序号": 1, "预期结果": "现场动作", "责任专业": "变电"},
            {"联调配置编码": "FAS-责任专业样例", "步骤序号": 1, "操作步骤": "", "输出序号": 2, "预期结果": "主机反馈", "责任专业": "自动化、通信"},
        ]
        assigned = client.post("/api/workspace/configs/import", headers=admin, json={"scope": scope, "rows": discipline_rows})
        assert assigned.status_code == 200, assigned.text
        assert assigned.json()["data"][0]["steps"][0]["results"][0]["responsibleDisciplines"] == ["变电"]
        assert assigned.json()["data"][0]["steps"][0]["results"][1]["responsibleDisciplines"] == ["自动化", "通信"]

        compact_rows = [
            {"联调配置编码": "FAS-紧凑样例", "设备类型": "声光报警器", "步骤序号": 1, "操作步骤": "启动设备", "输出序号": 1, "预期结果": "设备启动", "责任专业": "自动化"},
            {"联调配置编码": "", "设备类型": "", "步骤序号": 1, "操作步骤": "", "输出序号": 2, "预期结果": "主机收到反馈", "责任专业": "自动化"},
        ]
        compact = client.post("/api/workspace/configs/import", headers=admin, json={"scope": scope, "rows": compact_rows})
        assert compact.status_code == 200, compact.text
        assert compact.json()["data"][0]["configCode"] == "FAS-紧凑样例"
        assert len(compact.json()["data"][0]["steps"][0]["results"]) == 2


def test_workspace_download_templates_have_samples_and_descriptive_names(tmp_path: Path) -> None:
    with TestClient(create_app(Settings(mode="formal", database_path=tmp_path / "templates.sqlite3"))) as client:
        registered = client.post(
            "/api/auth/register",
            json={"username": "admin", "password": "x", "confirmPassword": "x", "displayName": "管理员", "agree": True},
        )
        admin = {"Authorization": f"Bearer {registered.json()['data']['token']}"}
        data_template = client.get("/api/workspace/template", headers=admin)
        assert data_template.status_code == 200
        assert "excelforge-data-import-template.xls" in data_template.headers["content-disposition"]
        data_book = xlrd.open_workbook(file_contents=data_template.content)
        assert data_book.sheet_names() == ["数据导入模板", "填写说明"]
        assert data_book.sheet_by_name("数据导入模板").cell_value(1, 0) == "DT-001"

        context = client.get("/api/workspace/context", headers=admin).json()["data"]
        scope = {"lineId": context["lines"][0]["id"], "professionId": context["professions"][0]["id"], "projectId": context["projects"][0]["id"]}
        config_template = client.get("/api/workspace/config-template", headers=admin, params=scope)
        assert config_template.status_code == 200
        assert "excelforge-config-spec-template.xls" in config_template.headers["content-disposition"]
        config_book = xlrd.open_workbook(file_contents=config_template.content)
        sheet = config_book.sheet_by_name("配置规范模板")
        assert sheet.nrows == 17
        assert sheet.cell_value(0, 8) == "责任专业"
        assert sheet.cell_value(1, 1) == "FAS-400V-切非"
        assert sheet.cell_value(2, 1) == ""
        assert sheet.cell_value(1, 4) == 1
        assert sheet.cell_value(5, 4) == 2
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
        line_two = client.post(
            "/api/workspace/lines", headers=admin, json={"code": "2", "name": "2号线"}
        ).json()["data"]

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
    with TestClient(create_app(Settings(mode="formal", database_path=tmp_path / "workspace-catalog.sqlite3"))) as client:
        registered = client.post(
            "/api/auth/register",
            json={"username": "admin", "password": "secret123", "confirmPassword": "secret123", "displayName": "管理员", "agree": True},
        )
        admin = {"Authorization": f"Bearer {registered.json()['data']['token']}"}
        context = client.get("/api/workspace/context", headers=admin).json()["data"]
        line = context["lines"][0]
        profession = context["professions"][0]
        project = context["projects"][0]
        scope = {"lineId": line["id"], "professionId": profession["id"], "projectId": project["id"]}
        payload = {"scope": scope, "category": "equipment_types", "code": "VERTICAL_LIFT", "name": "垂梯", "sortOrder": 1}
        created = client.post("/api/workspace/catalog", headers=admin, json=payload)
        assert created.status_code == 200, created.text
        item = created.json()["data"]
        assert item["name"] == "垂梯"
        assert item["lineId"] == line["id"]
        listed = client.get("/api/workspace/catalog", headers=admin, params={**scope, "category": "equipment_types"})
        assert [row["id"] for row in listed.json()["data"]] == [item["id"]]
        updated = client.put(f"/api/workspace/catalog/{item['id']}", headers=admin, json={**payload, "name": "垂直电梯"})
        assert updated.status_code == 200, updated.text
        disabled = client.post(f"/api/workspace/catalog/{item['id']}/status", headers=admin, params={**scope, "category": "equipment_types", "enabled": False})
        assert disabled.status_code == 200, disabled.text
        assert disabled.json()["data"]["isEnabled"] is False
        assert client.get("/api/workspace/catalog", headers=admin, params={**scope, "category": "equipment_types"}).json()["data"] == []
        assert len(client.get("/api/workspace/catalog", headers=admin, params={**scope, "category": "equipment_types", "includeDisabled": True}).json()["data"]) == 1

        shared_station = client.post("/api/workspace/catalog", headers=admin, json={
            "scope": scope, "category": "stations", "code": "STATION_A", "name": "嘉庚体育馆站", "sortOrder": 1,
        })
        shared_discipline = client.post("/api/workspace/catalog", headers=admin, json={
            "scope": scope, "category": "disciplines", "code": "ZDH", "name": "自动化", "sortOrder": 1,
        })
        assert shared_station.status_code == shared_discipline.status_code == 200
        second_profession = client.post("/api/workspace/professions", headers=admin, json={
            "code": "TX", "name": "通信", "sortOrder": 2,
        }).json()["data"]
        second_project = client.post("/api/workspace/projects", headers=admin, json={
            "professionId": second_profession["id"], "code": "ISCS", "name": "ISCS", "sortOrder": 1,
        }).json()["data"]
        second_scope = {"lineId": line["id"], "professionId": second_profession["id"], "projectId": second_project["id"]}
        for category in ("stations", "disciplines"):
            shared = client.get("/api/workspace/catalog", headers=admin, params={**second_scope, "category": category})
            assert [row["name"] for row in shared.json()["data"]] == ["嘉庚体育馆站" if category == "stations" else "自动化"]
        other_line = client.post("/api/workspace/lines", headers=admin, json={
            "code": "10", "name": "10号线", "sortOrder": 10,
        }).json()["data"]
        other_scope = {"lineId": other_line["id"], "professionId": profession["id"], "projectId": project["id"]}
        assert client.get("/api/workspace/catalog", headers=admin, params={**other_scope, "category": "stations"}).json()["data"] == []

