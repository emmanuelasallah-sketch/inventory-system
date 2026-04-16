from fastapi import APIRouter, HTTPException
from app.supabase_client import supabase
from datetime import datetime, timedelta

router = APIRouter(prefix="/products", tags=["Products"])


# 🔧 HELPER
def normalize(value: str):
    return value.strip().title() if value else None


# ✅ CREATE OR UPDATE PRODUCT
@router.post("/")
def create_product(product: dict):
    try:
        name = normalize(product.get("name"))
        size = normalize(product.get("size"))
        stock = int(product.get("stock") or 0)
        price = float(product.get("price") or 0)
        category_id = product.get("category_id")

        if not name or not size:
            raise HTTPException(400, "Name and size required")

        existing = supabase.table("products") \
            .select("*") \
            .eq("name", name) \
            .eq("size", size) \
            .execute()

        # UPDATE
        if existing.data:
            p = existing.data[0]
            new_stock = p["stock"] + stock

            supabase.table("products").update({
                "stock": new_stock,
                "price": price if price > 0 else p["price"],
                "category_id": category_id or p["category_id"],
                "updated_at": datetime.now().isoformat()
            }).eq("id", p["id"]).execute()

            # STOCK HISTORY
            if stock > 0:
                supabase.table("stock_history").insert({
                    "product_id": p["id"],
                    "name": name,
                    "quantity_added": stock
                }).execute()

            return {"message": "Stock updated", "new_stock": new_stock}

        # CREATE
        res = supabase.table("products").insert({
            "name": name,
            "size": size,
            "price": price,
            "stock": stock,
            "category_id": category_id,
            "expiry_date": product.get("expiry_date"),
            "min_stock": product.get("min_stock", 5)
        }).execute()

        created = res.data[0]

        # STOCK HISTORY
        if stock > 0:
            supabase.table("stock_history").insert({
                "product_id": created["id"],
                "name": name,
                "quantity_added": stock
            }).execute()

        return created

    except Exception as e:
        raise HTTPException(500, str(e))


# ✅ GET PRODUCTS (WITH CATEGORY JOIN)
@router.get("/")
def get_products(category_id: str = None):
    try:
        query = supabase.table("products").select("*, categories(name)")

        if category_id:
            query = query.eq("category_id", category_id)

        res = query.execute()
        products = res.data or []

        for p in products:
            stock = p.get("stock", 0)
            price = p.get("price", 0)
            min_stock = p.get("min_stock", 0)

            p["low_stock"] = stock <= min_stock
            p["total_value"] = stock * price
            p["category_name"] = p.get("categories", {}).get("name")

        return products

    except Exception as e:
        raise HTTPException(500, str(e))


# ✅ EDIT PRODUCT
@router.put("/{product_id}")
def edit_product(product_id: str, data: dict):
    try:
        existing = supabase.table("products").select("*").eq("id", product_id).execute()

        if not existing.data:
            raise HTTPException(404, "Product not found")

        p = existing.data[0]

        update_data = {
            "name": normalize(data.get("name")) or p["name"],
            "size": normalize(data.get("size")) or p["size"],
            "price": float(data.get("price") or p["price"]),
            "stock": int(data.get("stock") or p["stock"]),
            "category_id": data.get("category_id") or p.get("category_id"),
            "expiry_date": data.get("expiry_date") or p.get("expiry_date"),
            "min_stock": data.get("min_stock") or p.get("min_stock"),
            "updated_at": datetime.now().isoformat()
        }

        supabase.table("products").update(update_data).eq("id", product_id).execute()

        return {"message": "Product updated"}

    except Exception as e:
        raise HTTPException(500, str(e))


# ✅ DELETE
@router.delete("/{product_id}")
def delete_product(product_id: str):
    res = supabase.table("products").delete().eq("id", product_id).execute()

    if not res.data:
        raise HTTPException(404, "Not found")

    return {"message": "Deleted"}


# ✅ STOCK UPDATE
@router.post("/stock")
def update_stock(data: dict):
    product_id = data.get("product_id")
    change = int(data.get("change") or 0)

    res = supabase.table("products").select("*").eq("id", product_id).execute()

    if not res.data:
        raise HTTPException(404, "Not found")

    p = res.data[0]
    new_stock = p["stock"] + change

    if new_stock < 0:
        raise HTTPException(400, "Not enough stock")

    supabase.table("products").update({
        "stock": new_stock
    }).eq("id", product_id).execute()

    if change < 0:
        supabase.table("sales_history").insert({
            "product_id": product_id,
            "name": p["name"],
            "quantity_sold": abs(change)
        }).execute()

    return {"message": "Stock updated"}


# ✅ ALERTS
@router.get("/alerts")
def alerts():
    res = supabase.table("products").select("*").execute()
    products = res.data or []

    alerts = []

    for p in products:
        if p["stock"] <= p.get("min_stock", 0):
            alerts.append({
                "type": "low_stock",
                "product": p["name"]
            })

    return alerts