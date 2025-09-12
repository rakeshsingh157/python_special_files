from flask import Blueprint , jsonify, session, request
from database import get_db_connection
from mysql.connector import Error
from datetime import datetime

# This can be a new Blueprint or part of your main app
home_bp = Blueprint('home', __name__)

@home_bp.route("/api/tasks/today")
def get_today_tasks():
    """Fetches tasks scheduled for the current date for the logged-in user."""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    today_date = datetime.now().strftime('%Y-%m-%d')
    
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
    """Fetches the distinct days that have unfinished tasks for a given month and year."""
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

