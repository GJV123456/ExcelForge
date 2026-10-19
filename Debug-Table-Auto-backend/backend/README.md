# ExcelForge backend

Frontend developers should use the Chinese rule catalog contract in
[`docs/catalog-api.zh-CN.md`](../docs/catalog-api.zh-CN.md).

The backend uses the repository-local Python 3.11 virtual environment at
`backend/.venv`. Do not install project dependencies into the global Python or
commit the virtual environment.

## Setup on Windows

```powershell
& 'E:\Python 11\python.exe' -m venv backend\.venv
& 'backend\.venv\Scripts\python.exe' -m pip install -r backend\requirements-dev.txt
& 'backend\.venv\Scripts\python.exe' -m pip check
```

## Tests and quality checks

```powershell
Push-Location backend
& '.\.venv\Scripts\python.exe' -m pytest tests
& '.\.venv\Scripts\python.exe' -m ruff check --no-cache app tests
& '.\.venv\Scripts\python.exe' -m mypy app
Pop-Location
```

## Run the API

Mock mode is the default. It returns a visibly marked BIFF8 `.xls` transport
test file and never presents it as a formal import workbook.

```powershell
& 'backend\.venv\Scripts\python.exe' -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Configuration uses environment variables:

- `EXCELFORGE_MODE=mock|formal` (default: `mock`)
- `EXCELFORGE_MOCK_DELAY_SECONDS=0..10` (default: `0`; use `2` for Loading tests)
- `EXCELFORGE_TEMPLATE_PATH=<path>` (optional explicit template override)
- `EXCELFORGE_DATABASE_PATH=<path>` (optional SQLite database override)
- `EXCELFORGE_AUTH_USERNAME=<username>` (optional one-time legacy account migration)
- `EXCELFORGE_AUTH_PASSWORD=<password>` (optional one-time legacy account migration)
- `EXCELFORGE_AUTH_DISPLAY_NAME=<name>` (optional migration display name)

Endpoints currently available:

- `GET /api/health`
- `POST /api/auth/register` (first-account initialization)
- `POST /api/auth/login`
- `POST /api/auth/change-password`
- `POST /api/auth/logout`
- `GET /api/catalog/equipment-types`
- `GET /api/catalog/equipment-hierarchy` (parent types with child subtypes)
- `GET /api/catalog/equipment-types/{id}/subtypes`
- `PUT /api/catalog/equipment-subtypes/{id}/statuses`
- `GET /api/catalog/stations`
- `POST /api/catalog/stations`
- `PUT /api/catalog/stations/{id}`
- `DELETE /api/catalog/stations/{id}`
- `POST /api/catalog/equipment-types`
- `PUT /api/catalog/equipment-types/{id}`
- `DELETE /api/catalog/equipment-types/{id}`
- `GET /api/catalog/disciplines`
- `POST /api/catalog/disciplines`
- `PUT /api/catalog/disciplines/{id}`
- `DELETE /api/catalog/disciplines/{id}`
- `GET /api/catalog/test-contents`
- `GET /api/catalog/test-contents/{id}`
- `POST /api/catalog/test-contents`
- `PUT /api/catalog/test-contents/{id}`
- `DELETE /api/catalog/test-contents/{id}`
- `GET /api/generations`
- `GET /api/generations/{id}`
- `GET /api/generations/{id}/download`
- `POST /api/excel/process` (frozen v1 Mock contract)
- `POST /api/v2/excel/process` (formal workbook generation; rules may come from SQLite)

The v1 endpoint remains unchanged and does not accept formal rule fields. To
generate `最终导入表.xls`, set `EXCELFORGE_MODE=formal` before startup and use
the v2 endpoint. The frontend may include `operationSteps` for compatibility;
when omitted, the backend resolves the fixed operation-step/result hierarchy
from SQLite using `equipmentSubtype` first and `equipmentType` as a fallback.
Each matching catalog rule must provide at least one step, one result per step,
and one enabled responsible discipline per result. Test styles and parameter
formulas are not accepted; the formal workbook keeps `结果输出` column D empty
and only writes `参数公式!A3=end`.

Formal filenames use `最终导入表_站点_类型1_类型2_YYYYMMDDHHMMSS.xls`, with
equipment types de-duplicated in first-appearance order. Source runs use the
repository template. A packaged executable instead expects
`联调测试表导入模版.xls` in the same directory as the executable unless
`EXCELFORGE_TEMPLATE_PATH` is set.

## Test rule database

The rule catalog uses SQLite and stores the reusable relationship:

```text
equipment type -> test content -> operation step -> result output
                                             -> responsible discipline(s)
