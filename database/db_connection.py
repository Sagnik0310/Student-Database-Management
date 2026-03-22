import mysql.connector as mc
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config.env")

def get_connection():
    try:
        db = mc.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )

        print("Database connected successfully")
        return db

    except mc.Error as e:
        print(f"MySQL connection error: {e}")
        return None

    except Exception as e:
        print(f"Unexpected error: {e}")
        return None