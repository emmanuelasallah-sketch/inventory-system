from fastapi import APIRouter, HTTPException
from app.supabase_client import supabase
from datetime import datetime, timedelta

router = APIRouter(prefix="/products", tags=["Products"])


# 🔧 HELPER
def normalize_text(value: str | None):
    return value.strip().title() if value else None


# ✅ CREATE OR UPDATE PRODUCT
@router.post("/")
def create_product(product: dict):
    try:
        name = normalize_text(product.get("name"))
        size = normalize_text(product.get("size"))

        stock = int(product.get("stock") or 0)
        price = float(product.get("price") or 0)

        selling_price = product.get("selling_price")
        category_id = product.get("category_id") or None
        expiry_date = product.get("expiry_date") or None  # ✅ FIXED

        if selling_price:
            selling_price = float(selling_price)

        if not name or not size:
            raise HTTPException(status_code=400, detail="Name and size are required")

        # 🔍 CHECK EXISTING PRODUCT
        existing = supabase.table("products") \
            .select("*") \
            .eq("name", name) \
            .eq("size", size) \
            .execute()

        # ✅ UPDATE EXISTING
        if existing.data:
            existing_product = existing.data[0]
            new_stock = existing_product.get("stock", 0) + stock

            final_selling_price = (
                selling_price
                if selling_price is not None
                else existing_product.get("selling_price")
            )

            supabase.table("products").update({
                "stock": new_stock,
                "price": price if price > 0 else existing_product.get("price"),
                "selling_price": final_selling_price,
                "category_id": category_id or existing_product.get("category_id"),
                "expiry_date": expiry_date or existing_product.get("expiry_date")  # ✅ FIXED
            }).eq("id", existing_product["id"]).execute()

            return {"message": "Stock updated", "new_stock": new_stock}

        # 🆕 CREATE NEW PRODUCT
        new_product = supabase.table("products").insert({
            "name": name,
            "size": size,
            "price": price,
            "selling_price": selling_price,
            "stock": stock,
            "category_id": category_id,
            "expiry_date": expiry_date,  # ✅ FIXED
            "min_stock": int(product.get("min_stock") or 5)
        }).execute()

        return new_product.data[0]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ GET PRODUCTS
@router.get("/")
def get_products(category_id: str = None, search: str = None):
    try:
        query_builder = supabase.table("products").select("*")

        if category_id:
            query_builder = query_builder.eq("category_id", category_id)

        if search:
            query_builder = query_builder.ilike("name", f"%{search}%")

        res = query_builder.execute()
        products = res.data or []

        for p in products:
            stock = p.get("stock", 0)
            price = p.get("price", 0)
            min_stock = p.get("min_stock", 0)

            p["low_stock"] = stock <= min_stock
            p["total_value"] = stock * price

        return products

    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(500, str(e))

# ✅ EDIT PRODUCT
@router.put("/{product_id}")
def edit_product(product_id: str, data: dict):
    try:
        existing = supabase.table("products").select("*").eq("id", product_id).execute()

        if not existing.data:
            raise HTTPException(status_code=404, detail="Product not found")

        p = existing.data[0]

        # ✅ HANDLE SELLING PRICE CLEANLY
        new_selling_price = data.get("selling_price")
        if new_selling_price == "" or new_selling_price is None:
            final_selling_price = p.get("selling_price")
        else:
            final_selling_price = float(new_selling_price)

        # ✅ HANDLE EXPIRY CLEANLY
        new_expiry = data.get("expiry_date")
        if new_expiry == "":
            final_expiry = None  # user cleared it
        elif new_expiry is None:
            final_expiry = p.get("expiry_date")  # keep old
        else:
            final_expiry = new_expiry

        update_data = {
            "name": normalize_text(data.get("name")) or p["name"],
            "size": normalize_text(data.get("size")) or p["size"],
            "price": float(data.get("price") or p["price"]),
            "selling_price": final_selling_price,  # ✅ ADDED
            "stock": int(data.get("stock") or p["stock"]),
            "category_id": data.get("category_id") or p.get("category_id"),
            "expiry_date": final_expiry,  # ✅ FIXED
            "min_stock": data.get("min_stock") or p.get("min_stock"),
            "updated_at": datetime.now().isoformat()
        }

        supabase.table("products").update(update_data).eq("id", product_id).execute()

        return {"message": "Product updated"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ DELETE
@router.delete("/{product_id}")
def delete_product(product_id: str):
    res = supabase.table("products").delete().eq("id", product_id).execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="Not found")

    return {"message": "Deleted"}


# ✅ STOCK UPDATE
@router.post("/stock")
def update_stock(data: dict):
    product_id = data.get("product_id")
    change = int(data.get("change") or 0)

    res = supabase.table("products").select("*").eq("id", product_id).execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="Not found")

    p = res.data[0]
    new_stock = p["stock"] + change

    if new_stock < 0:
        raise HTTPException(status_code=400, detail="Not enough stock")

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