```

The application creates the empty schema on the first catalog request; it does
not seed or guess business rules. Source runs default to
`backend/data/excelforge.sqlite3`. Packaged Windows runs default to an
`excelforge.sqlite3` sibling of the executable; packaged Linux runs default to
`~/.local/share/debug-table-auto/excelforge.sqlite3`. Set
`EXCELFORGE_DATABASE_PATH` when another managed location is required. Database
files, WAL files and shared-memory files are runtime data and are not committed.

CSV may be added later as a human-maintained import/export format, but it is not
the primary store: this catalog has several one-to-many relationships plus a
many-to-many responsibility mapping, which require foreign-key, uniqueness and
transaction checks. A future CSV import must therefore validate all files and
load them into SQLite atomically; this phase intentionally does not define or
guess that import format.

### Tables and fields

#### `schema_migrations`

| Field | SQLite type | Constraint | Purpose |
| --- | --- | --- | --- |
| `version` | INTEGER | primary key | Applied schema version |
| `applied_at` | TEXT | not null | UTC migration timestamp |

#### `equipment_types`

| Field | SQLite type | Constraint | Purpose |
| --- | --- | --- | --- |
| `id` | INTEGER | primary key | Internal identifier |
| `code` | TEXT | not null, case-insensitive unique | Stable API/business code |
| `name` | TEXT | not null | Frontend display name, for example `烟感` |
| `description` | TEXT | not null, default empty | Optional explanation |
| `sort_order` | INTEGER | not null, default `0` | Display order |
| `is_enabled` | INTEGER | not null, `0` or `1` | Soft enable switch |
| `created_at` | TEXT | not null | UTC creation timestamp |
| `updated_at` | TEXT | not null | UTC update timestamp |

#### `test_contents`

| Field | SQLite type | Constraint | Purpose |
| --- | --- | --- | --- |
| `id` | INTEGER | primary key | Internal identifier |
| `code` | TEXT | not null, case-insensitive unique | Stable test-content code |
| `equipment_type_id` | INTEGER | not null, FK `equipment_types.id` | Applicable equipment type |
| `content` | TEXT | not null | Reusable test-content text/template |
| `description` | TEXT | not null, default empty | Optional explanation |
| `revision` | INTEGER | not null, positive, default `1` | Business-rule revision |
| `sort_order` | INTEGER | not null, default `0` | Display order within a type |
| `is_enabled` | INTEGER | not null, `0` or `1` | Soft enable switch |
| `created_at` | TEXT | not null | UTC creation timestamp |
| `updated_at` | TEXT | not null | UTC update timestamp |

#### `operation_steps`

| Field | SQLite type | Constraint | Purpose |
| --- | --- | --- | --- |
| `id` | INTEGER | primary key | Internal identifier |
| `test_content_id` | INTEGER | not null, FK `test_contents.id` | Owning test content |
| `description` | TEXT | not null | Operation-step text |
| `ratio_change` | TEXT | not null, `是` or `否` | Whether this step changes ratio |
| `sort_order` | INTEGER | not null, unique per test content | Step order |
| `is_enabled` | INTEGER | not null, `0` or `1` | Soft enable switch |
| `created_at` | TEXT | not null | UTC creation timestamp |
| `updated_at` | TEXT | not null | UTC update timestamp |

#### `result_outputs`

| Field | SQLite type | Constraint | Purpose |
| --- | --- | --- | --- |
| `id` | INTEGER | primary key | Internal identifier |
| `operation_step_id` | INTEGER | not null, FK `operation_steps.id` | Owning operation step |
| `description` | TEXT | not null | Expected result/output text |
| `sort_order` | INTEGER | not null, unique per operation step | Result order |
| `is_enabled` | INTEGER | not null, `0` or `1` | Soft enable switch |
| `created_at` | TEXT | not null | UTC creation timestamp |
| `updated_at` | TEXT | not null | UTC update timestamp |

#### `disciplines`

| Field | SQLite type | Constraint | Purpose |
| --- | --- | --- | --- |
| `id` | INTEGER | primary key | Internal identifier |
| `code` | TEXT | not null, case-insensitive unique | Stable discipline code |
| `name` | TEXT | not null | Frontend display name |
| `description` | TEXT | not null, default empty | Optional explanation |
| `sort_order` | INTEGER | not null, default `0` | Display order |
| `is_enabled` | INTEGER | not null, `0` or `1` | Soft enable switch |
| `created_at` | TEXT | not null | UTC creation timestamp |
| `updated_at` | TEXT | not null | UTC update timestamp |

#### `result_output_disciplines`

| Field | SQLite type | Constraint | Purpose |
| --- | --- | --- | --- |
| `result_output_id` | INTEGER | composite PK, FK `result_outputs.id` | Result output |
| `discipline_id` | INTEGER | composite PK, FK `disciplines.id` | Responsible discipline |
| `sort_order` | INTEGER | not null, unique per result output | Discipline order |

`result_output_disciplines` is a many-to-many join so one result may be owned by
multiple disciplines without duplicating its text. Foreign keys use restrictive
delete rules for the main hierarchy; join rows cascade when either side is
deleted. Soft disabling is preferred for business records already in use.

Subtype status choices are maintained with
`PUT /api/catalog/equipment-subtypes/{id}/statuses` and a body such as
`{"statuses":["预警","火警"]}`. Removing or renaming a status already used by
an existing test rule is rejected with `CATALOG_STATUS_IN_USE`, so catalog
maintenance cannot silently break formal generation.

#### Generation history tables (Schema v2)

Successful `POST /api/v2/excel/process` calls are recorded transactionally after
the workbook passes its self-check and before the file response is returned.
`generation_runs` stores the request ID, output filename and SHA-256, generation
time, location and hierarchy counts. `generation_test_contents`,
`generation_operation_steps`, `generation_result_outputs` and
`generation_result_disciplines` store the submitted text snapshot, original
sequence and the one-based Excel row number in the corresponding output sheet.
Failed workbook generation or failed database transactions return no file and do
not leave a partial history hierarchy.

The response header `X-Generation-ID` identifies the saved run. Read summaries
with `GET /api/generations?limit=50&offset=0`, read the full nested snapshot
with `GET /api/generations/{id}`, and download the exact generated workbook
again with `GET /api/generations/{id}/download`. Successful generations store
the generated BIFF8 bytes in `generation_runs.output_blob`, so a later download
does not regenerate the workbook or re-match catalog rules. Older history rows
created before file retention was enabled may have no downloadable bytes.

The history deliberately stores request snapshots rather than matching catalog
rules by text, because text matching may be ambiguous. Exact catalog foreign
keys can be added later when the frontend contract supplies stable rule IDs.

| Table | Fields |
| --- | --- |
| `generation_runs` | `id`, `request_id`, `generated_at`, `filename`, `output_sha256`, `output_blob`, `location_type`, `direction`, `start_station`, `end_station`, `test_content_count`, `operation_step_count`, `result_output_count`, `discipline_count`, `created_at` |
| `generation_test_contents` | `id`, `generation_id`, `sequence_index`, `sort_index`, `generated_content`, `equipment_code`, `equipment_type`, `excel_row_number` |
| `generation_operation_steps` | `id`, `generation_test_content_id`, `sequence_index`, `description`, `ratio_change`, `excel_row_number` |
| `generation_result_outputs` | `id`, `generation_operation_step_id`, `sequence_index`, `description`, `excel_row_number` |
| `generation_result_disciplines` | `generation_result_output_id`, `sequence_index`, `discipline_name` |

All child tables use foreign keys with cascading deletion from a generation run.
Sequence and Excel row constraints prevent duplicate mappings within one run.
`discipline_count` counts submitted responsibility occurrences, not distinct
discipline names.

### Read API contract

`GET /api/catalog/equipment-types` returns enabled equipment types in
`sortOrder, id` order. `GET /api/catalog/test-contents` returns the complete
nested mapping and accepts optional query parameters `equipmentType` (matches
code or name) and `includeDisabled=false`. `GET
/api/catalog/test-contents/{id}` returns one nested mapping or HTTP 404.

Example list response:

```json
{
  "data": [
    {
      "id": 1,
      "code": "SMOKE_STANDARD",
      "content": "站厅B端车控室烟感",
      "description": "",
      "revision": 1,
      "sortOrder": 1,
      "equipmentType": {"id": 1, "code": "SMOKE", "name": "烟感"},
      "operationSteps": [
        {
          "id": 1,
          "description": "触发设备报警",
          "ratioChange": "否",
          "sortOrder": 1,
          "results": [
            {
              "id": 1,
              "description": "系统正确显示报警",
              "sortOrder": 1,
              "responsibleDisciplines": [
                {"id": 1, "code": "FAS", "name": "FAS"}
              ]
            }
          ]
        }
      ]
    }
  ],
  "meta": {"count": 1}
}
```

These endpoints are read-only. Business-data write/import endpoints, audit
history and rule editing are intentionally outside this phase because their
authorization and import format are not yet defined.

### Database maintenance

To import the supplied rule workbook into the catalog (the import runs in one
transaction and replaces catalog business rows), install the development
dependencies and run:

```powershell
& '.\\.venv\\Scripts\\python.exe' scripts\\import_rule_workbook.py `
  'C:\\Users\\Administrator\\Desktop\\操作步骤(1).xlsx'
```

