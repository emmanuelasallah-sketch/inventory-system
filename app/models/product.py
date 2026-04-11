from sqlalchemy import Column, String, Integer, Date, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String)
    barcode = Column(String, unique=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))
    price = Column(Numeric)
    quantity = Column(Integer, default=0)
    expiry_date = Column(Date)