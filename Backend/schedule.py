from flask import Blueprint, jsonify, session, request
from database import get_db_connection
from mysql.connector import Error
from datetime import datetime

schedule_bp = Blueprint('schedule', __name__)

@schedule_bp.route("/api/tasks/all")
def get_all_tasks():
    """Fetches ALL tasks (pending and completed) for the logged-in user."""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
        
    try:
        cursor = conn.cursor(dictionary=True)
        # Fetches all tasks and orders them by date and time
        query = """
            SELECT id, title, description, category, date, time, done, reminder_setting 
            FROM events 
            WHERE user_id = %s
            ORDER BY date, time
        """
        cursor.execute(query, (user_id,))
        tasks = cursor.fetchall()
        return jsonify(tasks)
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@schedule_bp.route("/api/schedule/events/month_view")
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
        
        print(f"Pending days for month {month}: {pending_days}") # Debugging line
        print(f"Completed days for month {month}: {completed_days}") # Debugging line

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