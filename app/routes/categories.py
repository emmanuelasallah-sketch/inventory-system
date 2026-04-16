from fastapi import APIRouter, HTTPException
from app.supabase_client import supabase

router = APIRouter(prefix="/categories", tags=["Categories"])


# =========================
# 🔧 HELPER
# =========================
def normalize(name: str):
    if not name:
        return None
    return name.strip().title()


# =========================
# 📥 GET ALL CATEGORIES
# =========================
@router.get("/")
def get_categories():
    try:
        res = supabase.table("categories") \
            .select("*") \
            .order("name") \
            .execute()

        return res.data or []

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# ➕ CREATE CATEGORY
# =========================
@router.post("/")
def create_category(data: dict):
    try:
        name = normalize(data.get("name"))

        if not name:
            raise HTTPException(status_code=400, detail="Category name is required")

        # 🔍 case-insensitive check
        existing = supabase.table("categories") \
            .select("*") \
            .ilike("name", name) \
            .execute()

        if existing.data:
            return {
                "message": "Category already exists",
                "data": existing.data[0]
            }

        res = supabase.table("categories").insert({
            "name": name
        }).execute()

        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to create category")

        return {
            "message": "Category created",
            "data": res.data[0]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# ✏️ UPDATE CATEGORY
# =========================
@router.put("/{category_id}")
def update_category(category_id: str, data: dict):
    try:
        name = normalize(data.get("name"))

        if not name:
            raise HTTPException(status_code=400, detail="Name is required")

        # prevent duplicates
        duplicate = supabase.table("categories") \
            .select("*") \
            .ilike("name", name) \
            .neq("id", category_id) \
            .execute()

        if duplicate.data:
            raise HTTPException(status_code=400, detail="Category already exists")

        res = supabase.table("categories") \
            .update({"name": name}) \
            .eq("id", category_id) \
            .execute()

        if not res.data:
            raise HTTPException(status_code=404, detail="Category not found")

        return {
            "message": "Category updated",
            "data": res.data[0]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# 🗑 DELETE CATEGORY (SAFE)
# =========================
@router.delete("/{category_id}")
def delete_category(category_id: str):
    try:
        # check if category is in use
        used = supabase.table("products") \
            .select("id") \
            .eq("category_id", category_id) \
            .limit(1) \
            .execute()

        if used.data:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete category: it is used by products"
            )

        res = supabase.table("categories") \
            .delete() \
            .eq("id", category_id) \
            .execute()

        if not res.data:
            raise HTTPException(status_code=404, detail="Category not found")

        return {"message": "Category deleted"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))