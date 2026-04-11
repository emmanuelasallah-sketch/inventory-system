from fastapi import APIRouter
from app.schemas.user import UserCreate, UserLogin
from app.auth.utils import hash_password, verify_password
from app.auth.auth import create_access_token
from app.supabase_client import supabase
from fastapi import HTTPException

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
def register(user: UserCreate):
    existing = (
        supabase.table("users")
        .select("*")
        .eq("email", user.email)
        .execute()
    )

    if existing.data:
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = {
        "email": user.email,
        "password_hash": hash_password(user.password),
        "role": "admin"
    }

    response = supabase.table("users").insert(new_user).execute()

    print("REGISTER RESPONSE:", response)  # 👈 ADD THIS

    if not response.data:
        raise HTTPException(status_code=400, detail="User creation failed")

    return {"message": "User created successfully"}



@router.post("/login")
def login(user: UserLogin):
    try:
        response = (
            supabase.table("users")
            .select("*")
            .eq("email", user.email)
            .execute()
        )

        data = response.data

        if not data:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        db_user = data[0]

        if not verify_password(user.password, db_user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token({
            "sub": db_user["email"],
            "role": db_user["role"]
        })

        return {
            "access_token": token,
            "token_type": "bearer"
        }

    except HTTPException as e:
        raise e  # ✅ keep 401 as 401

    except Exception as e:
        print("LOGIN ERROR:", e)
        raise HTTPException(status_code=500, detail="Server error")