from fastapi import APIRouter, HTTPException
from app.supabase_client import supabase

router = APIRouter(prefix="/categories", tags=["Categories"])


# ✅ LIST ALL CATEGORIES
@router.get("/")
def get_categories():
    res = supabase.table("categories").select("*").order("name").execute()
    return res.data or []


# ✅ CREATE CATEGORY
@router.post("/")
def create_category(data: dict):
    name = data.get("name")

    if not name:
        raise HTTPException(status_code=400, detail="Category name required")

    name = name.strip().title()

    existing = supabase.table("categories").select("*").eq("name", name).execute()

    if existing.data:
        return {"message": "Category already exists"}

    res = supabase.table("categories").insert({
        "name": name
    }).execute()

    return res.data[0]


# ✅ UPDATE CATEGORY
@router.put("/{category_id}")
def update_category(category_id: str, data: dict):
    name = data.get("name")

    if not name:
        raise HTTPException(status_code=400, detail="Name required")

    res = supabase.table("categories") \
        .update({"name": name.strip().title()}) \
        .eq("id", category_id) \
        .execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="Category not found")

    return {"message": "Category updated"}


# ❗ SAFE DELETE (IMPORTANT UPGRADE)
@router.delete("/{category_id}")
def delete_category(category_id: str):

    # 🔍 check if used in products
    products = supabase.table("products") \
        .select("id") \
        .eq("category_id", category_id) \
        .limit(1) \
        .execute()

    if products.data:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete category in use by products"
        )

    res = supabase.table("categories").delete().eq("id", category_id).execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="Category not found")

    return {"message": "Category deleted"}