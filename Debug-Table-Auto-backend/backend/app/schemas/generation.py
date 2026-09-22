"""Public response structures for generated workbook history."""

from __future__ import annotations

from typing_extensions import TypedDict

from app.schemas.catalog import CatalogMeta


class GenerationDisciplineItem(TypedDict):
    sequenceIndex: int
    name: str


class GenerationResultItem(TypedDict):
    sequenceIndex: int
    description: str
    excelRowNumber: int
    responsibleDisciplines: list[GenerationDisciplineItem]


class GenerationStepItem(TypedDict):
    sequenceIndex: int
    description: str
    ratioChange: str
    excelRowNumber: int
    results: list[GenerationResultItem]


class GenerationContentItem(TypedDict):
    sequenceIndex: int
    sortIndex: int
    generatedContent: str
    equipmentCode: str
    equipmentType: str
    excelRowNumber: int
    operationSteps: list[GenerationStepItem]


class GenerationLocation(TypedDict):
    type: str
    direction: str
    startStation: str
    endStation: str


class GenerationCounts(TypedDict):
    testContents: int
    operationSteps: int
    resultOutputs: int
    disciplines: int


class GenerationSummary(TypedDict):
    id: str
    requestId: str
    generatedAt: str
    filename: str
    outputSha256: str
    testLocation: GenerationLocation
    counts: GenerationCounts


class GenerationDetail(GenerationSummary):
    testContents: list[GenerationContentItem]


class GenerationListResponse(TypedDict):
    data: list[GenerationSummary]
    meta: CatalogMeta


class GenerationDetailResponse(TypedDict):
    data: GenerationDetail