The current imported database contains 30 equipment types, 71 rules, 92
operation steps and 343 result outputs. The smoke-detector rule contains two
steps and seven outputs, each assigned to the 自动化 discipline.

The parent/child equipment hierarchy is stored in `equipment_type_subtypes`.
After importing or refreshing the workbook, seed the hierarchy (idempotently):

```powershell
& '.\\.venv\\Scripts\\python.exe' scripts\\seed_equipment_hierarchy.py `
  --database '.\\data\\excelforge.sqlite3'
```

See [`docs/equipment-type-hierarchy-api.zh-CN.md`](../docs/equipment-type-hierarchy-api.zh-CN.md)
for the response contract used by the frontend tree selector.

Run maintenance from `backend/` with the project venv. `init` creates or upgrades
the schema, `check` runs SQLite integrity and foreign-key checks, and `backup`
uses the SQLite online backup API for a consistent copy. Backup refuses to
overwrite an existing file.

```powershell
Push-Location backend
& '.\.venv\Scripts\python.exe' -m app.db.maintenance init
& '.\.venv\Scripts\python.exe' -m app.db.maintenance check
& '.\.venv\Scripts\python.exe' -m app.db.maintenance backup `
  --output '.\backups\excelforge-20260812.sqlite3'
Pop-Location
```

