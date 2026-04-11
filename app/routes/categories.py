from fastapi import APIRouter
from app.supabase_client import supabase

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/")
def get_categories():
    res = supabase.table("categories").select("*").execute()
    return res.data


@router.post("/")
def add_category(data: dict):
    res = supabase.table("categories").insert(data).execute()
    return res.data


@router.delete("/{category_id}")
def delete_category(category_id: str):
    supabase.table("categories").delete().eq("id", category_id).execute()
    return {"message": "Deleted"}