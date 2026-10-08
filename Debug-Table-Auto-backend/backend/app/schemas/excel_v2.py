"""Versioned v2 request schema for frontend rows and catalog-backed rules."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.schemas.excel import ApiModel, PositiveSortIndex, StrictText, TestLocation

NonEmptyText = Annotated[
    str,
    StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=32_767),
]
IntegrationCode = Annotated[
    str,
    StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=32),
]


class V2ResultOutput(ApiModel):
    description: NonEmptyText
    responsible_disciplines: list[NonEmptyText] = Field(
        alias="responsibleDisciplines", min_length=1
    )


class V2OperationStep(ApiModel):
    description: NonEmptyText
    ratio_change: Literal["是", "否"] = Field(alias="ratioChange")
    results: Annotated[list[V2ResultOutput], Field(min_length=1)]


class V2TestContent(ApiModel):
    sort_index: PositiveSortIndex = Field(alias="sortIndex")
    generated_content: NonEmptyText = Field(alias="generatedContent")
    equipment_chinese: StrictText = Field(default="", alias="equipmentChinese", max_length=32_767)
    signal_description: StrictText = Field(default="", alias="signalDescription", max_length=32_767)
    additional_code: StrictText = Field(default="", alias="additionalCode", max_length=32_767)
    equipment_code: StrictText = Field(default="", alias="equipmentCode", max_length=32_767)
    equipment_type: StrictText = Field(default="", alias="equipmentType", max_length=32_767)
    equipment_subtype: StrictText = Field(default="", alias="equipmentSubtype", max_length=32_767)
    equipment_status: StrictText = Field(default="", alias="equipmentStatus", max_length=32_767)
    # Kept as an input-only compatibility field for older frontend bundles.
    # It is derived for preview display and is not used for workbook generation.
    interval_name: StrictText = Field(default="", alias="intervalName", max_length=32_767)
    # The frontend may send steps explicitly for backwards compatibility.  In
    # the database-driven flow this field is omitted and the backend resolves
    # the fixed operation/result hierarchy from the catalog.
    operation_steps: Annotated[
        list[V2OperationStep], Field(alias="operationSteps", min_length=1)
    ] = Field(default_factory=list)


class ExcelProcessV2Request(ApiModel):
    integration_code: IntegrationCode = Field(default="T19", alias="integrationCode")
    test_location: TestLocation = Field(alias="testLocation")
    test_contents: Annotated[list[V2TestContent], Field(alias="testContents", min_length=1)]
