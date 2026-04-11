from dotenv import load_dotenv
import os
from supabase import create_client

# 🔥 FORCE correct path
load_dotenv(dotenv_path="C:/Users/USER/PycharmProjects/cosmetic_backend/.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("URL:", SUPABASE_URL)  # debug

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)