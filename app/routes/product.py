from fastapi import APIRouter, HTTPException
from app.supabase_client import supabase
from datetime import datetime, timedelta

router = APIRouter(prefix="/products", tags=["Products"])


# ✅ CREATE PRODUCT
@router.post("/")
def create_product(product: dict):
    response = supabase.table("products").insert({
                    "name": product["name"],
                    "size": product.get("size"),
                    "price": float(product.get("price", 0)),
                    "stock": int(product.get("stock", 0)),
                    "expiry_date": product.get("expiry_date"),
                    "min_stock": product.get("min_stock", 5),
                    "category": product.get("category"),
                }).execute()
    return response.data


# ✅ GET PRODUCTS (FULL DATA + FLAGS)
@router.get("/")
def get_products(search: str = None):
    query = supabase.table("products").select("*")

    # ✅ Only filter if search exists
    if search and search.strip() != "":
        query = query.ilike("name", f"%{search}%")

    response = query.execute()
    products = response.data

    for p in products:
        stock = p.get("stock", 0)
        min_stock = p.get("min_stock", 0)

        p["low_stock"] = stock <= min_stock

    return products

# ✅ DELETE PRODUCT
@router.delete("/{product_id}")
def delete_product(product_id: str):
    res = supabase.table("products").delete().eq("id", product_id).execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"message": "Product deleted"}


# ✅ STOCK UPDATE
@router.post("/stock")
def update_stock(data: dict):
    product_id = data["product_id"]
    change = data["change"]

    response = supabase.table("products").select("*").eq("id", product_id).execute()

    if not response.data:
        raise HTTPException(status_code=404, detail="Product not found")

    product = response.data[0]

    new_stock = product.get("stock", 0) + change

    if new_stock < 0:
        raise HTTPException(status_code=400, detail="Not enough stock")

    supabase.table("products").update({
        "stock": new_stock
    }).eq("id", product_id).execute()

    return {
        "message": "Stock updated",
        "new_stock": new_stock
    }


# ✅ SELL PRODUCT
@router.post("/sell")
def sell_product(data: dict):
    name = data["name"]
    size = data["size"]
    quantity = data["quantity"]

    response = supabase.table("products") \
        .select("*") \
        .eq("name", name) \
        .eq("size", size) \
        .execute()

    if not response.data:
        raise HTTPException(status_code=404, detail="Product not found")

    product = response.data[0]

    if product["stock"] < quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")

    new_stock = product["stock"] - quantity

    # update stock
    supabase.table("products").update({
        "stock": new_stock
    }).eq("id", product["id"]).execute()

    # record sale
    supabase.table("products").insert({
        "name": product["name"],
        "size": product["size"],
        "price": product["price"],
        "stock": product.get("stock", 0),
        "expiry_date": product.get("expiry_date"),
        "min_stock": product.get("min_stock", 5)
    }).execute()

    return {
        "message": "Sale recorded",
        "remaining_stock": new_stock
    }


# ✅ ALERTS (FOR FUTURE MESSAGE PAGE)
@router.get("/alerts")
def get_alerts():
    response = supabase.table("products").select("*").execute()
    products = response.data

    alerts = []

    for p in products:
        stock = p.get("stock", 0)
        min_stock = p.get("min_stock", 0)

        # LOW STOCK
        if stock <= min_stock:
            alerts.append({
                "type": "low_stock",
                "product": p["name"],
                "size": p.get("size") or None,
                "stock": stock
            })

        # EXPIRY
        if p.get("expiry_date"):
            expiry = datetime.fromisoformat(p["expiry_date"])

            if expiry < datetime.now():
                alerts.append({
                    "type": "expired",
                    "product": p["name"]
                })

            elif expiry < datetime.now() + timedelta(days=7):
                alerts.append({
                    "type": "expiring_soon",
                    "product": p["name"]
                })

    return alerts