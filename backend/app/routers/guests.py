# backend/app/routers/guests.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.deps import get_current_user, get_supabase, limiter
from app.models.common import ApiResponse, PaginatedResponse
from app.models.guest import GuestResponse, GuestListItem
from app.services.audit import write_audit_log

router = APIRouter(tags=["guests"])


@router.get("/guests", response_model=PaginatedResponse[GuestListItem])
@limiter.limit("60/minute")
async def list_guests(
    request: Request,
    q: str | None = Query(None, description="Full-text search"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db=Depends(get_supabase),
):
    hotel_id = current_user["hotel_id"]
    offset = (page - 1) * page_size

    result = (
        db.table("guests")
        .select("id, first_name, last_name, doc_type, doc_number_last4, created_at", count="exact")
        .eq("hotel_id", hotel_id)
        .is_("deleted_at", None)
        .range(offset, offset + page_size - 1)
        .execute()
    )

    await write_audit_log(
        db=db, hotel_id=hotel_id, user_id=current_user["user_id"],
        action="guests.list",
        ip_address=request.client.host if request.client else None,
    )

    items = [GuestListItem(**g) for g in (result.data or [])]
    return PaginatedResponse(data=items, total=result.count or 0, page=page, page_size=page_size)


@router.get("/guests/{guest_id}", response_model=ApiResponse[GuestResponse])
@limiter.limit("60/minute")
async def get_guest(
    request: Request,
    guest_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_supabase),
):
    result = (
        db.table("guests")
        .select("*")
        .eq("id", guest_id)
        .eq("hotel_id", current_user["hotel_id"])
        .is_("deleted_at", None)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Guest not found")

    await write_audit_log(
        db=db, hotel_id=current_user["hotel_id"], user_id=current_user["user_id"],
        action="guest.read", resource_type="guest", resource_id=guest_id,
        ip_address=request.client.host if request.client else None,
    )

    return ApiResponse.ok(GuestResponse(**result.data))


@router.delete("/guests/{guest_id}", response_model=ApiResponse[None])
@limiter.limit("10/minute")
async def delete_guest(
    request: Request,
    guest_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_supabase),
):
    now_iso = datetime.now(timezone.utc).isoformat()
    result = (
        db.table("guests")
        .update({"deleted_at": now_iso, "deletion_requested_at": now_iso})
        .eq("id", guest_id)
        .eq("hotel_id", current_user["hotel_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Guest not found")

    await write_audit_log(
        db=db, hotel_id=current_user["hotel_id"], user_id=current_user["user_id"],
        action="guest.deleted", resource_type="guest", resource_id=guest_id,
        metadata={"doc_number_last4": result.data[0].get("doc_number_last4")},
        ip_address=request.client.host if request.client else None,
    )

    return ApiResponse.ok(None)
