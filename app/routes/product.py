from fastapi import APIRouter, HTTPException
from app.supabase_client import supabase
from datetime import datetime, timedelta

router = APIRouter(prefix="/products", tags=["Products"])


# 🔧 HELPER
def normalize_text(value: str):
    return value.strip().title() if value else None


# ✅ CREATE OR UPDATE PRODUCT
@router.post("/")
def create_product(product: dict):
    try:
        name = normalize_text(product.get("name"))
        size = normalize_text(product.get("size"))
        stock = int(product.get("stock") or 0)
        price = float(product.get("price") or 0)
        category_id = product.get("category_id")

        if not name or not size:
            raise HTTPException(status_code=400, detail="Name and size are required")

        # 🔍 CHECK EXISTING
        existing = supabase.table("products") \
            .select("*") \
            .eq("name", name) \
            .eq("size", size) \
            .execute()

        # ✅ UPDATE
        if existing.data:
            existing_product = existing.data[0]
            new_stock = existing_product.get("stock", 0) + stock

            supabase.table("products").update({
                "stock": new_stock,
                "price": price if price > 0 else existing_product.get("price", 0),
                "category_id": category_id or existing_product.get("category_id")
            }).eq("id", existing_product["id"]).execute()

            # STOCK HISTORY
            if stock > 0:
                supabase.table("stock_history").insert({
                    "product_id": existing_product["id"],
                    "name": name,
                    "quantity_added": stock
                }).execute()

            return {"message": "Stock updated", "new_stock": new_stock}

        # 🆕 CREATE
        new_product = supabase.table("products").insert({
            "name": name,
            "size": size,
            "price": price,
            "stock": stock,
            "category_id": category_id,
            "expiry_date": product.get("expiry_date"),
            "min_stock": int(product.get("min_stock") or 5)
        }).execute()

        if not new_product.data:
            raise HTTPException(status_code=500, detail="Failed to create product")

        created = new_product.data[0]

        # STOCK HISTORY
        if stock > 0:
            supabase.table("stock_history").insert({
                "product_id": created["id"],
                "name": name,
                "quantity_added": stock
            }).execute()

        return created

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ GET PRODUCTS (WITH FILTER + CATEGORY NAME)
@router.get("/")
def get_products(category_id: str = None):
    try:
        query = supabase.table("products").select("*, categories(name)")

        # ✅ FILTER
        if category_id:
            query = query.eq("category_id", category_id)

        response = query.execute()
        products = response.data or []

        for p in products:
            stock = p.get("stock", 0)
            price = p.get("price", 0)
            min_stock = p.get("min_stock", 0)

            p["low_stock"] = stock <= min_stock
            p["total_value"] = stock * price
            p["category_name"] = p.get("categories", {}).get("name")

        return products

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ GET CATEGORIES
@router.get("/categories")
def get_categories():
    res = supabase.table("categories").select("*").execute()
    return res.data


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
    try:
        product_id = data.get("product_id")
        change = int(data.get("change") or 0)

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

        # SALES HISTORY
        if change < 0:
            supabase.table("sales_history").insert({
                "product_id": product_id,
                "name": product["name"],
                "quantity_sold": abs(change)
            }).execute()

        return {"message": "Stock updated", "new_stock": new_stock}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ SELL PRODUCT
@router.post("/sell")
def sell_product(data: dict):
    try:
        name = normalize_text(data.get("name"))
        size = normalize_text(data.get("size"))
        quantity = int(data.get("quantity") or 0)

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

        if product.get("stock", 0) < quantity:
            raise HTTPException(status_code=400, detail="Not enough stock")

        new_stock = product["stock"] - quantity

        supabase.table("products").update({
            "stock": new_stock
        }).eq("id", product["id"]).execute()

        supabase.table("sales_history").insert({
            "product_id": product["id"],
            "name": product["name"],
            "quantity_sold": quantity
        }).execute()

        return {
            "message": "Sale recorded",
            "remaining_stock": new_stock
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ ALERTS
@router.get("/alerts")
def get_alerts():
    response = supabase.table("products").select("*").execute()
    products = response.data or []

    alerts = []

    for p in products:
        stock = p.get("stock", 0)
        min_stock = p.get("min_stock", 0)

        if stock <= min_stock:
            alerts.append({
                "type": "low_stock",
                "product": p["name"],
                "size": p.get("size"),
                "stock": stock
            })

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