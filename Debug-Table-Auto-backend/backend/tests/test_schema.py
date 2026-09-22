from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.excel import ExcelProcessRequest


def _payload() -> dict[str, object]:
    return {
        "testLocation": {
            "type": "站点",
            "direction": "上行",
            "startStation": "1",
            "endStation": "2",
        },
        "testContents": [
            {
                "sortIndex": 1,
                "generatedContent": "站厅B端车控室烟感N1L1D01",
                "equipmentCode": "N1L1D01",
                "equipmentType": "烟感",
            }
        ],
    }


def test_v1_schema_preserves_aliases_and_chinese() -> None:
    payload = _payload()
    request = ExcelProcessRequest.model_validate(payload)

    assert request.model_dump(by_alias=True) == payload
    assert request.test_contents[0].sort_index == 1


@pytest.mark.parametrize("value", ["1", 1.0, True])
def test_sort_index_is_a_strict_integer(value: object) -> None:
    payload = _payload()
    contents = payload["testContents"]
    assert isinstance(contents, list)
    contents[0]["sortIndex"] = value  # type: ignore[index]

    with pytest.raises(ValidationError):
        ExcelProcessRequest.model_validate(payload)


def test_extra_fields_are_rejected() -> None:
    payload = _payload()
    payload["sourceData"] = []

    with pytest.raises(ValidationError):
        ExcelProcessRequest.model_validate(payload)
