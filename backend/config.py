import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # External API Configuration
    HOSPITAL_API_BASE_URL = os.getenv("HOSPITAL_API_BASE_URL", "https://hospital-directory.onrender.com")
    
    # CSV Processing Settings
    MAX_CSV_SIZE = int(os.getenv("MAX_CSV_SIZE", "20"))
    CSV_REQUIRED_COLUMNS = ["name", "address"]
    CSV_OPTIONAL_COLUMNS = ["phone"]
    
    # Performance optimization settings
    MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
    HTTP_TIMEOUT_SECONDS = int(os.getenv("HTTP_TIMEOUT_SECONDS", "30"))
    HTTP_CONNECT_TIMEOUT_SECONDS = int(os.getenv("HTTP_CONNECT_TIMEOUT_SECONDS", "10"))
    
    # Application Settings
    APP_NAME = os.getenv("APP_NAME", "Hospital Bulk Processing API")
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
    
    # Progress Tracking Settings
    PROGRESS_CLEANUP_HOURS = int(os.getenv("PROGRESS_CLEANUP_HOURS", "24"))
    
settings = Settings()