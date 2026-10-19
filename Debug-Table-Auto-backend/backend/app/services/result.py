"""Common result type for generated workbook responses."""

from __future__ import annotations

from dataclasses import dataclass

XLS_MEDIA_TYPE = "application/vnd.ms-excel"


@dataclass(frozen=True, slots=True)
class ProcessedFile:
    content: bytes
    filename: str
    media_type: str = XLS_MEDIA_TYPE
