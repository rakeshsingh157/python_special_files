from flask import Blueprint, request, jsonify, session
import mysql.connector
from mysql.connector import Error
from ai_scheduler import AIScheduler
from config import Config
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pytz
from database import get_db_connection

load_dotenv()

ai_bp = Blueprint('ai', __name__)

# --- Database Configuration from Environment Variables ---
DB_HOST = Config.DB_HOST
DB_USER = Config.DB_USER
DB_PASSWORD = Config.DB_PASSWORD
DB_DATABASE = Config.DB_DATABASE

def get_db_connection():
    try:
        return mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_DATABASE
        )
    except Error as e:
        print(f"❌ DB Connection Error: {e}")
        return None

ai_scheduler = AIScheduler()

@ai_bp.route('/api/<user_id>/ai/generate-schedule', methods=['POST'])
def generate_schedule_with_user():
    if 'user_id' not in session:
        return jsonify({'message': 'Not logged in'}), 401

    data = request.json
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({'message': 'Prompt is required'}), 400

    try:
        tasks = ai_scheduler.generate_tasks(prompt)
        return jsonify(tasks), 200
    except Exception as e:
        print(f"Error in AI generation: {e}")
        return jsonify({'message': 'Failed to generate tasks from AI.'}), 500

@ai_bp.route('/api/ai/generate-schedule', methods=['POST'])
def generate_schedule():
    if 'user_id' not in session:
        return jsonify({'message': 'Not logged in'}), 401

    data = request.json
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({'message': 'Prompt is required'}), 400

    try:
        tasks = ai_scheduler.generate_tasks(prompt)
        return jsonify(tasks), 200
    except Exception as e:
        print(f"Error in AI generation: {e}")
        return jsonify({'message': 'Failed to generate tasks from AI.'}), 500

@ai_bp.route('/api/ai/add-task', methods=['POST'])
def add_ai_task_to_schedule():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': 'Not logged in'}), 401

    data = request.json
    title = data.get('title')
    description = data.get('description')
    category = data.get('category')
    date = data.get('date')
    time = data.get('time')
    reminder_setting = data.get('reminder')

    if not all([title, description, category, date, time, reminder_setting]):
        return jsonify({'message': 'All task fields are required'}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({'message': 'Database connection error'}), 500

    cursor = conn.cursor()
    try:
        # --- Timezone-aware reminder calculation for IST ---
        ist_tz = pytz.timezone('Asia/Kolkata')
        naive_event_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        aware_event_dt = ist_tz.localize(naive_event_dt)
        
        value, unit = reminder_setting.split()
        value = int(value)
        
        delta = timedelta()
        if "minute" in unit:
            delta = timedelta(minutes=value)
        elif "hour" in unit:
            delta = timedelta(hours=value)
        elif "day" in unit:
            delta = timedelta(days=value)
            
        aware_reminder_dt = aware_event_dt - delta
        reminder_datetime_str = aware_reminder_dt.strftime('%Y-%m-%d %H:%M:%S')
        # ---------------------------------------------------

        query = (
            """
            INSERT INTO events 
            (user_id, title, description, category, date, time, done, reminder_setting, reminder_datetime, reminde1, reminde2, reminde3, reminde4)
            VALUES (%s, %s, %s, %s, %s, %s, FALSE, %s, %s, %s, %s, %s, %s)
            """
        )
        values = (user_id, title, description, category, date, time, reminder_setting, reminder_datetime_str, False, False, False, False)
        cursor.execute(query, values)
        conn.commit()
        return jsonify({'message': 'Task added to schedule successfully'}), 201
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Failed to add task: {err}'}), 500
    except Exception as e:
        conn.rollback()
        return jsonify({'message': f'An unexpected error occurred: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

