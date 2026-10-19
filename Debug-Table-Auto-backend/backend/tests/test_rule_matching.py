from __future__ import annotations

import pytest

from app.exceptions import BusinessError
from app.schemas.excel_v2 import V2TestContent
from app.services.formal_processor import _catalog_steps


class _CatalogStub:
    def __init__(self, rules: list[dict[str, object]]) -> None:
        self.rules = rules

    def list_test_contents(self, *, equipment_type: str) -> list[dict[str, object]]:
        return self.rules


def _rule(status: str, description: str) -> dict[str, object]:
    return {
        "content": "监视模块",
        "equipmentSubtype": "吸气式主机",
        "equipmentStatus": status,
        "operationSteps": [
            {
                "description": description,
                "ratioChange": "否",
                "results": [
                    {
                        "description": f"{description}结果",
                        "responsibleDisciplines": [{"name": "自动化"}],
                    }
                ],
            }
        ],
    }


def _item(status: str) -> V2TestContent:
    return V2TestContent(
        sortIndex=1,
        generatedContent=f"站厅B端ASD-1{status}监视模块N1L1M68",
        equipmentChinese=f"站厅B端ASD-1{status}监视模块N1L1M68",
        equipmentType="监视模块",
        equipmentSubtype="吸气式主机",
        equipmentStatus=status,
    )


@pytest.mark.parametrize("status", ["预警", "火警", "故障", "远程复位"])
def test_catalog_matching_selects_matching_status_before_generic_content(status: str) -> None:
    rules = [
        _rule("预警", "预警操作"),
        _rule("火警", "火警操作"),
        _rule("故障", "故障操作"),
        _rule("远程复位", "复位操作"),
    ]

    steps = _catalog_steps(_item(status), _CatalogStub(rules))  # type: ignore[arg-type]

    expected_description = "复位操作" if status == "远程复位" else f"{status}操作"
    assert steps[0]["description"] == expected_description


def test_catalog_matching_does_not_fall_back_to_a_different_subtype() -> None:
    wrong_subtype = {
        **_rule("切非", "400V切非操作"),
        "equipmentSubtype": "400V切非",
    }
    item = _item("远程复位").model_copy(
        update={"equipment_type": "控制模块", "equipment_subtype": "吸气式主机"}
    )

    with pytest.raises(BusinessError) as error:
        _catalog_steps(item, _CatalogStub([wrong_subtype]))  # type: ignore[arg-type]

    assert error.value.code == "CATALOG_RULE_NOT_FOUND"


def test_fault_is_inferred_from_generated_content_when_frontend_status_is_missing() -> None:
    rules = [
        _rule("预警", "预警操作"),
        _rule("火警", "火警操作"),
        _rule("故障", "故障操作"),
    ]
    item = _item("故障").model_copy(
        update={
            "equipment_status": "",
            "generated_content": "站厅B端ASD-1故障监视模块N1L1M70",
            "equipment_chinese": "站厅B端ASD-1",
        }
    )

    steps = _catalog_steps(item, _CatalogStub(rules))  # type: ignore[arg-type]

    assert steps[0]["description"] == "故障操作"


@pytest.mark.parametrize(
    ("equipment_type", "subtype", "statuses", "status"),
    [
        ("监视模块", "AFC", ["AFC切非反馈", "AFC切非"], "AFC切非反馈"),
        ("监视模块", "感温光纤", ["区间上行感温光纤报警反馈", "区间下行感温光纤报警反馈"], "区间下行感温光纤报警反馈"),
        ("监视模块", "消防泵", ["消防泵动作反馈", "消防泵故障反馈"], "消防泵故障反馈"),
    ],
)
def test_shared_generic_titles_select_exact_status_for_other_equipment(
    equipment_type: str,
    subtype: str,
    statuses: list[str],
    status: str,
) -> None:
    rules = [
        {**_rule(candidate_status, f"步骤-{candidate_status}"), "equipmentSubtype": subtype}
        for candidate_status in statuses
    ]
    item = _item(status).model_copy(
        update={
            "equipment_type": equipment_type,
            "equipment_subtype": subtype,
            "equipment_status": status,
        }
    )

    steps = _catalog_steps(item, _CatalogStub(rules))  # type: ignore[arg-type]

    assert steps[0]["description"] == f"步骤-{status}"
