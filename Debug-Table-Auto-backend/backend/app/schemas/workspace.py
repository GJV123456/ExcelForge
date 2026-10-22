"""Schemas for the configurable line/profession/project workspace."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.schemas.common import ApiModel

Text = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=512)]

Role = Literal["super_admin", "line_admin", "professional_configurator"]


class ScopeSelection(ApiModel):
    line_id: int = Field(alias="lineId", gt=0)
    profession_id: int = Field(alias="professionId", gt=0)
    project_id: int = Field(alias="projectId", gt=0)
    debug_subitem_id: str | None = Field(default=None, alias="debugSubitemId", max_length=64)
    debug_division_id: str | None = Field(default=None, alias="debugDivisionId", max_length=64)


class LineWriteRequest(ApiModel):
    code: Text
    name: Text
    sort_order: int = Field(default=1, alias="sortOrder", gt=0)
    is_enabled: bool = Field(default=True, alias="isEnabled")


class ProfessionWriteRequest(ApiModel):
    code: Text
    name: Text
    parent_id: int | None = Field(default=None, alias="parentId", gt=0)
    sort_order: int = Field(default=1, alias="sortOrder", gt=0)
    is_enabled: bool = Field(default=True, alias="isEnabled")


class ProfessionBatchWriteRequest(ApiModel):
    professions: list[ProfessionWriteRequest] = Field(min_length=1, max_length=100)


class ProjectWriteRequest(ApiModel):
    line_id: int | None = Field(default=None, alias="lineId", gt=0)
    profession_id: int = Field(alias="professionId", gt=0)
    code: Text
    name: Text
    description: str = ""
    sort_order: int = Field(default=1, alias="sortOrder", gt=0)
    is_enabled: bool = Field(default=True, alias="isEnabled")
    engine_code: str = Field(default="", alias="engineCode", max_length=32)


class ConfigResultWriteRequest(ApiModel):
    description: Text
    responsible_disciplines: list[Text] = Field(default_factory=list, alias="responsibleDisciplines")


class ConfigStepWriteRequest(ApiModel):
    description: Text
    ratio_change: Literal["是", "否"] = Field(default="否", alias="ratioChange")
    results: list[ConfigResultWriteRequest] = Field(default_factory=list)
    sort_order: int = Field(default=1, alias="sortOrder", gt=0)
    is_enabled: bool = Field(default=True, alias="isEnabled")


class ConfigWriteRequest(ApiModel):
    scope: ScopeSelection
    config_code: Text = Field(alias="configCode")
    device_type: str = Field(default="", alias="deviceType", max_length=512)
    description: str = ""
    steps: list[ConfigStepWriteRequest] = Field(default_factory=list)
    is_enabled: bool = Field(default=True, alias="isEnabled")
    debug_subitem_id: str | None = Field(default=None, alias="debugSubitemId", max_length=64)
    debug_division_id: str | None = Field(default=None, alias="debugDivisionId", max_length=64)


class ConfigCopyRequest(ApiModel):
    source_config_id: str = Field(alias="sourceConfigId", min_length=1, max_length=64)
    target: ScopeSelection


class BatchConfigCopyRequest(ApiModel):
    source_config_ids: list[str] = Field(alias="sourceConfigIds", min_length=1, max_length=500)
    target: ScopeSelection


class ConfigImportRequest(ApiModel):
    scope: ScopeSelection
    rows: list[dict[str, object]] = Field(min_length=1, max_length=10000)
    decisions: dict[str, Literal["overwrite", "skip"]] = Field(default_factory=dict)


class DebugItemWriteRequest(ApiModel):
    scope: ScopeSelection
    category: Literal["debug_subitems", "debug_divisions"]
    parent_id: str | None = Field(default=None, alias="parentId", max_length=64)
    code: str = Field(default="", max_length=100)
    name: Text
    description: str = Field(default="", max_length=2000)
    sort_order: int = Field(default=1, alias="sortOrder", gt=0)
    is_enabled: bool = Field(default=True, alias="isEnabled")


class DebugItemsBatchWriteRequest(ApiModel):
    scope: ScopeSelection
    category: Literal["debug_subitems", "debug_divisions"]
    parent_id: str | None = Field(default=None, alias="parentId", max_length=64)
    names: list[Text] = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    sort_order: int = Field(default=1, alias="sortOrder", gt=0)


class WorkspaceCatalogWriteRequest(ApiModel):
    scope: ScopeSelection
    category: Literal["equipment_types", "disciplines", "stations"]
    code: str = Field(default="", max_length=100)
    name: Text
    parent_id: str | None = Field(default=None, alias="parentId", max_length=64)
    description: str = Field(default="", max_length=2000)
    sort_order: int = Field(default=1, alias="sortOrder", gt=0)
    is_enabled: bool = Field(default=True, alias="isEnabled")


class WorkspaceStationsBatchWriteRequest(ApiModel):
    scope: ScopeSelection
    names: list[Text] = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    sort_order: int = Field(default=1, alias="sortOrder", gt=0)
    is_enabled: bool = Field(default=True, alias="isEnabled")


class UserWriteRequest(ApiModel):
    username: Text
    # Passwords intentionally have no length or composition rules.
    password: str | None = None
    display_name: Text = Field(alias="displayName")
    role: Role
    line_id: int | None = Field(default=None, alias="lineId", gt=0)
    profession_id: int | None = Field(default=None, alias="professionId", gt=0)
    is_enabled: bool = Field(default=True, alias="isEnabled")
