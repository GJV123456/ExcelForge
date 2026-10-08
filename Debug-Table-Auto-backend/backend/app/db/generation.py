"""Transactional generation history persistence and queries."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.db.catalog import CatalogRepository
from app.schemas.excel_v2 import ExcelProcessV2Request
from app.schemas.generation import (
    GenerationContentItem,
    GenerationCounts,
    GenerationDetail,
    GenerationDisciplineItem,
    GenerationLocation,
    GenerationResultItem,
    GenerationStepItem,
    GenerationSummary,
)


def _last_row_id(cursor: sqlite3.Cursor) -> int:
    if cursor.lastrowid is None:
        raise RuntimeError("SQLite insert did not return a row ID")
    return cursor.lastrowid


class GenerationRepository:
    """Persist successful formal generations in the catalog database."""

    def __init__(self, database_path: Path) -> None:
        self.database = CatalogRepository(database_path)

    def record_success(
        self,
        request: ExcelProcessV2Request,
        *,
        request_id: str,
        generated_at: datetime,
        filename: str,
        output: bytes,
    ) -> str:
        """Atomically snapshot the request hierarchy and workbook row mappings."""
        self.database.ensure_schema()
        generation_id = str(uuid4())
        step_count = sum(len(content.operation_steps) for content in request.test_contents)
        result_count = sum(
            len(step.results)
            for content in request.test_contents
            for step in content.operation_steps
        )
        discipline_count = sum(
            len(result.responsible_disciplines)
            for content in request.test_contents
            for step in content.operation_steps
            for result in step.results
        )
        location = request.test_location

        with closing(self.database._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO generation_runs(
                    id, integration_code, request_id, generated_at, filename, output_sha256,
                    output_blob,
                    location_type, direction, start_station, end_station,
                    test_content_count, operation_step_count, result_output_count,
                    discipline_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generation_id,
                    request.integration_code,
                    request_id,
                    generated_at.isoformat(),
                    filename,
                    hashlib.sha256(output).hexdigest().upper(),
                    output,
                    location.location_type,
                    location.direction,
                    location.start_station,
                    location.end_station,
                    len(request.test_contents),
                    step_count,
                    result_count,
                    discipline_count,
                ),
            )

            next_step_excel_row = 3
            next_result_excel_row = 3
            for content_sequence, content in enumerate(request.test_contents, start=1):
                content_cursor = connection.execute(
                    """
                    INSERT INTO generation_test_contents(
                        generation_id, sequence_index, sort_index, generated_content,
                        equipment_code, equipment_type, excel_row_number
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        generation_id,
                        content_sequence,
                        content.sort_index,
                        content.generated_content,
                        content.equipment_code,
                        content.equipment_type,
                        content_sequence + 2,
                    ),
                )
                content_id = _last_row_id(content_cursor)
                for step_sequence, step in enumerate(content.operation_steps, start=1):
                    step_cursor = connection.execute(
                        """
                        INSERT INTO generation_operation_steps(
                            generation_test_content_id, sequence_index, description,
                            ratio_change, excel_row_number
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            content_id,
                            step_sequence,
                            step.description,
                            step.ratio_change,
                            next_step_excel_row,
                        ),
                    )
                    next_step_excel_row += 1
                    step_id = _last_row_id(step_cursor)
                    for result_sequence, result in enumerate(step.results, start=1):
                        result_cursor = connection.execute(
                            """
                            INSERT INTO generation_result_outputs(
                                generation_operation_step_id, sequence_index,
                                description, excel_row_number
                            ) VALUES (?, ?, ?, ?)
                            """,
                            (
                                step_id,
                                result_sequence,
                                result.description,
                                next_result_excel_row,
                            ),
                        )
                        next_result_excel_row += 1
                        result_id = _last_row_id(result_cursor)
                        connection.executemany(
                            """
                            INSERT INTO generation_result_disciplines(
                                generation_result_output_id, sequence_index, discipline_name
                            ) VALUES (?, ?, ?)
                            """,
                            (
                                (result_id, discipline_sequence, discipline)
                                for discipline_sequence, discipline in enumerate(
                                    result.responsible_disciplines, start=1
                                )
                            ),
                        )
        return generation_id

    def list_generations(
        self, *, limit: int, offset: int, integration_code: str | None = None
    ) -> list[GenerationSummary]:
        self.database.ensure_schema()
        with closing(self.database._connect()) as connection, connection:
            if integration_code:
                rows = connection.execute(
                    """
                    SELECT * FROM generation_runs
                    WHERE integration_code = ?
                    ORDER BY generated_at DESC, created_at DESC, id DESC
                    LIMIT ? OFFSET ?
                    """,
                    (integration_code, limit, offset),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM generation_runs
                    ORDER BY generated_at DESC, created_at DESC, id DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()
        return [self._summary(row) for row in rows]

    def get_generation(self, generation_id: str) -> GenerationDetail | None:
        self.database.ensure_schema()
        with closing(self.database._connect()) as connection, connection:
            run = connection.execute(
                "SELECT * FROM generation_runs WHERE id = ?", (generation_id,)
            ).fetchone()
            if run is None:
                return None
            rows = connection.execute(
                """
                SELECT
                    gc.sequence_index AS content_sequence,
                    gc.sort_index,
                    gc.generated_content,
                    gc.equipment_code,
                    gc.equipment_type,
                    gc.excel_row_number AS content_excel_row,
                    gs.id AS step_id,
                    gs.sequence_index AS step_sequence,
                    gs.description AS step_description,
                    gs.ratio_change,
                    gs.excel_row_number AS step_excel_row,
                    gr.id AS result_id,
                    gr.sequence_index AS result_sequence,
                    gr.description AS result_description,
                    gr.excel_row_number AS result_excel_row,
                    gd.sequence_index AS discipline_sequence,
                    gd.discipline_name
                FROM generation_test_contents AS gc
                LEFT JOIN generation_operation_steps AS gs
                    ON gs.generation_test_content_id = gc.id
                LEFT JOIN generation_result_outputs AS gr
                    ON gr.generation_operation_step_id = gs.id
                LEFT JOIN generation_result_disciplines AS gd
                    ON gd.generation_result_output_id = gr.id
                WHERE gc.generation_id = ?
                ORDER BY
                    gc.sequence_index,
                    gs.sequence_index,
                    gr.sequence_index,
                    gd.sequence_index
                """,
                (generation_id,),
            ).fetchall()

        detail = GenerationDetail(**self._summary(run), testContents=[])
        content_lookup: dict[int, GenerationContentItem] = {}
        step_lookup: dict[int, GenerationStepItem] = {}
        result_lookup: dict[int, GenerationResultItem] = {}
        for row in rows:
            content_sequence = int(row["content_sequence"])
            content = content_lookup.get(content_sequence)
            if content is None:
                content = GenerationContentItem(
                    sequenceIndex=content_sequence,
                    sortIndex=int(row["sort_index"]),
                    generatedContent=str(row["generated_content"]),
                    equipmentCode=str(row["equipment_code"]),
                    equipmentType=str(row["equipment_type"]),
                    excelRowNumber=int(row["content_excel_row"]),
                    operationSteps=[],
                )
                content_lookup[content_sequence] = content
                detail["testContents"].append(content)
            if row["step_id"] is None:
                continue
            step_id = int(row["step_id"])
            step = step_lookup.get(step_id)
            if step is None:
                step = GenerationStepItem(
                    sequenceIndex=int(row["step_sequence"]),
                    description=str(row["step_description"]),
                    ratioChange=str(row["ratio_change"]),
                    excelRowNumber=int(row["step_excel_row"]),
                    results=[],
                )
                step_lookup[step_id] = step
                content["operationSteps"].append(step)
            if row["result_id"] is None:
                continue
            result_id = int(row["result_id"])
            result = result_lookup.get(result_id)
            if result is None:
                result = GenerationResultItem(
                    sequenceIndex=int(row["result_sequence"]),
                    description=str(row["result_description"]),
                    excelRowNumber=int(row["result_excel_row"]),
                    responsibleDisciplines=[],
                )
                result_lookup[result_id] = result
                step["results"].append(result)
            if row["discipline_sequence"] is not None:
                result["responsibleDisciplines"].append(
                    GenerationDisciplineItem(
                        sequenceIndex=int(row["discipline_sequence"]),
                        name=str(row["discipline_name"]),
                    )
                )
        return detail

    def get_output(self, generation_id: str) -> tuple[str, bytes] | None:
        """Return the stored workbook bytes and filename for a successful run."""
        self.database.ensure_schema()
        with closing(self.database._connect()) as connection, connection:
            row = connection.execute(
                "SELECT filename, output_blob FROM generation_runs WHERE id = ?",
                (generation_id,),
            ).fetchone()
        if row is None or row["output_blob"] is None:
            return None
        return str(row["filename"]), bytes(row["output_blob"])

    @staticmethod
    def _summary(row: sqlite3.Row) -> GenerationSummary:
        return GenerationSummary(
            id=str(row["id"]),
            integrationCode=str(row["integration_code"]),
            requestId=str(row["request_id"]),
            generatedAt=str(row["generated_at"]),
            filename=str(row["filename"]),
            outputSha256=str(row["output_sha256"]),
            testLocation=GenerationLocation(
                type=str(row["location_type"]),
                direction=str(row["direction"]),
                startStation=str(row["start_station"]),
                endStation=str(row["end_station"]),
            ),
            counts=GenerationCounts(
                testContents=int(row["test_content_count"]),
                operationSteps=int(row["operation_step_count"]),
                resultOutputs=int(row["result_output_count"]),
                disciplines=int(row["discipline_count"]),
            ),
        )
