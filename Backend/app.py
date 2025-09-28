from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import mysql.connector
from mysql.connector import Error
from user_profile import profile_bp
import os
from werkzeug.utils import secure_filename
from bcrypt import hashpw, gensalt, checkpw
import uuid
from login_register import auth_bp, init_db
from collaboration import collaboration_bp
from ai import ai_bp
from ai_assistant import ai_assistant_bp
from home_routes import home_bp
from tasks import tasks_bp
from schedule import schedule_bp
from config import Config
from dotenv import load_dotenv

load_dotenv()

# Validate configuration
Config.validate_config()

# Create the Flask application instance
app = Flask(__name__)
app = Flask(__name__, template_folder='../', static_folder='static')
app.secret_key = Config.SECRET_KEY or os.urandom(24)




app.register_blueprint(profile_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(collaboration_bp)
app.register_blueprint(ai_assistant_bp)
app.register_blueprint(home_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(schedule_bp)

# --- Database and Uploads Configuration ---
@app.route("/")
def home():
    """Serves the main login/signup page."""
    return render_template("index.html")


@app.route("/profile/<user_id>")
def profile_page(user_id):
    """Serves the user profile page."""
    return render_template("profile.html", user_id=user_id)


@app.route("/home")
def home_page():
    if 'user_id' not in session: return redirect(url_for('home'))
    return render_template("home.html")

@app.route("/schedule")
def schedule_page():
    if 'user_id' not in session: return redirect(url_for('home'))
    return render_template("schedule.html")

@app.route("/add_event")
def add_event_page():
    if 'user_id' not in session: return redirect(url_for('home'))
    return render_template("add-new-task.html")

@app.route("/AI")
def ai_page():
    if 'user_id' not in session:
        return render_template("index.html")
    return render_template("AI.html")
    
@app.route("/aiAssistant")
def ai_assistant_page():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    return render_template("AiAssistant.html")
    
@app.route("/collaboration")
def collaboration_page():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    return render_template("collabration.html")

# --- Main entry point ---
if __name__ == "__main__":
    init_db()  # Re-enable database initialization
    app.run(debug=True)

