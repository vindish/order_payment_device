import os
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "dev")
SECRET_KEY = os.getenv("SECRET_KEY")
DB_URL = os.getenv("DB_URL")