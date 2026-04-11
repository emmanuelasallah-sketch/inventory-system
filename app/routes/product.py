from fastapi import APIRouter, HTTPException
from app.supabase_client import supabase
from datetime import datetime, timedelta

router = APIRouter(prefix="/products", tags=["Products"])


# ✅ CREATE PRODUCT
@router.post("/")
def create_product(product: dict):
    response = supabase.table("products").insert({
        "name": product["name"],
        "price": product["price"],
        "quantity": product.get("quantity", 0),
        "expiry_date": product.get("expiry_date"),
        "min_stock": product.get("min_stock", 5)
    }).execute()

    return response.data


# ✅ GET PRODUCTS + LOW STOCK FLAG
@router.get("/")
def get_products():
    response = supabase.table("products").select("*").execute()
    products = response.data

    for p in products:
        p["low_stock"] = p["quantity"] <= p["min_stock"]

    return products

@router.delete("/{product_id}")
def delete_product(product_id: str):
    res = supabase.table("products").delete().eq("id", product_id).execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"message": "Product deleted"}


# ✅ STOCK IN / STOCK OUT
@router.post("/stock")
def update_stock(data: dict):
    product_id = data["product_id"]
    change = data["change"]

    response = supabase.table("products").select("*").eq("id", product_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Product not found")

    product = response.data[0]
    new_quantity = product["quantity"] + change

    if new_quantity < 0:
        raise HTTPException(status_code=400, detail="Not enough stock")

    supabase.table("products").update({
        "quantity": new_quantity
    }).eq("id", product_id).execute()

    return {"message": "Stock updated", "new_quantity": new_quantity}


# ✅ ALERT SYSTEM (LOW STOCK + EXPIRY)
@router.get("/alerts")
def get_alerts():
    response = supabase.table("products").select("*").execute()
    products = response.data

    alerts = []

    for p in products:
        # LOW STOCK
        if p["quantity"] <= p["min_stock"]:
            alerts.append({
                "type": "low_stock",
                "product": p["name"]
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