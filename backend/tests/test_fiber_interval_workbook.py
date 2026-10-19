import xlrd

from app.schemas.excel import ExcelProcessRequest
from app.services.excel_service import build_workbook


def _request(*contents: str) -> ExcelProcessRequest:
    return ExcelProcessRequest.model_validate(
        {
            "testLocation": {
                "type": "站点",
                "direction": "",
                "startStation": "嘉庚体育馆站",
                "endStation": "嘉庚体育馆站",
            },
            "testContents": [
                {
                    "sortIndex": index,
                    "generatedContent": content,
                    "equipmentType": "监视模块",
                    "equipmentSubtype": "感温光纤",
                }
                for index, content in enumerate(contents, start=1)
            ],
        }
    )


def test_interval_direction_and_name_flow_into_steps_and_results():
    output = build_workbook(
        _request(
            "角石区间上行感温光纤报警反馈监视模块N1L1M24",
            "角石区间下行感温光纤报警反馈监视模块N1L1M25",
            "角龟区间上行感温光纤报警反馈监视模块N1L1M26",
        )
    )
    workbook = xlrd.open_workbook(file_contents=output)

    assert workbook.sheet_names() == ["测试地点", "测试内容", "操作步骤", "结果输出", "参数公式"]
    steps = workbook.sheet_by_name("操作步骤")
    assert steps.cell_value(2, 1) == "现场测试人员触发角石上行区间感温光纤主机火警"
    assert steps.cell_value(3, 1) == "现场测试人员触发角石下行区间感温光纤主机火警"
    assert steps.cell_value(4, 1) == "现场测试人员触发角龟上行区间感温光纤主机火警"

    results = workbook.sheet_by_name("结果输出")
    assert results.cell_value(2, 1) == "现场：角石上行区间感温光纤主机火警指示灯亮"
    assert results.cell_value(5, 1) == "综合监控：收到角石上行区间感温光纤主机通道报警、事件、位置正确"
    assert results.cell_value(6, 1) == "现场：角石下行区间感温光纤主机火警指示灯亮"
    assert results.cell_value(8, 1) == "FAS图文工作站：收到角石下行区间感温光纤主机火警报文"
    assert results.cell_value(2, 0) == 3
    assert results.cell_value(5, 0) == 3
    assert results.cell_value(6, 0) == 4
    assert results.cell_value(2, 2) == "自动化"
    assert results.cell_value(2, 3) == ""

    content_sheet = workbook.sheet_by_name("测试内容")
    assert content_sheet.cell_value(2, 0) == "角石区间上行感温光纤报警反馈监视模块N1L1M24"
    assert content_sheet.cell_value(5, 0) == "end"
    formula = workbook.sheet_by_name("参数公式")
    assert formula.cell_value(2, 0) == "end"
    assert all(formula.cell_value(row, 0) != "end" for row in range(3, formula.nrows))


def test_comprehensive_fiber_fault_keeps_its_fault_steps():
    workbook = xlrd.open_workbook(
        file_contents=build_workbook(_request("站厅B端感温光纤综合故障监视模块N1L1M23"))
    )
    steps = workbook.sheet_by_name("操作步骤")
    results = workbook.sheet_by_name("结果输出")

    assert steps.cell_value(2, 1) == "现场测试人员模拟触发感温光纤主机故障"
    assert results.cell_value(2, 1) == "现场：感温光纤主机故障指示灯亮"
