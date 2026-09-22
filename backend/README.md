# ExcelForge backend

## Run

```powershell
cd D:\ExcelForge\backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

## API

- `POST /api/auth/login`
- `POST /api/excel/process`

`/api/excel/process` accepts:

```json
{
  "testLocation": {
    "type": "站点",
    "direction": "",
    "startStation": "嘉庚体育馆站",
    "endStation": "嘉庚体育馆站",
    "stations": ["嘉庚体育馆站"]
  },
  "testContents": [
    {
      "sortIndex": 1,
      "equipmentChinese": "站厅B端会务室",
      "signalDescription": "",
      "additionalCode": "",
      "generatedContent": "站厅B端会务室温感N1L1D22",
      "equipmentCode": "N1L1D22",
      "equipmentType": "温感",
      "equipmentSubtype": "",
      "equipmentStatus": ""
    }
  ]
}

