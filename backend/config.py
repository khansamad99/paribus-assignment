import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    HOSPITAL_API_BASE_URL = "https://hospital-directory.onrender.com"
    MAX_CSV_SIZE = 20
    CSV_REQUIRED_COLUMNS = ["name", "address"]
    CSV_OPTIONAL_COLUMNS = ["phone"]
    
settings = Settings()