from fastapi import APIRouter, HTTPException
from app.supabase_client import supabase

router = APIRouter(prefix="/sales", tags=["Sales"])


# =========================
# 📥 GET SALES
# =========================
@router.get("/")
def get_sales():
    res = supabase.table("sales").select("*").order("created_at", desc=True).execute()
    return res.data or []


# =========================
# 🛒 CHECKOUT (CART SYSTEM)
# =========================
@router.post("/checkout")
def checkout(data: dict):
    try:
        items = data.get("items", [])

        if not items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        total_amount = 0
        validated_items = []

        # =========================
        # STEP 1: VALIDATE ALL ITEMS
        # =========================
        for item in items:
            name = item.get("product_name")
            size = item.get("size")
            qty = int(item.get("quantity") or 0)

            if not name or not size or qty <= 0:
                raise HTTPException(status_code=400, detail="Invalid cart item")

            product_res = supabase.table("products") \
                .select("*") \
                .eq("name", name.strip().title()) \
                .eq("size", size.strip().title()) \
                .limit(1) \
                .execute()

            if not product_res.data:
                raise HTTPException(status_code=404, detail=f"{name} not found")

            product = product_res.data[0]

            if product.get("stock", 0) < qty:
                raise HTTPException(
                    status_code=400,
                    detail=f"Not enough stock for {product['name']}"
                )

            validated_items.append({
                "product": product,
                "quantity": qty
            })

        # =========================
        # STEP 2: CREATE ORDER
        # =========================
        order_res = supabase.table("orders").insert({
            "total_amount": 0
        }).execute()

        if not order_res.data:
            raise HTTPException(status_code=500, detail="Failed to create order")

        order_id = order_res.data[0]["id"]

        # =========================
        # STEP 3: PROCESS ITEMS
        # =========================
        for item in validated_items:
            product = item["product"]
            qty = item["quantity"]

            new_stock = product["stock"] - qty

            # update stock
            supabase.table("products").update({
                "stock": new_stock
            }).eq("id", product["id"]).execute()

            # insert order item
            supabase.table("order_items").insert({
                "order_id": order_id,
                "product_id": product["id"],
                "quantity": qty,
                "price": product["price"]
            }).execute()

            total_amount += float(product["price"]) * qty

            # optional: sales history
            supabase.table("sales_history").insert({
                "product_id": product["id"],
                "name": product["name"],
                "quantity_sold": qty
            }).execute()

        # =========================
        # STEP 4: UPDATE ORDER TOTAL
        # =========================
        supabase.table("orders") \
            .update({"total_amount": total_amount}) \
            .eq("id", order_id) \
            .execute()

        return {
            "message": "Order completed",
            "order_id": order_id,
            "total": total_amount
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))