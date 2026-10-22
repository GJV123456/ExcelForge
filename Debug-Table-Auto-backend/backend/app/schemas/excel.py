"""Formal workbook request schema."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.schemas.common import ApiModel, PositiveSortIndex, StrictText, TestLocation

NonEmptyText = Annotated[
    str,
    StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=32_767),
]
IntegrationCode = Annotated[
    str,
    StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=32),
]


class ResultOutput(ApiModel):
    description: NonEmptyText
    responsible_disciplines: list[NonEmptyText] = Field(alias="responsibleDisciplines", min_length=1)


class OperationStep(ApiModel):
    description: NonEmptyText
    ratio_change: Literal["是", "否"] = Field(alias="ratioChange")
    results: Annotated[list[ResultOutput], Field(min_length=1)]


class FormalTestContent(ApiModel):
    sort_index: PositiveSortIndex = Field(alias="sortIndex")
    generated_content: NonEmptyText = Field(alias="generatedContent")
    equipment_chinese: StrictText = Field(default="", alias="equipmentChinese", max_length=32_767)
    signal_description: StrictText = Field(default="", alias="signalDescription", max_length=32_767)
    additional_code: StrictText = Field(default="", alias="additionalCode", max_length=32_767)
    equipment_code: StrictText = Field(default="", alias="equipmentCode", max_length=32_767)
    equipment_type: StrictText = Field(default="", alias="equipmentType", max_length=32_767)
    equipment_subtype: StrictText = Field(default="", alias="equipmentSubtype", max_length=32_767)
    equipment_status: StrictText = Field(default="", alias="equipmentStatus", max_length=32_767)
    interval_name: StrictText = Field(default="", alias="intervalName", max_length=32_767)
    integration_config_code: StrictText = Field(default="", alias="integrationConfigCode", max_length=512)
    operation_steps: Annotated[list[OperationStep], Field(alias="operationSteps", min_length=1)] = Field(
        default_factory=list
    )


class ExcelProcessRequest(ApiModel):
    integration_code: IntegrationCode = Field(default="T19", alias="integrationCode")
    source_filename: StrictText = Field(default="", alias="sourceFilename", max_length=512)
    test_location: TestLocation = Field(alias="testLocation")
    line_id: int | None = Field(default=None, alias="lineId", gt=0)
    profession_id: int | None = Field(default=None, alias="professionId", gt=0)
    project_id: int | None = Field(default=None, alias="projectId", gt=0)
    test_contents: Annotated[list[FormalTestContent], Field(alias="testContents", min_length=1)]
