from fastapi import APIRouter, Depends
from datetime import date, timedelta
from app.supabase_client import supabase
from app.auth.dependencies import get_current_admin

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/")
def get_dashboard(user: dict = Depends(get_current_admin)):
    today = date.today()
    next_7_days = today + timedelta(days=7)

    # 1. Get all products
    products_response = supabase.table("products").select("*").execute()
    products = products_response.data or []

    # 2. Get all sales
    sales_response = supabase.table("sales").select("*").execute()
    sales = sales_response.data or []

    # 📊 Metrics
    total_products = len(products)

    low_stock = [p for p in products if p["quantity"] <= 5]

    expired = [
        p for p in products
        if p.get("expiry_date") and p["expiry_date"] < str(today)
    ]

    expiring_soon = [
        p for p in products
        if p.get("expiry_date") and str(today) <= p["expiry_date"] <= str(next_7_days)
    ]

    total_sales = len(sales)

    total_quantity_sold = sum(s["quantity"] for s in sales)

    return {
        "total_products": total_products,
        "low_stock_count": len(low_stock),
        "expired_count": len(expired),
        "expiring_soon_count": len(expiring_soon),
        "total_sales": total_sales,
        "total_quantity_sold": total_quantity_sold,

        # Optional detailed lists
        "low_stock_products": low_stock,
        "expired_products": expired,
        "expiring_soon_products": expiring_soon
    }