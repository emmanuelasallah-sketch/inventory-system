from fastapi import APIRouter, HTTPException, Depends
from datetime import date
from app.schemas.promotion import PromotionCreate
from app.supabase_client import supabase
from app.auth.dependencies import get_current_admin

router = APIRouter(prefix="/promotions", tags=["Promotions"])


# ✅ CREATE PROMOTION (Admin only)
@router.post("/")
def create_promotion(promo: PromotionCreate, user: dict = Depends(get_current_admin)):
    # Check product exists
    product = (
        supabase.table("products")
        .select("*")
        .eq("id", promo.product_id)
        .single()
        .execute()
    ).data

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Validate dates
    if promo.start_date > promo.end_date:
        raise HTTPException(status_code=400, detail="Invalid date range")

    response = supabase.table("promotions").insert(promo.dict()).execute()

    return {"message": "Promotion created", "data": response.data}


# ✅ GET ACTIVE PROMOTIONS
@router.get("/active")
def get_active_promotions():
    today = str(date.today())

    response = supabase.table("promotions").select("*").execute()

    active = [
        p for p in response.data
        if p["start_date"] <= today <= p["end_date"]
    ]

    return active


# ✅ GET PROMOTIONS FOR A PRODUCT
@router.get("/product/{product_id}")
def get_product_promotions(product_id: int):
    response = (
        supabase.table("promotions")
        .select("*")
        .eq("product_id", product_id)
        .execute()
    )

    return response.data


# ✅ DELETE PROMOTION
@router.delete("/{promo_id}")
def delete_promotion(promo_id: int, user: dict = Depends(get_current_admin)):
    supabase.table("promotions").delete().eq("id", promo_id).execute()
    return {"message": "Promotion deleted"}