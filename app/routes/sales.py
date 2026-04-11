from fastapi import APIRouter
from app.supabase_client import supabase


router = APIRouter(prefix="/sales", tags=["Sales"])


@router.get("/")
def get_sales():
    res = supabase.table("sales").select("*").execute()
    return res.data



@router.post("/")
def create_sale(data: dict):

    product_res = (
        supabase.table("products")
        .select("*")
        .ilike("name", f"%{data['product_name']}%")
        .eq("size", data["size"])
        .limit(1)
        .execute()
    )

    if not product_res.data:
        return {"error": "Product not found"}

    product = product_res.data[0]

    new_qty = product["quantity"] - data["quantity"]

    if new_qty < 0:
        return {"error": "Not enough stock"}

    supabase.table("products").update({
        "quantity": new_qty
    }).eq("id", product["id"]).execute()

    supabase.table("sales").insert({
        "product_id": product["id"],
        "quantity": data["quantity"]
    }).execute()

    return {"message": "Sale recorded"}