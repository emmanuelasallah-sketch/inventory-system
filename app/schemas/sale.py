from pydantic import BaseModel

class SaleCreate(BaseModel):
    product_id: int
    quantity: int