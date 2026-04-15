from fastapi import APIRouter, HTTPException
from app.supabase_client import supabase
from datetime import datetime, timedelta

router = APIRouter(prefix="/products", tags=["Products"])


# ✅ CREATE OR UPDATE PRODUCT
@router.post("/")
def create_product(product: dict):
    name = product.get("name")
    size = product.get("size")
    stock = int(product.get("stock", 0))
    price = float(product.get("price", 0))

    if not name or not size:
        raise HTTPException(status_code=400, detail="Name and size are required")

    # 🔍 Check if product exists (same name + size)
    existing = supabase.table("products") \
        .select("*") \
        .eq("name", name) \
        .eq("size", size) \
        .execute()

    if existing.data:
        # ✅ UPDATE STOCK
        existing_product = existing.data[0]
        new_stock = existing_product["stock"] + stock

        supabase.table("products").update({
            "stock": new_stock,
            "price": price or existing_product["price"]  # keep or update price
        }).eq("id", existing_product["id"]).execute()

        # ✅ RECORD STOCK HISTORY
        supabase.table("stock_history").insert({
            "product_id": existing_product["id"],
            "name": name,
            "quantity_added": stock
        }).execute()

        return {"message": "Stock updated", "new_stock": new_stock}

    # 🆕 CREATE NEW PRODUCT
    new_product = supabase.table("products").insert({
        "name": name,
        "size": size,
        "price": price,
        "stock": stock,
        "category": product.get("category"),
        "expiry_date": product.get("expiry_date"),
        "min_stock": product.get("min_stock", 5)
    }).execute()

    created = new_product.data[0]

    # ✅ RECORD STOCK HISTORY
    supabase.table("stock_history").insert({
        "product_id": created["id"],
        "name": name,
        "quantity_added": stock
    }).execute()

    return created


# ✅ GET PRODUCTS
@router.get("/")
def get_products():
    response = supabase.table("products").select("*").execute()
    products = response.data

    for p in products:
        stock = p.get("stock", 0)
        min_stock = p.get("min_stock", 0)

        p["low_stock"] = stock <= min_stock
        p["total_value"] = stock * p.get("price", 0)  # ✅ PRICE × STOCK

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
    product_id = data.get("product_id")
    change = int(data.get("change", 0))

    response = supabase.table("products").select("*").eq("id", product_id).execute()

    if not response.data:
        raise HTTPException(status_code=404, detail="Product not found")

    product = response.data[0]
    new_stock = product["stock"] + change

    if new_stock < 0:
        raise HTTPException(status_code=400, detail="Not enough stock")

    supabase.table("products").update({
        "stock": new_stock
    }).eq("id", product_id).execute()

    # ✅ RECORD SALES HISTORY (ONLY WHEN SELLING)
    if change < 0:
        supabase.table("sales_history").insert({
            "product_id": product_id,
            "name": product["name"],
            "quantity_sold": abs(change)
        }).execute()

    return {"message": "Stock updated", "new_stock": new_stock}


# ✅ SELL PRODUCT (FIXED)
@router.post("/sell")
def sell_product(data: dict):
    name = data.get("name")
    size = data.get("size")
    quantity = int(data.get("quantity", 0))

    if not name or not size or quantity <= 0:
        raise HTTPException(status_code=400, detail="Invalid input")

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

    # ✅ UPDATE STOCK
    supabase.table("products").update({
        "stock": new_stock
    }).eq("id", product["id"]).execute()

    # ✅ FIXED: RECORD SALE PROPERLY
    supabase.table("sales_history").insert({
        "product_id": product["id"],
        "name": product["name"],
        "quantity_sold": quantity
    }).execute()

    return {
        "message": "Sale recorded",
        "remaining_stock": new_stock
    }


# ✅ ALERTS
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
                "size": p.get("size"),
                "stock": stock
            })

        # EXPIRY
        if p.get("expiry_date"):
            expiry = datetime.fromisoformat(p["expiry_date"])

            if expiry < datetime.now():
                alerts.append({"type": "expired", "product": p["name"]})

            elif expiry < datetime.now() + timedelta(days=7):
                alerts.append({"type": "expiring_soon", "product": p["name"]})

    return alerts


# ✅ STOCK HISTORY
@router.get("/stock_history")
def get_stock_history():
    res = supabase.table("stock_history") \
        .select("*") \
        .order("created_at", desc=True) \
        .execute()
    return res.data


# ✅ SALES HISTORY
@router.get("/sales_history")
def get_sales_history():
    res = supabase.table("sales_history") \
        .select("*") \
        .order("created_at", desc=True) \
        .execute()
    return res.data