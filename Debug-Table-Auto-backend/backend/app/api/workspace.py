"""Hierarchical workspace, configuration and account administration APIs."""

from __future__ import annotations

from io import BytesIO
from typing import Annotated

import xlwt
from fastapi import APIRouter, Query, Request, Response

from app.db.auth import AuthRepository, AuthUser
from app.db.workspace import (
    ROLE_LINE_ADMIN,
    ROLE_PROFESSIONAL_CONFIGURATOR,
    ROLE_SUPER_ADMIN,
    WorkspaceRepository,
)
from app.exceptions import BusinessError
from app.schemas.workspace import (
    BatchConfigCopyRequest,
    ConfigCopyRequest,
    ConfigImportRequest,
    ConfigWriteRequest,
    DebugItemsBatchWriteRequest,
    DebugItemWriteRequest,
    LineWriteRequest,
    ProfessionWriteRequest,
    ProjectWriteRequest,
    ScopeSelection,
    UserWriteRequest,
    WorkspaceCatalogWriteRequest,
)

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


def _xls_workbook(sheets: dict[str, list[list[object]]]) -> bytes:
    """Create the user-facing .xls templates with a sample and instructions."""
    workbook = xlwt.Workbook(encoding="utf-8")
    header_style = xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour gray25; align: horiz center")
    text_style = xlwt.easyxf("align: vert top, wrap on")
    for sheet_name, rows in sheets.items():
        sheet = workbook.add_sheet(sheet_name[:31])
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                sheet.write(
                    row_index,
                    column_index,
                    value,
                    header_style if row_index == 0 else text_style,
                )
                sheet.col(column_index).width = max(sheet.col(column_index).width, 3200)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _repository(request: Request) -> WorkspaceRepository:
    return request.app.state.workspace_repository


def _current_user(request: Request) -> AuthUser:
    authorization = request.headers.get("Authorization", "")
    if not authorization.lower().startswith("bearer "):
        raise BusinessError("登录状态已失效，请重新登录", "AUTH_UNAUTHORIZED", status_code=401)
    user = AuthRepository(request.app.state.auth_repository.database.database_path).get_user_by_token(
        authorization[7:].strip()
    )
    if user is None:
        raise BusinessError("登录状态已失效，请重新登录", "AUTH_UNAUTHORIZED", status_code=401)
    return user


def _is_super(user: AuthUser) -> bool:
    return user.get("role") == ROLE_SUPER_ADMIN


def _can_edit_scope(user: AuthUser, scope: ScopeSelection) -> bool:
    role = user.get("role")
    if role == ROLE_SUPER_ADMIN:
        return True
    if role == ROLE_LINE_ADMIN:
        return user.get("lineId") == scope.line_id
    if role == ROLE_PROFESSIONAL_CONFIGURATOR:
        return user.get("lineId") == scope.line_id and user.get("professionId") == scope.profession_id
    return False


def _require_edit_scope(user: AuthUser, scope: ScopeSelection) -> None:
    if not _can_edit_scope(user, scope):
        raise BusinessError("当前账号没有编辑该线路和专业的权限", "WORKSPACE_FORBIDDEN", status_code=403)


def _scope_from_config(config: dict[str, object]) -> ScopeSelection:
    return ScopeSelection(
        lineId=int(config["lineId"]),
        professionId=int(config["professionId"]),
        projectId=int(config["projectId"]),
    )


@router.get("/context")
def context(
    request: Request,
    include_disabled: Annotated[bool, Query(alias="includeDisabled")] = False,
) -> dict[str, object]:
    user = _current_user(request)
    repository = _repository(request)
    return {
        "data": {
            "lines": repository.list_lines(include_disabled=include_disabled),
            "professions": repository.list_professions(include_disabled=include_disabled),
            "projects": repository.list_projects(include_disabled=include_disabled),
            "currentUser": user,
        }
    }


