# backend/app/routers/hotels.py
from fastapi import APIRouter, Depends, HTTPException, Request

from app.deps import get_current_user, get_supabase, limiter

router = APIRouter(tags=["hotels"])


@router.get("/hotels/me", response_model=dict)
@limiter.limit("60/minute")
async def get_my_hotel(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_supabase),
):
    result = (
        db.table("hotels")
        .select("id, name, subscription_status, plan, image_retention_hours, created_at")
        .eq("id", current_user["hotel_id"])
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return {"success": True, "data": result.data, "error": None}
