"""Frozen v1 request schema for Excel processing."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_serializer

StrictText = Annotated[str, StringConstraints(strict=True)]
PositiveSortIndex = Annotated[int, Field(strict=True, gt=0)]


class ApiModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_by_alias=True,
        validate_by_name=False,
        serialize_by_alias=True,
    )


class TestLocation(ApiModel):
    location_type: StrictText = Field(alias="type")
    direction: StrictText
    start_station: StrictText = Field(alias="startStation")
    end_station: StrictText = Field(alias="endStation")
    stations: list[StrictText] = Field(default_factory=list)

    @model_serializer(mode="wrap")
    def _serialize_without_empty_stations(self, handler):  # type: ignore[no-untyped-def]
        data = handler(self)
        if not self.stations:
            data.pop("stations", None)
        return data


class TestContent(ApiModel):
    sort_index: PositiveSortIndex = Field(alias="sortIndex")
    generated_content: StrictText = Field(alias="generatedContent")
    equipment_code: StrictText = Field(alias="equipmentCode")
    equipment_type: StrictText = Field(alias="equipmentType")


class ExcelProcessRequest(ApiModel):
    test_location: TestLocation = Field(alias="testLocation")
    test_contents: list[TestContent] = Field(alias="testContents")
