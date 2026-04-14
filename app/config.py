import os
from dotenv import load_dotenv


load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://hospital-directory.onrender.com")
MAX_CSV_HOSPITALS = 20
MAX_CONCURRENT_REQUESTS = 20
