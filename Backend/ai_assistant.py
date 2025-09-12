import os
from flask import Blueprint, request, jsonify, session
from dotenv import load_dotenv
import google.generativeai as genai
from database import get_db_connection # Make sure you can import your DB connection
from mysql.connector import Error
from datetime import datetime, timedelta

load_dotenv()

ai_assistant_bp = Blueprint('ai_assistant', __name__)

api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    print("Warning: GOOGLE_GEMINI_API_KEY not found in .env file.")

# --- NEW HELPER FUNCTION TO GET SCHEDULE ---
def _get_user_schedule(user_id):
    """Fetches the user's upcoming events for the next 7 days from the database."""
    conn = get_db_connection()
    if not conn:
        return "Database connection failed."
    
    try:
        cursor = conn.cursor(dictionary=True)
        # Get events from today onwards for the next 7 days
        today = datetime.now().strftime('%Y-%m-%d')
        end_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        query = "SELECT title, date, time FROM events WHERE user_id = %s AND date >= %s AND date <= %s AND done = FALSE ORDER BY date, time"
        cursor.execute(query, (user_id, today, end_date))
        events = cursor.fetchall()
        
        if not events:
            return "The user's schedule for the next 7 days is clear."
            
        # Format the events into a clean string for the AI
        schedule_string = "Here is the user's schedule for the next 7 days:\n"
        for event in events:
            schedule_string += f"- On {event['date']} at {event['time']}: {event['title']}\n"
        return schedule_string
        
    except Error as e:
        print(f"Database error fetching schedule: {e}")
        return "Could not retrieve schedule due to a database error."
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@ai_assistant_bp.route("/api/ai/chat", methods=['POST'])
def ai_chat():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    user_message = request.json.get("message")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        # 1. Get the user's schedule from the database
        schedule_context = _get_user_schedule(user_id)

        history = session.get('chat_history', [])
        history.append({'role': 'user', 'parts': [{'text': user_message}]})

        # 2. Create a dynamic system prompt including the schedule context
        system_prompt = f"""
        You are Scout, a friendly and professional project management assistant integrated into the HelpScout application.
        Your goal is to help users organize their work, plan tasks, and manage schedules effectively based on the context provided.
        - Be concise, encouraging, and clear in your responses.
        - When asked to generate a list of tasks or ideas, always use markdown bullet points.
        - Use the current date of {datetime.now().strftime('%A, %Y-%m-%d')} for any time-related questions like "tomorrow".

        ---
        CONTEXT:
        {schedule_context}
        ---
        """
        
        model = genai.GenerativeModel('gemini-1.5-flash-latest', system_instruction=system_prompt)
        chat = model.start_chat(history=history)
        response = chat.send_message(user_message)
        ai_response_text = response.text

        history.append({'role': 'model', 'parts': [{'text': ai_response_text}]})
        session['chat_history'] = history
        session.modified = True

        return jsonify({"reply": ai_response_text})

    except Exception as e:
        print(f"An error occurred with the Gemini API: {e}")
        return jsonify({"error": "An error occurred while communicating with the AI assistant."}), 500