@router.get("/lines")
def list_lines(request: Request) -> dict[str, object]:
    _current_user(request)
    data = _repository(request).list_lines()
    return {"data": data, "meta": {"count": len(data)}}


@router.post("/lines")
def create_line(payload: LineWriteRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    if not _is_super(user):
        raise BusinessError("只有超级管理员可以新增线路", "WORKSPACE_ADMIN_REQUIRED", status_code=403)
    return {"data": _repository(request).create_line(payload)}


@router.put("/lines/{line_id}")
def update_line(line_id: int, payload: LineWriteRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    if not _is_super(user):
        raise BusinessError("只有超级管理员可以编辑线路", "WORKSPACE_ADMIN_REQUIRED", status_code=403)
    return {"data": _repository(request).update_line(line_id, payload)}


@router.get("/professions")
def list_professions(request: Request) -> dict[str, object]:
    _current_user(request)
    data = _repository(request).list_professions()
    return {"data": data, "meta": {"count": len(data)}}


@router.post("/professions")
def create_profession(payload: ProfessionWriteRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    if not _is_super(user):
        raise BusinessError("只有超级管理员可以新增专业", "WORKSPACE_ADMIN_REQUIRED", status_code=403)
    return {"data": _repository(request).create_profession(payload)}


@router.put("/professions/{profession_id}")
def update_profession(profession_id: int, payload: ProfessionWriteRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    if not _is_super(user):
        raise BusinessError("只有超级管理员可以编辑专业", "WORKSPACE_ADMIN_REQUIRED", status_code=403)
    return {"data": _repository(request).update_profession(profession_id, payload)}


@router.get("/projects")
def list_projects(
    request: Request,
    profession_id: Annotated[int | None, Query(alias="professionId", gt=0)] = None,
    line_id: Annotated[int | None, Query(alias="lineId", gt=0)] = None,
) -> dict[str, object]:
    _current_user(request)
    data = _repository(request).list_projects(profession_id, line_id=line_id)
    return {"data": data, "meta": {"count": len(data)}}


@router.post("/projects")
def create_project(payload: ProjectWriteRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    line_id = payload.line_id or user.get("lineId") or 1
    if line_id is None:
        raise BusinessError("新增联调项目必须指定线路", "WORKSPACE_SCOPE_REQUIRED", status_code=422)
    if not _is_super(user) and user.get("lineId") != int(line_id):
        raise BusinessError("当前账号没有编辑该线路项目的权限", "WORKSPACE_FORBIDDEN", status_code=403)
    repository = _repository(request)
    if not any(item["id"] == int(line_id) for item in repository.list_lines(include_disabled=True)):
        raise BusinessError("所属线路不存在", "WORKSPACE_SCOPE_NOT_FOUND", status_code=404)
    if not any(item["id"] == payload.profession_id for item in repository.list_professions(include_disabled=True)):
        raise BusinessError("所属专业不存在", "WORKSPACE_SCOPE_NOT_FOUND", status_code=404)
    payload.line_id = int(line_id)
    return {"data": repository.create_project(payload)}


@router.put("/projects/{project_id}")
def update_project(project_id: int, payload: ProjectWriteRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    current = next(
        (item for item in _repository(request).list_projects(include_disabled=True) if item["id"] == project_id),
        None,
    )
    if current is None:
        raise BusinessError("联调项目不存在", "WORKSPACE_PROJECT_NOT_FOUND", status_code=404)
    line_id = payload.line_id or current.get("lineId")
    repository = _repository(request)
    if not any(item["id"] == int(line_id) for item in repository.list_lines(include_disabled=True)):
        raise BusinessError("所属线路不存在", "WORKSPACE_SCOPE_NOT_FOUND", status_code=404)
    if not any(item["id"] == payload.profession_id for item in repository.list_professions(include_disabled=True)):
        raise BusinessError("所属专业不存在", "WORKSPACE_SCOPE_NOT_FOUND", status_code=404)
    if not _is_super(user) and (current.get("lineId") != user.get("lineId") or current.get("lineId") != line_id):
        raise BusinessError("当前账号没有编辑该联调项目的权限", "WORKSPACE_FORBIDDEN", status_code=403)
    payload.line_id = int(line_id)
    return {"data": repository.update_project(project_id, payload)}


@router.get("/configs")
def list_configs(
    request: Request,
    line_id: Annotated[int, Query(alias="lineId", gt=0)],
    profession_id: Annotated[int, Query(alias="professionId", gt=0)],
    project_id: Annotated[int, Query(alias="projectId", gt=0)],
    debug_subitem_id: Annotated[str | None, Query(alias="debugSubitemId")] = None,
    debug_division_id: Annotated[str | None, Query(alias="debugDivisionId")] = None,
    include_disabled: Annotated[bool, Query(alias="includeDisabled")] = False,
) -> dict[str, object]:
    _current_user(request)
    scope = ScopeSelection(
        lineId=line_id,
        professionId=profession_id,
        projectId=project_id,
        debugSubitemId=debug_subitem_id,
        debugDivisionId=debug_division_id,
    )
    data = _repository(request).list_configs(scope, include_disabled)
    return {"data": data, "meta": {"count": len(data)}}


@router.post("/configs")
def create_config(payload: ConfigWriteRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    _require_edit_scope(user, payload.scope)
    return {"data": _repository(request).create_config(payload, int(user["id"]))}


@router.put("/configs/{config_id}")
def update_config(config_id: str, payload: ConfigWriteRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    _require_edit_scope(user, payload.scope)
    return {"data": _repository(request).update_config(config_id, payload, int(user["id"]))}


@router.post("/configs/copy")
def copy_config(payload: ConfigCopyRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    _require_edit_scope(user, payload.target)
    return {"data": _repository(request).copy_configs(payload, int(user["id"]))}


@router.post("/configs/batch-copy")
def batch_copy_configs(payload: BatchConfigCopyRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    _require_edit_scope(user, payload.target)
    return {"data": _repository(request).copy_configs(payload, int(user["id"]))}


@router.post("/configs/import")
def import_configs(payload: ConfigImportRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    _require_edit_scope(user, payload.scope)
    return {"data": _repository(request).import_configs(payload, int(user["id"]))}


@router.post("/configs/import/preview")
def preview_import_configs(payload: ConfigImportRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    _require_edit_scope(user, payload.scope)
    return {"data": _repository(request).preview_import(payload)}


@router.get("/debug-items")
def list_debug_items(
    request: Request,
    line_id: Annotated[int, Query(alias="lineId", gt=0)],
    profession_id: Annotated[int, Query(alias="professionId", gt=0)],
    project_id: Annotated[int, Query(alias="projectId", gt=0)],
    category: Annotated[str, Query(pattern="^(debug_subitems|debug_divisions)$")],
    parent_id: Annotated[str | None, Query(alias="parentId")] = None,
    include_disabled: Annotated[bool, Query(alias="includeDisabled")] = False,
) -> dict[str, object]:
    user = _current_user(request)
    scope = ScopeSelection(lineId=line_id, professionId=profession_id, projectId=project_id)
    if include_disabled:
        _require_edit_scope(user, scope)
    data = _repository(request).list_debug_items(scope, category, parent_id, include_disabled)
    return {"data": data, "meta": {"count": len(data)}}


@router.post("/debug-items")
def create_debug_item(payload: DebugItemWriteRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    _require_edit_scope(user, payload.scope)
    return {"data": _repository(request).save_debug_item(payload)}


@router.post("/debug-items/batch")
def create_debug_items_batch(payload: DebugItemsBatchWriteRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    _require_edit_scope(user, payload.scope)
    return {"data": _repository(request).save_debug_items_batch(payload)}


@router.put("/debug-items/{item_id}")
def update_debug_item(item_id: str, payload: DebugItemWriteRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    _require_edit_scope(user, payload.scope)
    return {"data": _repository(request).save_debug_item(payload, item_id)}


@router.delete("/debug-items/{item_id}")
def delete_debug_item(
    item_id: str,
    request: Request,
    line_id: Annotated[int, Query(alias="lineId", gt=0)],
    profession_id: Annotated[int, Query(alias="professionId", gt=0)],
    project_id: Annotated[int, Query(alias="projectId", gt=0)],
    category: Annotated[str, Query(pattern="^(debug_subitems|debug_divisions)$")],
) -> dict[str, object]:
    user = _current_user(request)
    scope = ScopeSelection(lineId=line_id, professionId=profession_id, projectId=project_id)
    _require_edit_scope(user, scope)
    _repository(request).delete_debug_item(item_id, scope, category)
    return {"data": {"id": item_id, "deleted": True}}


@router.post("/debug-items/{item_id}/status")
def set_debug_item_status(
    item_id: str,
    enabled: bool,
    request: Request,
    line_id: Annotated[int, Query(alias="lineId", gt=0)],
    profession_id: Annotated[int, Query(alias="professionId", gt=0)],
    project_id: Annotated[int, Query(alias="projectId", gt=0)],
    category: Annotated[str, Query(pattern="^(debug_subitems|debug_divisions)$")],
) -> dict[str, object]:
    user = _current_user(request)
    scope = ScopeSelection(lineId=line_id, professionId=profession_id, projectId=project_id)
    _require_edit_scope(user, scope)
    return {"data": _repository(request).set_debug_item_status(item_id, scope, category, enabled)}


@router.post("/configs/{config_id}/status")
def set_config_status(config_id: str, enabled: bool, request: Request) -> dict[str, object]:
    user = _current_user(request)
    config = _repository(request).get_config(config_id, include_disabled=True)
    if config is None:
        raise BusinessError("联调配置不存在", "WORKSPACE_CONFIG_NOT_FOUND", status_code=404)
    _require_edit_scope(user, _scope_from_config(config))
    return {"data": _repository(request).disable_config(config_id, enabled, int(user["id"]))}


@router.get("/catalog")
def list_workspace_catalog(
    request: Request,
    line_id: Annotated[int, Query(alias="lineId", gt=0)],
    profession_id: Annotated[int, Query(alias="professionId", gt=0)],
    project_id: Annotated[int, Query(alias="projectId", gt=0)],
    category: Annotated[str, Query(pattern="^(equipment_types|disciplines|stations)$")],
    include_disabled: Annotated[bool, Query(alias="includeDisabled")] = False,
) -> dict[str, object]:
    user = _current_user(request)
    scope = ScopeSelection(lineId=line_id, professionId=profession_id, projectId=project_id)
    _require_edit_scope(user, scope) if include_disabled else None
    data = _repository(request).list_catalog_items(scope, category, include_disabled)
    return {"data": data, "meta": {"count": len(data)}}


@router.post("/catalog")
def create_workspace_catalog_item(payload: WorkspaceCatalogWriteRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    _require_edit_scope(user, payload.scope)
    return {"data": _repository(request).save_catalog_item(payload)}


@router.put("/catalog/{item_id}")
def update_workspace_catalog_item(
    item_id: str, payload: WorkspaceCatalogWriteRequest, request: Request
) -> dict[str, object]:
    user = _current_user(request)
    _require_edit_scope(user, payload.scope)
    return {"data": _repository(request).save_catalog_item(payload, item_id)}


@router.post("/catalog/{item_id}/status")
def set_workspace_catalog_status(
    item_id: str,
    enabled: bool,
    request: Request,
    line_id: Annotated[int, Query(alias="lineId", gt=0)],
    profession_id: Annotated[int, Query(alias="professionId", gt=0)],
    project_id: Annotated[int, Query(alias="projectId", gt=0)],
    category: Annotated[str, Query(pattern="^(equipment_types|disciplines|stations)$")],
) -> dict[str, object]:
    user = _current_user(request)
    scope = ScopeSelection(lineId=line_id, professionId=profession_id, projectId=project_id)
    _require_edit_scope(user, scope)
    current = next(
        (row for row in _repository(request).list_catalog_items(scope, category, True) if row["id"] == item_id),
        None,
    )
    if current is None:
        raise BusinessError("配置项目不存在", "WORKSPACE_CATALOG_NOT_FOUND", status_code=404)
    payload = WorkspaceCatalogWriteRequest(
        scope=scope,
        category=category,
        code=current["code"],
        name=current["name"],
        description=current["description"],
        sortOrder=current["sortOrder"],
        isEnabled=enabled,
    )
    return {"data": _repository(request).save_catalog_item(payload, item_id)}


@router.get("/template", response_class=Response)
def template(request: Request) -> Response:
    _current_user(request)
    content = _xls_workbook(
        {
            "数据导入模板": [
                ["设备编码", "设备类型", "设备中文", "联调配置编码"],
                ["DT-001", "垂梯", "垂梯 01", "FAS-垂梯-状态反馈"],
            ],
            "填写说明": [
                ["填写说明"],
                ["设备编码、设备类型、设备中文为原始设备版必填列。"],
                ["联调配置编码有值时按新配置匹配；留空时继续使用原有 FAS 兼容规则。"],
                ["其他业务列可以保留，系统按列名读取。"],
            ],
        }
    )
    return Response(
        content=content,
        media_type="application/vnd.ms-excel",
        headers={"Content-Disposition": "attachment; filename=excelforge-data-import-template.xls"},
    )


@router.get("/config-template", response_class=Response)
def config_template(
    request: Request,
    line_id: Annotated[int, Query(alias="lineId", gt=0)],
    profession_id: Annotated[int, Query(alias="professionId", gt=0)],
    project_id: Annotated[int, Query(alias="projectId", gt=0)],
) -> Response:
    """Download the configuration specification template with a concrete sample."""
    user = _current_user(request)
    scope = ScopeSelection(lineId=line_id, professionId=profession_id, projectId=project_id)
    config_items = _repository(request).list_configs(scope, include_disabled=True)
    header = [
        "业务显示ID",
        "联调配置编码",
        "调试子项",
        "调试分项",
        "说明",
        "步骤序号",
        "操作步骤",
        "输出序号",
        "预期结果",
        "责任专业",
    ]
    template_rows = [header]
    for item in config_items:
        first_config_row = True
        for step in item["steps"] or [{"description": "", "results": []}]:
            results = step["results"] or [{"description": ""}]
            for result_index, result in enumerate(results, start=1):
                template_rows.append(
                    [
                        item["businessId"] if first_config_row else "",
                        item["configCode"] if first_config_row else "",
                        "" if not first_config_row else "",
                        "" if not first_config_row else "",
                        item["description"] if first_config_row else "",
                        step.get("sortOrder", 1),
                        step["description"] if result_index == 1 else "",
                        result_index,
                        result["description"],
                        "、".join(result.get("responsibleDisciplines", [])),
                    ]
                )
                first_config_row = False
    if not config_items:
        template_rows.extend(
            [
                [
                    "",
                    "FAS-400V-切非",
                    "FAS设备信息监视",
                    "400V",
                    "",
                    1,
                    "FAS主机控制切非模块动作",
                    1,
                    "现场：现场400V抽屉柜动作",
                    "变电",
                ],
                ["", "", "", "", "", "", "", 2, "FAS主机：400V切非控制模块已下发信息", "自动化"],
                [
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    3,
                    "FAS图文工作站：收到400V切非控制模块已下发信息",
                    "自动化",
                ],
                [
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    4,
                    "综合监控：收到400V切非控制模块已下发报警、事件",
                    "自动化",
                ],
                ["", "", "", "", "", 2, "测试11234", 1, "测试1454", "自动化"],
                ["", "", "", "", "", "", "", 2, "测试245", "自动化"],
                ["", "", "", "", "", "", "", 3, "测试345", "通信"],
                ["", "", "", "", "", "", "", 4, "测试445", "变电"],
                [
                    "",
                    "FAS-声光报警器-声光报警控制",
                    "FAS设备信息监视",
                    "声光报警器",
                    "",
                    1,
                    "FAS主机控制声光报警器启动",
                    1,
                    "FAS主机：声光报警器控制模块已启动",
                    "自动化",
                ],
                ["", "", "", "", "", "", "", 2, "现场：现场声光已启动", "自动化"],
                [
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    3,
                    "FAS图文工作站：收到声光报警器控制模块已启动",
                    "自动化",
                ],
                [
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    4,
                    "综合监控：收到声光报警器控制模块已启动报警、事件",
                    "自动化",
                ],
                [
                    "",
                    "FAS-声光报警器-声光交替模块",
                    "FAS设备信息监视",
                    "声光交替模块",
                    "",
                    1,
                    "FAS主机控制声光交替模块动作",
                    1,
                    "FAS主机：声光交替控制模块已启动",
                    "自动化",
                ],
                ["", "", "", "", "", "", "", 2, "现场：现场声光交替已启动", "自动化"],
                [
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    3,
                    "FAS图文工作站：收到声光交替控制模块已启动",
                    "自动化",
                ],
                [
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    4,
                    "综合监控：收到声光交替控制模块已启动报警、事件",
                    "自动化",
                ],
            ]
        )
    instructions = [
        ["填写说明"],
        ["一个联调配置编码对应一套完整配置；每一行填写一个预期结果。"],
        ["同一配置的后续行可将联调配置编码、调试子项、调试分项和说明留空，系统沿用上一次填写的值。"],
        [
            "每个操作步骤的第一条结果填写步骤序号和操作步骤；同一步骤的后续结果行可以同时留空，系统会沿用上一条操作步骤。"
        ],
        ["输出序号控制同一步骤内预期结果的顺序；责任专业对应每条预期结果。"],
        ["调试子项必填；调试分项可留空，留空时规则直接归属该调试子项。未填写分类时使用当前页面选择的范围。"],
        ["新增配置时业务显示 ID 留空，由系统自动生成；已有配置的 ID 不能修改。"],
        ["多余列可以保留，系统只读取表头对应的列。"],
    ]
    _ = user
    return Response(
        content=_xls_workbook({"配置规范模板": template_rows, "填写说明": instructions}),
        media_type="application/vnd.ms-excel",
        headers={"Content-Disposition": "attachment; filename=excelforge-config-spec-template.xls"},
    )


@router.get("/users")
def list_users(request: Request) -> dict[str, object]:
    user = _current_user(request)
    if not _is_super(user):
        raise BusinessError("只有超级管理员可以管理账号", "WORKSPACE_ADMIN_REQUIRED", status_code=403)
    data = _repository(request).list_users()
    return {"data": data, "meta": {"count": len(data)}}


@router.post("/users")
def create_user(payload: UserWriteRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    if not _is_super(user):
        raise BusinessError("只有超级管理员可以管理账号", "WORKSPACE_ADMIN_REQUIRED", status_code=403)
    return {"data": _repository(request).create_user(payload)}


@router.put("/users/{user_id}")
def update_user(user_id: int, payload: UserWriteRequest, request: Request) -> dict[str, object]:
    user = _current_user(request)
    if not _is_super(user):
        raise BusinessError("只有超级管理员可以管理账号", "WORKSPACE_ADMIN_REQUIRED", status_code=403)
    return {"data": _repository(request).update_user(user_id, payload)}
