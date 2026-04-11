from pydantic import BaseModel
from typing import Optional
from datetime import date
from uuid import UUID

class ProductCreate(BaseModel):
    name: str
    description: Optional[str]
    barcode: Optional[str]
    category_id: Optional[UUID]
    price: float
    quantity: int
    expiry_date: Optional[date]

class ProductResponse(ProductCreate):
    id: int

    class Config:
        from_attributes = True