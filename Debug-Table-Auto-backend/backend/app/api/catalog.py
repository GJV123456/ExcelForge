"""Read-only API for reusable test rules."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response

from app.db.catalog import CatalogRepository
from app.exceptions import BusinessError
from app.schemas.catalog import (
    DisciplineListResponse,
    DisciplineWriteRequest,
    EquipmentHierarchyResponse,
    EquipmentStatusWriteRequest,
    EquipmentSubtypeListResponse,
    EquipmentTypeListResponse,
    EquipmentTypeWriteRequest,
    StationListResponse,
    StationWriteRequest,
    TestContentDetailResponse,
    TestContentListResponse,
    TestContentWriteRequest,
)

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


def _repository(request: Request) -> CatalogRepository:
    return request.app.state.catalog_repository


@router.get("/equipment-types")
def list_equipment_types(
    request: Request,
    include_disabled: Annotated[bool, Query(alias="includeDisabled")] = False,
) -> EquipmentTypeListResponse:
    data = _repository(request).list_equipment_types(include_disabled=include_disabled)
    return {"data": data, "meta": {"count": len(data)}}


@router.get("/equipment-hierarchy")
def list_equipment_hierarchy(
    request: Request,
    include_disabled: Annotated[bool, Query(alias="includeDisabled")] = False,
) -> EquipmentHierarchyResponse:
    """Return parent equipment types and configured child subtypes for tree UIs."""
    data = _repository(request).list_equipment_hierarchy(
        include_disabled=include_disabled
    )
    return {"data": data, "meta": {"count": len(data)}}


@router.get("/equipment-types/{equipment_type_id}/subtypes")
def list_equipment_subtypes(
    equipment_type_id: int,
    request: Request,
    include_disabled: Annotated[bool, Query(alias="includeDisabled")] = False,
) -> EquipmentSubtypeListResponse:
    data = _repository(request).list_equipment_subtypes(
        equipment_type_id, include_disabled=include_disabled
    )
    return {"data": data, "meta": {"count": len(data)}}


@router.put("/equipment-subtypes/{subtype_id}/statuses")
def update_equipment_subtype_statuses(
    subtype_id: int,
    payload: EquipmentStatusWriteRequest,
    request: Request,
) -> dict[str, object]:
    item = _repository(request).replace_equipment_subtype_statuses(subtype_id, payload)
    return {"data": item}


@router.delete("/equipment-subtypes/{subtype_id}", status_code=204)
def delete_equipment_subtype(subtype_id: int, request: Request) -> Response:
    _repository(request).delete_equipment_subtype(subtype_id)
    return Response(status_code=204)


@router.get("/disciplines")
def list_disciplines(
    request: Request,
    include_disabled: Annotated[bool, Query(alias="includeDisabled")] = False,
) -> DisciplineListResponse:
    data = _repository(request).list_disciplines(include_disabled=include_disabled)
    return {"data": data, "meta": {"count": len(data)}}


@router.get("/stations")
def list_stations(
    request: Request,
    include_disabled: Annotated[bool, Query(alias="includeDisabled")] = False,
) -> StationListResponse:
    data = _repository(request).list_stations(include_disabled=include_disabled)
    return {"data": data, "meta": {"count": len(data)}}


@router.post("/stations")
def create_station(
    payload: StationWriteRequest, request: Request
) -> dict[str, object]:
    return {"data": _repository(request).create_station(payload)}


@router.put("/stations/{station_id}")
def update_station(
    station_id: int, payload: StationWriteRequest, request: Request
) -> dict[str, object]:
    return {"data": _repository(request).update_station(station_id, payload)}


@router.delete("/stations/{station_id}", status_code=204)
def delete_station(station_id: int, request: Request) -> Response:
    _repository(request).delete_station(station_id)
    return Response(status_code=204)


@router.get("/test-contents")
def list_test_contents(
    request: Request,
    equipment_type: Annotated[str | None, Query(alias="equipmentType")] = None,
    equipment_subtype: Annotated[str | None, Query(alias="equipmentSubtype")] = None,
    equipment_status: Annotated[str | None, Query(alias="equipmentStatus")] = None,
    include_disabled: Annotated[bool, Query(alias="includeDisabled")] = False,
) -> TestContentListResponse:
    data = _repository(request).list_test_contents(
        equipment_type=equipment_type,
        equipment_subtype=equipment_subtype,
        equipment_status=equipment_status,
        include_disabled=include_disabled,
    )
    return {"data": data, "meta": {"count": len(data)}}


@router.get("/test-contents/{content_id}")
def get_test_content(content_id: int, request: Request) -> TestContentDetailResponse:
    data = _repository(request).list_test_contents(content_id=content_id)
    if not data:
        raise BusinessError(
            "测试内容不存在或未启用",
            "CATALOG_TEST_CONTENT_NOT_FOUND",
            status_code=404,
        )
    return {"data": data[0]}


@router.post("/equipment-types")
def create_equipment_type(
    payload: EquipmentTypeWriteRequest, request: Request
) -> dict[str, object]:
    item = _repository(request).create_equipment_type(payload)
    return {"data": item}


@router.put("/equipment-types/{equipment_type_id}")
def update_equipment_type(
    equipment_type_id: int, payload: EquipmentTypeWriteRequest, request: Request
) -> dict[str, object]:
    item = _repository(request).update_equipment_type(equipment_type_id, payload)
    return {"data": item}


@router.delete("/equipment-types/{equipment_type_id}", status_code=204)
def delete_equipment_type(equipment_type_id: int, request: Request) -> Response:
    _repository(request).delete_equipment_type(equipment_type_id)
    return Response(status_code=204)


@router.post("/disciplines")
def create_discipline(payload: DisciplineWriteRequest, request: Request) -> dict[str, object]:
    item = _repository(request).create_discipline(payload)
    return {"data": item}


@router.put("/disciplines/{discipline_id}")
def update_discipline(
    discipline_id: int, payload: DisciplineWriteRequest, request: Request
) -> dict[str, object]:
    item = _repository(request).update_discipline(discipline_id, payload)
    return {"data": item}


@router.delete("/disciplines/{discipline_id}", status_code=204)
def delete_discipline(discipline_id: int, request: Request) -> Response:
    _repository(request).delete_discipline(discipline_id)
    return Response(status_code=204)


@router.post("/test-contents")
def create_test_content(
    payload: TestContentWriteRequest, request: Request
) -> dict[str, object]:
    item = _repository(request).create_test_content(payload)
    return {"data": item}


@router.put("/test-contents/{content_id}")
def update_test_content(
    content_id: int, payload: TestContentWriteRequest, request: Request
) -> dict[str, object]:
    item = _repository(request).update_test_content(content_id, payload)
    return {"data": item}


@router.delete("/test-contents/{content_id}", status_code=204)
def delete_test_content(content_id: int, request: Request) -> Response:
    _repository(request).delete_test_content(content_id)
    return Response(status_code=204)
