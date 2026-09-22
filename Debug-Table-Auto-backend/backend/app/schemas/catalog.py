"""Public response structures for the read-only rule catalog."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator
from typing_extensions import TypedDict

from app.schemas.excel import ApiModel

TrimmedText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)
]
FreeText = Annotated[str, StringConstraints(strict=True, strip_whitespace=True)]


class CatalogMeta(TypedDict):
    count: int


class EquipmentTypeSummary(TypedDict):
    id: int
    code: str
    name: str


class EquipmentTypeItem(EquipmentTypeSummary):
    description: str
    sortOrder: int
    isEnabled: bool


class EquipmentSubtypeItem(TypedDict):
    id: int
    parentEquipmentTypeId: int
    code: str
    name: str
    sortOrder: int
    isEnabled: bool
    statuses: list[str]


class EquipmentStatusWriteRequest(ApiModel):
    statuses: list[TrimmedText] = Field(default_factory=list, max_length=100)

    @field_validator("statuses")
    @classmethod
    def validate_unique_statuses(cls, value: list[str]) -> list[str]:
        normalized = [item.casefold() for item in value]
        if len(set(normalized)) != len(normalized):
            raise ValueError("statuses must not contain duplicates")
        return value


class EquipmentSubtypeWriteRequest(ApiModel):
    id: int | None = Field(default=None, gt=0)
    name: TrimmedText
    sort_order: int = Field(alias="sortOrder", gt=0)
    is_enabled: bool = Field(alias="isEnabled", default=True)
    statuses: list[TrimmedText] = Field(default_factory=list, max_length=100)

    @field_validator("statuses")
    @classmethod
    def validate_unique_statuses(cls, value: list[str]) -> list[str]:
        normalized = [item.casefold() for item in value]
        if len(set(normalized)) != len(normalized):
            raise ValueError("statuses must not contain duplicates")
        return value


class EquipmentHierarchyItem(EquipmentTypeItem):
    subtypes: list[EquipmentSubtypeItem]
    statuses: list[str]


class DisciplineItem(TypedDict):
    id: int
    code: str
    name: str


class ResultOutputItem(TypedDict):
    id: int
    description: str
    sortOrder: int
    responsibleDisciplines: list[DisciplineItem]


class OperationStepItem(TypedDict):
    id: int
    description: str
    ratioChange: str
    sortOrder: int
    results: list[ResultOutputItem]


class TestContentItem(TypedDict):
    id: int
    equipmentTypeId: int
    code: str
    content: str
    description: str
    revision: int
    sortOrder: int
    isEnabled: bool
    equipmentSubtype: str
    equipmentStatus: str
    equipmentType: EquipmentTypeSummary
    operationSteps: list[OperationStepItem]


class EquipmentTypeListResponse(TypedDict):
    data: list[EquipmentTypeItem]
    meta: CatalogMeta


class EquipmentHierarchyResponse(TypedDict):
    data: list[EquipmentHierarchyItem]
    meta: CatalogMeta


class EquipmentSubtypeListResponse(TypedDict):
    data: list[EquipmentSubtypeItem]
    meta: CatalogMeta


class TestContentListResponse(TypedDict):
    data: list[TestContentItem]
    meta: CatalogMeta


class TestContentDetailResponse(TypedDict):
    data: TestContentItem


class DisciplineListItem(TypedDict):
    id: int
    code: str
    name: str
    description: str
    sortOrder: int
    isEnabled: bool


class StationListItem(TypedDict):
    id: int
    code: str
    name: str
    description: str
    sortOrder: int
    isEnabled: bool


class DisciplineListResponse(TypedDict):
    data: list[DisciplineListItem]
    meta: CatalogMeta


class StationListResponse(TypedDict):
    data: list[StationListItem]
    meta: CatalogMeta


class EquipmentTypeWriteRequest(ApiModel):
    code: TrimmedText | None = None
    name: TrimmedText
    description: FreeText = ""
    sort_order: int = Field(alias="sortOrder", gt=0)
    is_enabled: bool = Field(alias="isEnabled", default=True)
    subtypes: list[EquipmentSubtypeWriteRequest] | None = None

    @field_validator("subtypes")
    @classmethod
    def validate_unique_subtypes(
        cls, value: list[EquipmentSubtypeWriteRequest] | None
    ) -> list[EquipmentSubtypeWriteRequest] | None:
        if value is None:
            return None
        normalized = [item.name.casefold() for item in value]
        if len(set(normalized)) != len(normalized):
            raise ValueError("subtypes must not contain duplicates")
        return value


class DisciplineWriteRequest(ApiModel):
    code: TrimmedText | None = None
    name: TrimmedText
    description: FreeText = ""
    sort_order: int = Field(alias="sortOrder", gt=0)
    is_enabled: bool = Field(alias="isEnabled", default=True)


class StationWriteRequest(ApiModel):
    code: TrimmedText | None = None
    name: TrimmedText
    description: FreeText = ""
    sort_order: int = Field(alias="sortOrder", gt=0)
    is_enabled: bool = Field(alias="isEnabled", default=True)


class ResultOutputWriteRequest(ApiModel):
    description: TrimmedText
    sort_order: int = Field(alias="sortOrder", gt=0)
    responsible_discipline_ids: list[int] = Field(
        alias="responsibleDisciplineIds", min_length=1, max_length=1
    )
    is_enabled: bool = Field(alias="isEnabled", default=True)

    @field_validator("responsible_discipline_ids")
    @classmethod
    def validate_unique_disciplines(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("responsibleDisciplineIds must not contain duplicates")
        return value


class OperationStepWriteRequest(ApiModel):
    description: TrimmedText
    ratio_change: Literal["是", "否"] = Field(alias="ratioChange")
    sort_order: int = Field(alias="sortOrder", gt=0)
    results: list[ResultOutputWriteRequest] = Field(min_length=1)
    is_enabled: bool = Field(alias="isEnabled", default=True)

    @field_validator("results")
    @classmethod
    def validate_unique_result_sort_order(
        cls, value: list[ResultOutputWriteRequest]
    ) -> list[ResultOutputWriteRequest]:
        sort_orders = [item.sort_order for item in value]
        if len(set(sort_orders)) != len(sort_orders):
            raise ValueError("results.sortOrder must not contain duplicates")
        return value


class TestContentWriteRequest(ApiModel):
    equipment_type_id: int = Field(alias="equipmentTypeId", gt=0)
    code: TrimmedText | None = None
    content: TrimmedText
    equipment_subtype: FreeText = Field(default="", alias="equipmentSubtype")
    equipment_status: FreeText = Field(default="", alias="equipmentStatus")
    description: FreeText = ""
    revision: int = Field(default=1, gt=0)
    sort_order: int = Field(alias="sortOrder", gt=0)
    is_enabled: bool = Field(alias="isEnabled", default=True)
    operation_steps: list[OperationStepWriteRequest] = Field(
        alias="operationSteps", min_length=1
    )

    @field_validator("operation_steps")
    @classmethod
    def validate_unique_step_sort_order(
        cls, value: list[OperationStepWriteRequest]
    ) -> list[OperationStepWriteRequest]:
        sort_orders = [item.sort_order for item in value]
        if len(set(sort_orders)) != len(sort_orders):
            raise ValueError("operationSteps.sortOrder must not contain duplicates")
        return value
