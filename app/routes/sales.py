from fastapi import APIRouter
from app.supabase_client import supabase


router = APIRouter(prefix="/sales", tags=["Sales"])


@router.get("/")
def get_sales():
    res = supabase.table("sales").select("*").execute()
    return res.data



@router.post("/checkout")
def checkout(data: dict):
    items = data.get("items", [])

    if not items:
        return {"error": "Cart is empty"}

    total_amount = 0
    processed_items = []

    # STEP 1: Validate all items first
    for item in items:
        product_res = (
            supabase.table("products")
            .select("*")
            .ilike("name", f"%{item['product_name']}%")
            .eq("size", item["size"])
            .limit(1)
            .execute()
        )

        if not product_res.data:
            return {"error": f"{item['product_name']} not found"}

        product = product_res.data[0]

        if product["quantity"] < item["quantity"]:
            return {"error": f"Not enough stock for {product['name']}"}

        processed_items.append({
            "product": product,
            "quantity": item["quantity"]
        })

    # STEP 2: Create Order
    order_res = supabase.table("orders").insert({
        "total_amount": 0
    }).execute()

    order_id = order_res.data[0]["id"]

    # STEP 3: Process each item
    for item in processed_items:
        product = item["product"]
        qty = item["quantity"]

        new_qty = product["quantity"] - qty

        # update stock
        supabase.table("products").update({
            "quantity": new_qty
        }).eq("id", product["id"]).execute()

        # insert order item
        supabase.table("order_items").insert({
            "order_id": order_id,
            "product_id": product["id"],
            "quantity": qty,
            "price": product["price"]
        }).execute()

        total_amount += product["price"] * qty

    # STEP 4: update total
    supabase.table("orders").update({
        "total_amount": total_amount
    }).eq("id", order_id).execute()

    return {
        "message": "Order completed",
        "order_id": order_id,
        "total": total_amount
    }