To maintain another database, put the global option before the command:

```powershell
& '.\.venv\Scripts\python.exe' -m app.db.maintenance `
  --database 'D:\data\excelforge.sqlite3' check
```

The separately installed `sqlite3` CLI can inspect the same file, but the app
does not require it; Python's built-in SQLite driver owns runtime access.

### Database login contract

`POST /api/auth/register` creates the first account and returns a session. Once
initialized, registration is closed. `POST /api/auth/login` accepts
`username`, `password`, `agree` and `remember`; `remember` controls the database
session lifetime. `POST /api/auth/change-password` changes the current user's
password, and `POST /api/auth/logout` revokes the current session.

```json
{
  "data": {
    "token": "opaque-session-token",
    "userInfo": {"username": "operator", "name": "操作员"}
  }
}
```

The database stores only a password hash, never the plaintext password. Explicit
legacy environment credentials, when present, are imported once into an empty
database and are not checked directly on subsequent logins. Sessions are stored
as SHA-256 token hashes with an expiration time.

## Local Windows release

Build the frontend first, then invoke the release scripts with the backend venv:

```powershell
cd frontend
npm.cmd run build
cd ..\backend
& '.\.venv\Scripts\python.exe' ..\scripts\build_release.py
& '.\.venv\Scripts\python.exe' ..\scripts\verify_release.py
```

The onedir output and versioned ZIP are written under `build/release/`. The
staging frontend, PyInstaller work files, release directory, venv and Node
dependencies remain ignored by Git.

GitHub Release is triggered only by a successfully merged pull request whose
base branch is `main`. Windows is distributed as a complete onedir ZIP because
the EXE requires its sibling `_internal` runtime directory. Linux is distributed
as an amd64 Debian package installing under `/opt/debug-table-auto`, with a
`debug-table-auto` launcher. The approved import template is included both in
each platform package and as a standalone Release asset.
