import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "finance.db")
REQUEST_DELAY_SECONDS = float(os.getenv("REQUEST_DELAY_SECONDS", "2"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))
CORS_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
]