import mysql.connector
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Database configuration details from environment variables
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"), 
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "use_pure": bool(os.getenv("USE_PURE", True))
}

def get_db_connection():
    """
    Establishes and returns a new database connection.
    This function is now available to be imported by other modules.
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("Database connection successfully created.")
        return conn
    except mysql.connector.Error as e:
        print(f"Database connection failed: {e}")
        return None

class Database:
    def __init__(self):
        self.connection = get_db_connection()
        if not self.connection:
            raise Exception("Failed to initialize database connection.")
        
    def ensure_connection(self):
        """Ensures the database connection is active."""
        try:
            # The ping=True argument attempts to reconnect if the connection is lost.
            if not self.connection or not self.connection.is_connected():
                 print("Reconnecting to the database...")
                 self.connection = get_db_connection()
            if not self.connection:
                raise Exception("Failed to re-establish database connection.")
        except mysql.connector.Error as e:
            print(f"Connection check failed, attempting to reconnect: {e}")
            self.connection = get_db_connection()
            if not self.connection:
                 raise Exception("Failed to re-establish database connection after ping failure.")
            
    def add_event(self, user_id, title, description, category, date, time, 
                 reminder_setting, reminder_datetime):
        self.ensure_connection()
        cursor = self.connection.cursor()
        
        query = """
            INSERT INTO events 
            (user_id, title, description, category, date, time, done, 
             reminder_setting, reminder_datetime, reminde1, reminde2, reminde3, reminde4)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            user_id, title, description, category, date, time, False,
            reminder_setting, reminder_datetime, False, False, False, False
        )
        
        try:
            cursor.execute(query, values)
            self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            self.connection.rollback()
            raise e
        finally:
            cursor.close()
            
    def get_events(self, user_id):
        self.ensure_connection()
        cursor = self.connection.cursor(dictionary=True)
        
        query = "SELECT * FROM events WHERE user_id = %s ORDER BY date, time"
        
        try:
            cursor.execute(query, (user_id,))
            return cursor.fetchall()
        except Exception as e:
            raise e
        finally:
            cursor.close()
