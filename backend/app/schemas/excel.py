from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

StrictText = Annotated[str, StringConstraints(strict=True)]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=False)


class TestLocation(ApiModel):
    type: StrictText
    direction: StrictText = ""
    startStation: StrictText = ""
    endStation: StrictText = ""
    stations: list[StrictText] = Field(default_factory=list)


class TestContent(ApiModel):
    sortIndex: Annotated[int, Field(ge=1)]
    equipmentChinese: StrictText = ""
    signalDescription: StrictText = ""
    additionalCode: StrictText = ""
    generatedContent: StrictText
    equipmentCode: StrictText = ""
    equipmentType: StrictText = ""
    equipmentSubtype: StrictText = ""
    equipmentStatus: StrictText = ""


class ExcelProcessRequest(ApiModel):
    testLocation: TestLocation
    testContents: list[TestContent]


class ExcelProcessV2Request(ExcelProcessRequest):
    integrationCode: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=32)] = "T19"
