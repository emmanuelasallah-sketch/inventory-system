from pydantic import BaseModel
from datetime import date

class PromotionCreate(BaseModel):
    product_id: int
    discount_percent: float
    start_date: date
    end_date: date