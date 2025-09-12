from flask import Blueprint, request, jsonify, session
import mysql.connector
from mysql.connector import Error
from bcrypt import hashpw, gensalt, checkpw
import uuid

auth_bp = Blueprint('auth', __name__)

# --- Database Configuration ---
DB_HOST = "photostore.ct0go6um6tj0.ap-south-1.rds.amazonaws.com"
DB_USER = "admin"
DB_PASSWORD = "DBpicshot"
DB_DATABASE = "eventsreminder"

# --- Database Initialization ---
def init_db():
    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_DATABASE}")
        cursor.close()
        conn.close()

        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id varchar(255) not null UNIQUE,
            photo_url VARCHAR(255) DEFAULT 'https://i.ibb.co/68XqnN2/default-avatar.png',
            profile_bio VARCHAR(255) DEFAULT 'Productivity enthusiast and UI/UX designer.',
            username VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            phone VARCHAR(20) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # Updated Events Table Schema
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id varchar(255),
            title VARCHAR(255) NOT NULL,
            description TEXT,
            Category VARCHAR(255),
            date VARCHAR(255) NOT NULL,
            time VARCHAR(50),
            done BOOLEAN NOT NULL DEFAULT FALSE,
            reminder_setting VARCHAR(50),
            reminder_datetime VARCHAR(255),
            reminde1 boolean,
            reminde2 boolean,
            reminde3 boolean,
            reminde4 boolean,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ DB + Tables ensured.")
    except Error as e:
        print(f"❌ DB Init Error: {e}")

def get_db_connection():
    try:
        return mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_DATABASE)
    except Error as e:
        print(f"❌ DB Connection Error: {e}")
        return None

# --- Authentication Endpoints ---
@auth_bp.route('/register', methods=['POST'])
def register_user():
    data = request.json
    username, email, phone, password = data.get('username'), data.get('email'), data.get('phone'), data.get('password')

    if not all([username, email, phone, password]):
        return jsonify({'message': 'All fields are required!'}), 400

    conn = get_db_connection()
    if conn is None: return jsonify({'message': 'Database connection error'}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM users WHERE email = %s OR phone = %s", (email, phone))
        if cursor.fetchone():
            return jsonify({'message': 'User with this email or phone already exists'}), 409

        user_id = str(uuid.uuid4())
        hashed_password = hashpw(password.encode('utf-8'), gensalt())
        cursor.execute(
            "INSERT INTO users (user_id, username, email, phone, password) VALUES (%s, %s, %s, %s, %s)",
            (user_id, username, email, phone, hashed_password.decode('utf-8'))
        )
        conn.commit()
        return jsonify({'message': 'User registered successfully!'}), 201
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Registration failed: {err}'}), 500
    finally:
        cursor.close()
        conn.close()

@auth_bp.route('/login', methods=['POST'])
def login_user():
    data = request.json
    email, password = data.get('email'), data.get('password')

    if not all([email, password]):
        return jsonify({'message': 'Email and password are required!'}), 400

    conn = get_db_connection()
    if conn is None: return jsonify({'message': 'Database connection error'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT user_id, password FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user and checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['user_id'] = user['user_id']
            return jsonify({'message': 'Login successful'}), 200
        else:
            return jsonify({'message': 'Invalid email or password.'}), 401
    except mysql.connector.Error as err:
        return jsonify({'message': f'Login failed: {err}'}), 500
    finally:
        cursor.close()
        conn.close()

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'}), 200

