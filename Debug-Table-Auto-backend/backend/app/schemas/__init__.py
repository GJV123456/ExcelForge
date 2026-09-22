"""External API schemas."""

from app.schemas.excel import ExcelProcessRequest, TestContent, TestLocation
from app.schemas.excel_v2 import ExcelProcessV2Request

__all__ = ["ExcelProcessRequest", "ExcelProcessV2Request", "TestContent", "TestLocation"]
