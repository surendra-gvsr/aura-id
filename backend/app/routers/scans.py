# backend/app/routers/scans.py
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from cryptography.fernet import Fernet

from app.deps import get_current_user, get_current_workstation, get_supabase, limiter
from app.models.common import ApiResponse
from app.models.scan import ScanResponse, ParsedID
from app.services.image_pipeline import run_pipeline
from app.services.storage import upload_scan_image
from app.services.audit import write_audit_log
from app.utils.pii import mask_doc_number
from app.config import settings

router = APIRouter(tags=["scans"])


def get_vertex_client():
    from app.services.vertex_ai import VertexAIClient
    return VertexAIClient()


def _encrypt_doc_number(doc_number: str) -> bytes:
    f = Fernet(settings.doc_encryption_key.encode())
    return f.encrypt(doc_number.encode())


@router.get("/scans/pending-type", response_model=ApiResponse[list[ScanResponse]])
@limiter.limit("30/minute")
async def get_pending_type_scans(
    request: Request,
    current_workstation: dict = Depends(get_current_workstation),
    db=Depends(get_supabase),
):
    result = (
        db.table("scans")
        .select("*")
        .eq("hotel_id", current_workstation["hotel_id"])
        .eq("status", "parsed")
        .order("created_at", desc=False)
        .limit(10)
        .execute()
    )
    scans = []
    for s in result.data or []:
        parsed_data = ParsedID.model_validate(s["parsed_data"]) if s.get("parsed_data") else None
        scans.append(ScanResponse(
            id=s["id"], status=s["status"], parsed_data=parsed_data,
            face_region_blacked_out=s.get("face_region_blacked_out", True),
            created_at=s["created_at"], parsed_at=s.get("parsed_at"),
        ))
    return ApiResponse.ok(scans)


@router.post("/scans/{scan_id}/mark-typed", response_model=ApiResponse[ScanResponse])
async def mark_scan_typed(
    scan_id: str,
    current_workstation: dict = Depends(get_current_workstation),
    db=Depends(get_supabase),
):
    now_iso = datetime.now(timezone.utc).isoformat()
    result = (
        db.table("scans")
        .update({"status": "typed", "typed_at": now_iso})
        .eq("id", scan_id)
        .eq("hotel_id", current_workstation["hotel_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Scan not found")
    s = result.data[0]
    return ApiResponse.ok(ScanResponse(
        id=s["id"], status=s["status"],
        face_region_blacked_out=s.get("face_region_blacked_out", True),
        created_at=s["created_at"], typed_at=s.get("typed_at"),
    ))


@router.get("/scans/{scan_id}", response_model=ApiResponse[ScanResponse])
async def get_scan(
    scan_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_supabase),
):
    result = (
        db.table("scans")
        .select("*")
        .eq("id", scan_id)
        .eq("hotel_id", current_user["hotel_id"])
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Scan not found")

    await write_audit_log(
        db=db, hotel_id=current_user["hotel_id"], user_id=current_user["user_id"],
        action="scan.read", resource_type="scan", resource_id=scan_id,
        ip_address=request.client.host if request.client else None,
    )

    s = result.data
    parsed_data = ParsedID.model_validate(s["parsed_data"]) if s.get("parsed_data") else None
    return ApiResponse.ok(ScanResponse(
        id=s["id"], status=s["status"], parsed_data=parsed_data,
        face_region_blacked_out=s.get("face_region_blacked_out", True),
        created_at=s["created_at"], parsed_at=s.get("parsed_at"),
        typed_at=s.get("typed_at"), error_message=s.get("error_message"),
    ))


@router.post("/scans", status_code=201, response_model=ApiResponse[ScanResponse])
@limiter.limit("100/minute")
async def create_scan(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db=Depends(get_supabase),
):
    scan_id = str(uuid.uuid4())
    hotel_id = current_user["hotel_id"]
    user_id = current_user["user_id"]

    image_bytes = await file.read()
    content_type = file.content_type or "image/jpeg"

    db.table("scans").insert({
        "id": scan_id,
        "hotel_id": hotel_id,
        "user_id": user_id,
        "status": "pending",
        "face_region_blacked_out": True,
    }).execute()

    try:
        pipeline_result = await run_pipeline(image_bytes, content_type, scan_id=scan_id)
    except (ValueError, RuntimeError) as exc:
        db.table("scans").update({"status": "failed", "error_message": str(exc)}).eq("id", scan_id).execute()
        raise HTTPException(status_code=422, detail=str(exc))

    hotel_result = db.table("hotels").select("image_retention_hours").eq("id", hotel_id).single().execute()
    retention_hours = hotel_result.data.get("image_retention_hours", 24) if hotel_result.data else 24
    deletion_at = (datetime.now(timezone.utc) + timedelta(hours=retention_hours)).isoformat()

    image_path = upload_scan_image(db=db, hotel_id=hotel_id, scan_id=scan_id, image_bytes=pipeline_result.image_bytes)

    vertex_client = get_vertex_client()
    try:
        parsed: ParsedID = await vertex_client.extract_id_fields(pipeline_result.image_bytes)
    except Exception as exc:
        db.table("scans").update({"status": "failed", "error_message": str(exc), "image_path": image_path}).eq("id", scan_id).execute()
        raise HTTPException(status_code=502, detail="AI extraction failed")

    guest_id = None
    if parsed.last_name:
        guest_payload = {
            "hotel_id": hotel_id,
            "first_name": parsed.first_name,
            "last_name": parsed.last_name,
            "dob": parsed.dob.isoformat() if parsed.dob else None,
            "doc_type": parsed.doc_type,
            "doc_country": parsed.doc_country,
            "nationality": parsed.nationality,
            "doc_number_last4": mask_doc_number(parsed.doc_number)[-4:] if parsed.doc_number else None,
        }
        if parsed.doc_number:
            guest_payload["doc_number_encrypted"] = _encrypt_doc_number(parsed.doc_number).decode()

        if parsed.doc_number and parsed.doc_country:
            guest_result = db.table("guests").upsert(
                guest_payload, on_conflict="hotel_id,doc_number_last4,doc_country"
            ).execute()
        else:
            guest_result = db.table("guests").insert(guest_payload).execute()

        if guest_result.data:
            guest_id = guest_result.data[0]["id"]

    now_iso = datetime.now(timezone.utc).isoformat()
    db.table("scans").update({
        "status": "parsed",
        "guest_id": guest_id,
        "image_path": image_path,
        "image_deletion_scheduled_at": deletion_at,
        "face_region_blacked_out": True,
        "parsed_data": parsed.model_dump(mode="json"),
        "parsed_at": now_iso,
    }).eq("id", scan_id).execute()

    await write_audit_log(
        db=db,
        hotel_id=hotel_id,
        user_id=user_id,
        action="scan.parsed",
        resource_type="scan",
        resource_id=scan_id,
        metadata={"doc_type": parsed.doc_type, "doc_country": parsed.doc_country, "confidence": parsed.confidence},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return ApiResponse.ok(ScanResponse(
        id=scan_id,
        status="parsed",
        parsed_data=parsed,
        face_region_blacked_out=True,
        created_at=now_iso,
        parsed_at=now_iso,
    ))
