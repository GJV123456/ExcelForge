"""HTTP-independent formal workbook model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LocationRow:
    location_type: str
    direction: str
    start_station: str
    end_station: str


@dataclass(frozen=True, slots=True)
class ResultRow:
    description: str
    responsible_disciplines: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OperationStepRow:
    description: str
    ratio_change: str
    results: tuple[ResultRow, ...]


@dataclass(frozen=True, slots=True)
class TestContentRow:
    sort_index: int
    generated_content: str
    equipment_code: str
    equipment_type: str
    operation_steps: tuple[OperationStepRow, ...]


@dataclass(frozen=True, slots=True)
class FormalWorkbook:
    location: LocationRow
    test_contents: tuple[TestContentRow, ...]
