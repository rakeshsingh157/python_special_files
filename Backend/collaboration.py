from flask import Blueprint, request, jsonify, session
from database import get_db_connection
from mysql.connector import Error

collaboration_bp = Blueprint('collaboration', __name__)

# --- Collaboration Endpoints ---

@collaboration_bp.route("/api/collaboration/invite", methods=['POST'])
def invite_collaborator():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    inviter_id = session['user_id']
    invitee_email = request.json.get('email')
    if not invitee_email: return jsonify({"error": "Email is required"}), 400
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (invitee_email,))
        invitee = cursor.fetchone()
        if not invitee: return jsonify({"error": "User with that email not found"}), 404
        invitee_id = invitee['user_id']
        if inviter_id == invitee_id: return jsonify({"error": "You cannot invite yourself"}), 400
        cursor.execute("SELECT id FROM collaborations WHERE (inviter_id = %s AND invitee_id = %s) OR (inviter_id = %s AND invitee_id = %s)", (inviter_id, invitee_id, invitee_id, inviter_id))
        if cursor.fetchone(): return jsonify({"error": "An invitation already exists or you are already collaborators."}), 409
        cursor.execute("INSERT INTO collaborations (inviter_id, invitee_id) VALUES (%s, %s)", (inviter_id, invitee_id))
        conn.commit()
        return jsonify({"message": "Invitation sent successfully!"}), 201
    except Error as e:
        return jsonify({"error": f"An internal error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@collaboration_bp.route("/api/collaboration/requests")
def get_collaboration_requests():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    current_user_id = session['user_id']
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT c.id, u.username, u.photo_url FROM collaborations c JOIN users u ON c.inviter_id = u.user_id WHERE c.invitee_id = %s AND c.status = 'pending'"
        cursor.execute(query, (current_user_id,))
        requests = cursor.fetchall()
        return jsonify(requests), 200
    except Error as e:
        return jsonify({"error": f"An internal error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@collaboration_bp.route("/api/collaboration/requests/<int:request_id>", methods=['POST'])
def respond_to_request(request_id):
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    current_user_id, action = session['user_id'], request.json.get('action')
    if action not in ['accept', 'decline']: return jsonify({"error": "Invalid action"}), 400
    new_status = 'accepted' if action == 'accept' else 'declined'
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE collaborations SET status = %s WHERE id = %s AND invitee_id = %s", (new_status, request_id, current_user_id))
        if cursor.rowcount == 0: return jsonify({"error": "Request not found or you are not authorized to respond."}), 404
        conn.commit()
        return jsonify({"message": f"Invitation {action}ed."}), 200
    except Error as e:
        return jsonify({"error": f"An internal error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@collaboration_bp.route("/api/collaborators")
def get_collaborators():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    user_id = session['user_id']
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT u.user_id, u.username, u.photo_url, u.profile_bio FROM users u JOIN collaborations c ON u.user_id = IF(c.inviter_id = %s, c.invitee_id, c.inviter_id) WHERE (c.inviter_id = %s OR c.invitee_id = %s) AND c.status = 'accepted'"
        cursor.execute(query, (user_id, user_id, user_id))
        collaborators = cursor.fetchall()
        return jsonify(collaborators), 200
    except Error as e:
        return jsonify({"error": f"An internal error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@collaboration_bp.route("/api/collaborator/remove", methods=['POST'])
def remove_collaborator():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    user_id = session['user_id']
    collaborator_id = request.json.get('collaborator_id')
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM collaborations WHERE (inviter_id = %s AND invitee_id = %s) OR (inviter_id = %s AND invitee_id = %s)", (user_id, collaborator_id, collaborator_id, user_id))
        conn.commit()
        if cursor.rowcount > 0:
            return jsonify({"message": "Collaborator removed successfully"}), 200
        else:
            return jsonify({"error": "Collaboration not found"}), 404
    except Error as e:
        return jsonify({"error": f"An internal error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

# --- Task Viewing Endpoints ---
@collaboration_bp.route("/api/tasks/personal")
def get_personal_tasks():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    user_id = session['user_id']
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database error"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        # UPDATED QUERY: Only return tasks that were assigned TO the user by others (not self-created tasks)
        query = """
            SELECT
                e.*,
                assigner.email as assigner_email
            FROM
                events e
            INNER JOIN
                assigned_tasks at ON e.id = at.event_id
            INNER JOIN
                users assigner ON at.assigner_id = assigner.user_id
            WHERE
                e.user_id = %s AND at.assignee_id = %s AND at.assigner_id != %s
            ORDER BY
                e.date, e.time
        """
        cursor.execute(query, (user_id, user_id, user_id))
        tasks = cursor.fetchall()
        return jsonify(tasks), 200
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn.is_connected(): cursor.close(); conn.close()

@collaboration_bp.route("/api/tasks/assigned-by-me")
def get_assigned_tasks():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    user_id = session['user_id']
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database error"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT e.*, u.username as assignee_name FROM events e JOIN assigned_tasks at ON e.id = at.event_id JOIN users u ON at.assignee_id = u.user_id WHERE at.assigner_id = %s ORDER BY e.date, e.time"
        cursor.execute(query, (user_id,))
        tasks = cursor.fetchall()
        return jsonify(tasks), 200
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn.is_connected(): cursor.close(); conn.close()

# --- Task Assignment & Action Endpoints ---
@collaboration_bp.route('/api/task/create_and_assign', methods=['POST'])
def create_and_assign_task():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    assigner_id = session['user_id']
    data = request.json
    assignee_id, title, description, category, event_date, event_time = data.get('assignee_id'), data.get('title'), data.get('description'), data.get('category'), data.get('date'), data.get('time')
    if not all([assignee_id, title, category, event_date, event_time]): return jsonify({"error": "Missing required fields"}), 400
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    try:
        cursor = conn.cursor()
        conn.start_transaction()
        event_query = "INSERT INTO events (user_id, title, description, category, date, time, done, reminder_setting, reminder_datetime, reminde1, reminde2, reminde3, reminde4) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        event_values = (assignee_id, title, description, category, event_date, event_time, False, 'none', None, False, False, False, False)
        cursor.execute(event_query, event_values)
        new_event_id = cursor.lastrowid
        assignment_query = "INSERT INTO assigned_tasks (assigner_id, assignee_id, event_id) VALUES (%s, %s, %s)"
        cursor.execute(assignment_query, (assigner_id, assignee_id, new_event_id))
        conn.commit()
        return jsonify({"message": "Task created and assigned successfully", "event_id": new_event_id}), 201
    except Error as e:
        if conn and conn.is_connected(): conn.rollback()
        return jsonify({"error": f"An internal error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@collaboration_bp.route('/api/task/<int:task_id>/toggle_done', methods=['POST'])
def toggle_task_done(task_id):
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    user_id = session['user_id']
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    try:
        cursor = conn.cursor()
        query = "UPDATE events SET done = NOT done WHERE id = %s AND user_id = %s"
        cursor.execute(query, (task_id, user_id))
        if cursor.rowcount == 0: return jsonify({"error": "Task not found or you don't have permission."}), 404
        conn.commit()
        return jsonify({"message": "Task status updated."}), 200
    except Error as e:
        return jsonify({"error": f"An internal error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@collaboration_bp.route('/api/task/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    current_user_id = session['user_id']
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        conn.start_transaction()
        perm_query = "SELECT e.user_id, at.assigner_id FROM events e LEFT JOIN assigned_tasks at ON e.id = at.event_id WHERE e.id = %s"
        cursor.execute(perm_query, (task_id,))
        task_info = cursor.fetchone()
        if not task_info: return jsonify({"error": "Task not found."}), 404
        is_owner = task_info.get('user_id') == current_user_id
        is_assigner = task_info.get('assigner_id') == current_user_id
        if not (is_owner or is_assigner): return jsonify({"error": "You do not have permission to delete this task."}), 403
        cursor.execute("DELETE FROM assigned_tasks WHERE event_id = %s", (task_id,))
        cursor.execute("DELETE FROM events WHERE id = %s", (task_id,))
        conn.commit()
        return jsonify({"message": "Task successfully deleted."}), 200
    except Error as e:
        if conn and conn.is_connected(): conn.rollback()
        return jsonify({"error": f"An internal error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@collaboration_bp.route("/api/tasks/own")
def get_own_tasks():
    """Get tasks created by the user themselves (not assigned by others)"""
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    user_id = session['user_id']
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database error"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        # Get tasks that belong to the user but are NOT assigned by others
        query = """
            SELECT e.*
            FROM events e
            LEFT JOIN assigned_tasks at ON e.id = at.event_id
            WHERE e.user_id = %s AND (at.event_id IS NULL OR at.assigner_id = %s)
            ORDER BY e.date, e.time
        """
        cursor.execute(query, (user_id, user_id))
        tasks = cursor.fetchall()
        return jsonify(tasks), 200
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn.is_connected(): cursor.close(); conn.close()

@collaboration_bp.route("/api/collaboration/events/month_view")
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