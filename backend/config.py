import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    HOSPITAL_API_BASE_URL = "https://hospital-directory.onrender.com"
    MAX_CSV_SIZE = 20
    CSV_REQUIRED_COLUMNS = ["name", "address"]
    CSV_OPTIONAL_COLUMNS = ["phone"]
    
    # Performance optimization settings
    MAX_CONCURRENT_REQUESTS = 10
    HTTP_TIMEOUT_SECONDS = 30
    HTTP_CONNECT_TIMEOUT_SECONDS = 10
    
settings = Settings()