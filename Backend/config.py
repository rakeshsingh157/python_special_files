import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DB_HOST = os.getenv("DB_HOST", "photostore.ct0go6um6tj0.ap-south-1.rds.amazonaws.com")
    DB_USER = os.getenv("DB_USER", "admin")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "DBpicshot")
    DB_NAME = os.getenv("DB_NAME", "eventsreminder")
    USE_PURE = os.getenv("USE_PURE", "True").lower() == "true"