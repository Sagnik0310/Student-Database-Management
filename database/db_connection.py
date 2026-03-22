import mysql.connector as mc
import os
from dotenv import load_dotenv
from logs.logger import logger

load_dotenv("config.env")

def get_connection():

    try:
        db = mc.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )

        logger.info("Database connected successfully")
        return db

    except mc.Error as e:
        logger.error(f"MySQL connection error: {e}")
        print("Database connection failed")
        return None

    except Exception as e:
        logger.error(f"Unexpected error while connecting DB: {e}")
        print("Unexpected error occurred")
        return None