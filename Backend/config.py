import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database Configuration
    DB_HOST = os.getenv("DB_HOST")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME")
    DB_DATABASE = os.getenv("DB_DATABASE", os.getenv("DB_NAME"))  # Fallback to DB_NAME
    USE_PURE = os.getenv("USE_PURE", "True").lower() == "true"
    
    # Flask Configuration
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
    
    # AI API Keys
    GOOGLE_GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    COHERE_API_KEY = os.getenv("COHERE_API_KEY")
    
    # Database Configuration Dictionary
    DB_CONFIG = {
        "host": DB_HOST,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "database": DB_DATABASE,
        "use_pure": USE_PURE
    }
    
    @classmethod
    def validate_config(cls):
        """Validate that all required environment variables are set"""
        required_vars = [
            'DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME', 
            'GOOGLE_GEMINI_API_KEY'
        ]
        missing_vars = []
        
        for var in required_vars:
            value = getattr(cls, var, None)
            if not value or (isinstance(value, str) and not value.strip()):
                missing_vars.append(var)
        
        # Check Flask secret key separately since it might have a fallback
        if not cls.SECRET_KEY or (isinstance(cls.SECRET_KEY, str) and cls.SECRET_KEY.strip() == ""):
            print("Warning: FLASK_SECRET_KEY not set, using random key (not recommended for production)")
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True