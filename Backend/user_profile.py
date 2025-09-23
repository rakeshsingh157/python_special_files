from flask import Blueprint, request, jsonify, session
import mysql.connector
from mysql.connector import Error
from bcrypt import hashpw, gensalt, checkpw

profile_bp = Blueprint('profile', __name__)

# --- Database Configuration ---
DB_HOST = "database-1.chcyc88wcx2l.eu-north-1.rds.amazonaws.com"
DB_USER = "admin"
DB_PASSWORD = "DBpicshot"
DB_DATABASE = "eventsreminder"

def get_db_connection():
    try:
        return mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_DATABASE)
    except Error as e:
        print(f"❌ DB Connection Error: {e}")
        return None

# --- API Endpoints for Profile Data ---
@profile_bp.route('/api/profile', methods=['GET'])
def get_profile_data():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': 'Not logged in'}), 401

    conn = get_db_connection()
    if conn is None: return jsonify({'message': 'Database connection error'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT username, profile_bio, photo_url, email, phone FROM users WHERE user_id = %s", (user_id,))
        user_data = cursor.fetchone()

        if not user_data: return jsonify({'message': 'User not found'}), 404

        # Updated stat queries
        cursor.execute("SELECT COUNT(*) as tasks_done FROM events WHERE user_id = %s AND done = TRUE", (user_id,))
        tasks_done = cursor.fetchone()['tasks_done']
        
        cursor.execute("SELECT COUNT(*) as undone_tasks FROM events WHERE user_id = %s AND done = FALSE", (user_id,))
        undone_tasks = cursor.fetchone()['undone_tasks']

        cursor.execute("SELECT COUNT(*) as total_tasks FROM events WHERE user_id = %s", (user_id,))
        total_tasks = cursor.fetchone()['total_tasks']

        profile_data = {
            'username': user_data['username'],
            'bio': user_data['profile_bio'],
            'avatar': user_data['photo_url'],
            'email': user_data['email'],
            'phone': user_data['phone'],
            'stats': { 
                'tasks_done': tasks_done, 
                'undone_tasks': undone_tasks, 
                'total_tasks': total_tasks 
            }
        }
        return jsonify(profile_data), 200
    except mysql.connector.Error as err:
        return jsonify({'message': f'Server error: {err}'}), 500
    finally:
        cursor.close()
        conn.close()

@profile_bp.route('/api/profile', methods=['POST'])
def update_profile_data():
    user_id = session.get('user_id')
    if not user_id: return jsonify({'message': 'Not logged in'}), 401
    
    data = request.json
    new_username, new_bio = data.get('username'), data.get('bio')
    if not new_username or not new_bio: return jsonify({'message': 'Username and bio are required'}), 400

    conn = get_db_connection()
    if conn is None: return jsonify({'message': 'Database connection error'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET username = %s, profile_bio = %s WHERE user_id = %s", (new_username, new_bio, user_id))
        conn.commit()
        return jsonify({'message': 'Profile updated successfully'}), 200
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Update failed: {err}'}), 500
    finally:
        cursor.close()
        conn.close()

@profile_bp.route('/api/profile/photo', methods=['POST'])
def update_profile_photo():
    user_id = session.get('user_id')
    if not user_id: return jsonify({'message': 'Not logged in'}), 401

    data = request.json
    new_photo_url = data.get('photo_url')
    if not new_photo_url: return jsonify({'message': 'Photo URL is required'}), 400

    conn = get_db_connection()
    if conn is None: return jsonify({'message': 'Database connection error'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET photo_url = %s WHERE user_id = %s", (new_photo_url, user_id))
        conn.commit()
        return jsonify({'message': 'Profile photo updated successfully'}), 200
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Update failed: {err}'}), 500
    finally:
        cursor.close()
        conn.close()

@profile_bp.route('/api/profile/contact', methods=['POST'])
def update_contact_info():
    user_id = session.get('user_id')
    if not user_id: return jsonify({'message': 'Not logged in'}), 401
    
    data = request.json
    new_email, new_phone = data.get('email'), data.get('phone')
    if not new_email or not new_phone: return jsonify({'message': 'Email and phone are required'}), 400

    conn = get_db_connection()
    if conn is None: return jsonify({'message': 'Database connection error'}), 500
    
    cursor = conn.cursor()
    try:
        check_cursor = conn.cursor(dictionary=True)
        check_cursor.execute("SELECT user_id FROM users WHERE (email = %s OR phone = %s) AND user_id != %s", (new_email, new_phone, user_id))
        if check_cursor.fetchone():
            return jsonify({'message': 'Email or phone number is already in use.'}), 409
        
        cursor.execute("UPDATE users SET email = %s, phone = %s WHERE user_id = %s", (new_email, new_phone, user_id))
        conn.commit()
        return jsonify({'message': 'Contact information updated successfully'}), 200
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Update failed: {err}'}), 500
    finally:
        cursor.close()
        conn.close()

@profile_bp.route('/api/profile/change-password', methods=['POST'])
def change_password():
    user_id = session.get('user_id')
    if not user_id: return jsonify({'message': 'Not logged in'}), 401
    
    data = request.json
    old_password, new_password = data.get('old_password'), data.get('new_password')
    if not old_password or not new_password: return jsonify({'message': 'Old and new passwords are required'}), 400

    conn = get_db_connection()
    if conn is None: return jsonify({'message': 'Database connection error'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT password FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user: return jsonify({'message': 'User not found'}), 404

        if checkpw(old_password.encode('utf-8'), user['password'].encode('utf-8')):
            hashed_new_password = hashpw(new_password.encode('utf-8'), gensalt())
            update_cursor = conn.cursor()
            update_cursor.execute("UPDATE users SET password = %s WHERE user_id = %s", (hashed_new_password.decode('utf-8'), user_id))
            conn.commit()
            update_cursor.close()
            return jsonify({'message': 'Password updated successfully'}), 200
        else:
            return jsonify({'message': 'Incorrect old password'}), 403
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Server error: {err}'}), 500
    finally:
        cursor.close()
        conn.close()

# New endpoint to fetch events for the calendar
@profile_bp.route('/api/events', methods=['GET'])
def get_events_for_month():
    user_id = session.get('user_id')
    if not user_id: return jsonify({'message': 'Not logged in'}), 401

    year = request.args.get('year')
    month = request.args.get('month')

    if not year or not month:
        return jsonify({'message': 'Year and month parameters are required'}), 400

    conn = get_db_connection()
    if conn is None: return jsonify({'message': 'Database connection error'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        # Query for events in the given month and year
        date_pattern = f"{year}-{int(month):02d}-%"
        cursor.execute("SELECT date, done FROM events WHERE user_id = %s AND date LIKE %s", (user_id, date_pattern))
        events = cursor.fetchall()

        events_by_day = {}
        for event in events:
            # Assumes date is in 'YYYY-MM-DD' format
            day = int(event['date'].split('-')[2])
            if day not in events_by_day:
                events_by_day[day] = {'hasPending': False, 'hasCompleted': False}
            
            if event['done']:
                events_by_day[day]['hasCompleted'] = True
            else:
                events_by_day[day]['hasPending'] = True

        return jsonify(events_by_day)

    except mysql.connector.Error as err:
        return jsonify({'message': f'Server error: {err}'}), 500
    finally:
        cursor.close()
        conn.close()

