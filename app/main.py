from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.product import router as product_router
from app.routes.auth import router as auth_router
from app.routes import sales
from app.routes import dashboard
from app.routes import promotions
from app.routes import categories

print("🔥 MAIN FILE LOADED")

app = FastAPI()

# ✅ ADD CORS FIRST
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ THEN include routers
app.include_router(sales.router)
app.include_router(product_router)
app.include_router(auth_router)
app.include_router(dashboard.router)
app.include_router(promotions.router)
app.include_router(categories.router)
app.include_router(sales.router)


@app.get("/")
def home():
    return {"message": "API running 🚀"}