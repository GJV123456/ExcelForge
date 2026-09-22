from __future__ import annotations

from io import BytesIO

import xlwt

from app.schemas.excel import ExcelProcessRequest


def build_workbook(payload: ExcelProcessRequest) -> bytes:
    book = xlwt.Workbook(encoding="utf-8")
    sheet = book.add_sheet("结果")
    headers = [
        "sortIndex",
        "equipmentChinese",
        "signalDescription",
        "additionalCode",
        "generatedContent",
        "equipmentCode",
        "equipmentType",
        "equipmentSubtype",
        "equipmentStatus",
    ]
    for col, header in enumerate(headers):
        sheet.write(0, col, header)
    for row_index, item in enumerate(payload.testContents, start=1):
        values = [
            item.sortIndex,
            item.equipmentChinese,
            item.signalDescription,
            item.additionalCode,
            item.generatedContent,
            item.equipmentCode,
            item.equipmentType,
            item.equipmentSubtype,
            item.equipmentStatus,
        ]
        for col, value in enumerate(values):
            sheet.write(row_index, col, value)
    output = BytesIO()
    book.save(output)
    return output.getvalue()

