from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "../config.env"))

def get_connection():
    try:
        client = MongoClient(os.getenv("MONGO_URI"))

        db = client[os.getenv("DB_NAME")]

        print("MongoDB connected successfully")

        return db

    except Exception as e:
        print(f"MongoDB connection error: {e}")
        return None