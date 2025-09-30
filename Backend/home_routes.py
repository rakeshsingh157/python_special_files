from flask import Blueprint , jsonify, session, request
from database import get_db_connection
from mysql.connector import Error
from datetime import datetime
import pytz

# Configure IST timezone
IST = pytz.timezone('Asia/Kolkata')

# This can be a new Blueprint or part of your main app
home_bp = Blueprint('home', __name__)

@home_bp.route("/api/tasks/today")
def get_today_tasks():
    """Fetches tasks scheduled for the current date for the logged-in user."""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    today_date = datetime.now(IST).strftime('%Y-%m-%d')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
        
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT title, description, time 
            FROM events 
            WHERE user_id = %s AND date = %s AND done = FALSE 
            ORDER BY time
        """
        cursor.execute(query, (user_id, today_date))
        tasks = cursor.fetchall()
        return jsonify(tasks)
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@home_bp.route("/api/events/month_view")
def get_events_for_month():
    """Fetches the days with pending and/or completed tasks for a given month and year."""
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
        date_pattern = f"{year}-{int(month):02d}-%"
        cursor.execute("SELECT date, done FROM events WHERE user_id = %s AND date LIKE %s", (user_id, date_pattern))
        events = cursor.fetchall()

        events_by_day = {}
        for event in events:
            day = int(event['date'].split('-')[2])
            if day not in events_by_day:
                events_by_day[day] = {'hasPending': False, 'hasCompleted': False}
            if event['done']:
                events_by_day[day]['hasCompleted'] = True
            else:
                events_by_day[day]['hasPending'] = True

        return jsonify(events_by_day)
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

