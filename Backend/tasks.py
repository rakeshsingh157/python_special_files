from flask import Blueprint, request, jsonify, session
from database import get_db_connection
from mysql.connector import Error
from datetime import datetime, timedelta
import pytz  # You may need to run: pip install pytz

# This can be a new Blueprint or part of your main app
tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route("/api/tasks/add", methods=['POST'])
def add_task():
    """Handles the creation of a new task from the add-new-task.html form."""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    data = request.json
    
    title = data.get('title')
    description = data.get('description')
    category = data.get('category')
    date = data.get('date')
    time = data.get('time')
    reminder_setting = data.get('reminder_setting')

    if not all([title, category, date, time, reminder_setting]):
        return jsonify({"error": "Please fill out all required fields."}), 400

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

        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = conn.cursor()
        
        query = """
            INSERT INTO events 
            (user_id, title, description, category, date, time, done, 
             reminder_setting, reminder_datetime, reminde1, reminde2, reminde3, reminde4)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            user_id, title, description, category, date, time, False,
            reminder_setting, reminder_datetime_str, False, False, False, False
        )
        
        cursor.execute(query, values)
        conn.commit()
        
        return jsonify({"message": "Task added successfully!", "task_id": cursor.lastrowid}), 201

    except Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@tasks_bp.route("/api/tasks/events/month_view")
def get_events_for_month():
    """
    Fetches days with pending tasks and days with only completed tasks 
    for a given month and year.
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    user_id = session['user_id']
    year = request.args.get('year')
    month = request.args.get('month')

    if not year or not month:
        return jsonify({"error": "Year and month parameters are required"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        
        # Query 1: Get days with at least one PENDING task
        pending_query = """
            SELECT DISTINCT DAY(STR_TO_DATE(date, '%Y-%m-%d')) as event_day 
            FROM events 
            WHERE user_id = %s AND done = FALSE
            AND YEAR(STR_TO_DATE(date, '%Y-%m-%d')) = %s 
            AND MONTH(STR_TO_DATE(date, '%Y-%m-%d')) = %s
        """
        cursor.execute(pending_query, (user_id, year, month))
        pending_days = [row['event_day'] for row in cursor.fetchall()]

        # Query 2: Get days that ONLY have COMPLETED tasks
        completed_query = """
            SELECT DAY(STR_TO_DATE(date, '%Y-%m-%d')) as event_day
            FROM events
            WHERE user_id = %s
              AND YEAR(STR_TO_DATE(date, '%Y-%m-%d')) = %s
              AND MONTH(STR_TO_DATE(date, '%Y-%m-%d')) = %s
            GROUP BY date
            HAVING SUM(CASE WHEN done = FALSE THEN 1 ELSE 0 END) = 0
        """
        cursor.execute(completed_query, (user_id, year, month))
        completed_days = [row['event_day'] for row in cursor.fetchall() if row['event_day'] not in pending_days]
        
        return jsonify({
            "pending": pending_days,
            "completed": completed_days
        })
        
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

