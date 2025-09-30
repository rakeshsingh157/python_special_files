import os
import re
import json
import cohere
from flask import Blueprint, request, jsonify, session
from dotenv import load_dotenv
import google.generativeai as genai
from database import get_db_connection # Make sure you can import your DB connection
from mysql.connector import Error
from datetime import datetime, timedelta
import pytz
from groq import Groq

# Configure IST timezone
IST = pytz.timezone('Asia/Kolkata')

load_dotenv()

ai_assistant_bp = Blueprint('ai_assistant', __name__)

# API configurations
api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
cohere_api_key = os.getenv("COHERE_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
else:
    print("Warning: GOOGLE_GEMINI_API_KEY not found in .env file.")

# Initialize backup AI clients
co = None
groq_client = None

if cohere_api_key:
    co = cohere.Client(cohere_api_key)
    
if groq_api_key:
    groq_client = Groq(api_key=groq_api_key)

# --- SMART AI EVENT DETECTION AND CREATION ---
def detect_and_create_events(user_message, user_id):
    """
    Uses AI to intelligently detect if the user message contains events
    and automatically creates them. Only returns JSON when events are found.
    """
    
    # First, use AI to determine if this message contains events
    today = datetime.now(IST).strftime('%A, %Y-%m-%d')
    
    detection_prompt = f"""
    You are an AI assistant that determines if a user message contains calendar events or event operations.
    
    Today is {today}.
    
    User message: "{user_message}"
    
    Analyze this message and determine:
    1. Does it contain one or more calendar events to be scheduled?
    2. Does it contain requests to delete/cancel/remove events?
    3. Is it asking for event creation/scheduling?
    4. Is it asking for event deletion/cancellation?
    
    Events include: meetings, appointments, calls, lunch, dinner, workouts, classes, etc.
    Deletion keywords: cancel, delete, remove, clear, cancel my, remove my, delete my, etc.
    
    NOT events: questions, help requests, general conversation, reminders without specific events
    
    Respond with ONLY one of these:
    - "EVENTS_FOUND" if the message contains events to schedule
    - "DELETE_EVENTS" if the message contains requests to delete/cancel events
    - "NO_EVENTS" if no events are found
    - "QUESTION" if it's a question or help request
    """
    
    # Try different AI services to detect events
    event_detection_result = None
    
    try:
        # Try Gemini first (primary AI)
        if api_key:
            model = genai.GenerativeModel('gemini-1.5-pro')  # Using working model
            response = model.generate_content(detection_prompt)
            event_detection_result = response.text.strip()
            print(f"Gemini detection result: {event_detection_result}")
    except Exception as gemini_error:
        print(f"Gemini detection failed: {gemini_error}")
        
        try:
            # Fallback to Cohere
            if co:
                response = co.chat(
                    model='command-a-03-2025',
                    message=detection_prompt,
                    max_tokens=20,
                    temperature=0.1
                )
                if hasattr(response, 'text'):
                    event_detection_result = response.text.strip()
                else:
                    event_detection_result = str(response).strip()
                print(f"Cohere detection result: {event_detection_result}")
        except Exception as cohere_error:
            print(f"Cohere detection failed: {cohere_error}")
            
            try:
                # Final fallback to Groq
                if groq_client:
                    response = groq_client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": detection_prompt}],
                        max_tokens=20,
                        temperature=0.1
                    )
                    event_detection_result = response.choices[0].message.content.strip()
                    print(f"Groq detection result: {event_detection_result}")
            except Exception as groq_error:
                print(f"All AI detection failed: {groq_error}")
                return False, "AI detection services unavailable"
    
    # If no events detected, check for deletion requests
    if not event_detection_result or "NO_EVENTS" in event_detection_result or "QUESTION" in event_detection_result:
        return False, f"AI determined: {event_detection_result or 'No clear result'}"
    
    # If deletion request detected, handle event deletion
    if "DELETE_EVENTS" in event_detection_result:
        return handle_event_deletion(user_message, user_id)
    
    # If events found, extract them with AI
    if "EVENTS_FOUND" in event_detection_result:
        extraction_prompt = f"""
        You are an AI assistant that extracts event details from user messages.
        
        Today is {today}.
        Current time: {datetime.now(IST).strftime('%H:%M')}
        
        User message: "{user_message}"
        
        Extract ALL events mentioned in this message. For each event determine:
        1. Title (what is the event)
        2. Description (brief relevant description with context)
        3. Category (from allowed categories only)
        4. Date (convert relative dates like "tomorrow", "next week" to YYYY-MM-DD format)
        5. Time (MUST be in HH:MM format, NEVER use "TBD")
        6. Reminder setting (default "15 minutes" unless specified)
        
        ALLOWED CATEGORIES (choose most appropriate):
        work, home, sports, fun, health, fitness, personal, learning, finance, errands, cleaning, gardening, cooking, pets, meeting, commute, networking, admin, social, entertainment, travel, hobby, volunteering, important, to-do, later, family
        
        TIME REQUIREMENTS:
        - ALWAYS provide a time in HH:MM format (e.g. "09:00", "14:30")
        - NEVER use "TBD", "unknown", or empty time
        - Default times: morning events "09:00", afternoon "14:00", evening "19:00"
        - For school/learning events, use "09:00" as default
        
        DATE INTERPRETATION EXAMPLES:
        - Current date: {datetime.now(IST).strftime('%Y-%m-%d')} (September 29, 2025)
        this is only example
        - "on 1" → "2025-10-01" (October 1st)
        - "on 2" → "2025-10-02" (October 2nd)  
        - "on 5" → "2025-10-05" (October 5th)
        - "on 7" → "2025-10-07" (October 7th)
        - "on 15" → "2025-10-15" (October 15th)
        - "on 25" → "2025-10-25" (October 25th)
        - "tomorrow" → {(datetime.now(IST) + timedelta(days=1)).strftime('%Y-%m-%d')}
        - "today" → {datetime.now(IST).strftime('%Y-%m-%d')}
        
        CRITICAL RULE: Match the EXACT day number from user input!
        
        VALIDATION: 
        - If user says "on 7", the date MUST be "2025-10-07"
        - If user says "on 15", the date MUST be "2025-10-15"  
        - NEVER use today's date unless user says "today"
        - NEVER use "2025-09-29" unless user specifically mentions today
        
        Rules:
        - If no date specified, assume today
        - If no time specified, ALWAYS use "09:00" as default (NEVER use "TBD" or empty time)
        - Handle multiple events in one message
        - Convert times like "2pm" to "14:00"
        - For "on [number]", interpret as that EXACT day number of current/next month
        - NEVER change the day number: "on 5" = day 5, "on 15" = day 15, etc.
        - Use "meeting" category for meetings, calls, appointments
        - Use "health" for doctor/dentist appointments
        - Use "fitness" for gym/workout activities
        - Use "learning" for school, class, education events
        
        Respond with ONLY this JSON format:
        {{
            "events": [
                {{
                    "title": "Event Title",
                    "description": "Detailed description with context",
                    "category": "meeting",
                    "date": "YYYY-MM-DD",
                    "time": "HH:MM",
                    "reminder_setting": "15 minutes"
                }}
            ]
        }}
        """
        
        # Extract events using AI
        events_json = None
        
        try:
            # Try Gemini for extraction
            if api_key:
                print(f"[DEBUG] Extraction prompt for '{user_message}':")
                print(f"[DEBUG] Date interpretation should map 'on 5' to October 5th")
                model = genai.GenerativeModel('gemini-2.0-flash')  # Using faster model
                response = model.generate_content(extraction_prompt)
                events_json = response.text.strip()
                print(f"Gemini extraction result: {events_json}")
        except Exception as gemini_error:
            print(f"Gemini extraction failed: {gemini_error}")
            
            try:
                # Fallback to Cohere for extraction
                if co:
                    response = co.chat(
                        model='command-a-03-2025',
                        message=extraction_prompt,
                        max_tokens=500,
                        temperature=0.1
                    )
                    if hasattr(response, 'text'):
                        events_json = response.text.strip()
                    else:
                        events_json = str(response).strip()
                    print(f"Cohere extraction result: {events_json}")
            except Exception as cohere_error:
                print(f"Cohere extraction failed: {cohere_error}")
                
                try:
                    # Final fallback to Groq for extraction
                    if groq_client:
                        response = groq_client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "user", "content": extraction_prompt}],
                            max_tokens=500,
                            temperature=0.1
                        )
                        events_json = response.choices[0].message.content.strip()
                        print(f"Groq extraction result: {events_json}")
                except Exception as groq_error:
                    print(f"All AI extraction failed: {groq_error}")
                    return False, "AI extraction services unavailable"
        
        # Parse and save events
        if events_json:
            try:
                # Extract JSON from response
                json_start = events_json.find('{')
                json_end = events_json.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    clean_json = events_json[json_start:json_end]
                    events_data = json.loads(clean_json)
                    
                    if 'events' in events_data and events_data['events']:
                        # Validate and fix date interpretation
                        for event in events_data['events']:
                            # Fix common date interpretation errors
                            original_date = event.get('date', '')
                            fixed_date = fix_date_interpretation(user_message, original_date)
                            if fixed_date != original_date:
                                print(f"[DATE FIX] Changed {original_date} → {fixed_date} based on '{user_message}'")
                                event['date'] = fixed_date
                        
                        # Check for conflicts before creating events
                        all_conflicts = []
                        events_to_create = []
                        
                        for event in events_data['events']:
                            if all(key in event for key in ['title', 'date', 'time']):
                                # Check for conflicts
                                conflicts = check_event_conflicts(
                                    user_id, 
                                    event['date'], 
                                    event['time'], 
                                    event['title']
                                )
                                
                                if conflicts:
                                    # Store the pending event in session for later confirmation
                                    from flask import session
                                    session['pending_event_with_conflict'] = event
                                    
                                    # Generate conflict warning
                                    warning_msg = create_conflict_warning_message(
                                        conflicts, 
                                        event['title'], 
                                        event['date'], 
                                        event['time']
                                    )
                                    return False, warning_msg
                                else:
                                    events_to_create.append(event)
                        
                        # No conflicts found, create all events
                        created_count = 0
                        for event in events_to_create:
                            if create_event_in_db(user_id, event):
                                created_count += 1
                        
                        if created_count > 0:
                            return True, f"✅ Successfully created {created_count} event(s) automatically!"
                        else:
                            return False, "Failed to save events to database"
                    else:
                        return False, "No valid events found in AI response"
                else:
                    return False, "Could not parse JSON from AI response"
                    
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                return False, "Invalid JSON format from AI"
            except Exception as e:
                print(f"Event creation error: {e}")
                return False, f"Error creating events: {str(e)}"
    
    return False, "No events detected by AI"


def handle_event_deletion(user_message, user_id):
    """
    Handles event deletion requests using AI to identify which events to delete.
    """
    today = datetime.now(IST).strftime('%A, %Y-%m-%d')
    
    # First, get user's current events to help with deletion
    current_events = get_user_events_for_deletion(user_id)
    
    if not current_events:
        return False, "No events found to delete"
    
    # Create context of current events for AI with ACTUAL database IDs
    events_context = "Current events:\n"
    for event in current_events:
        events_context += f"ID {event['id']}: {event['title']} - {event['date']} at {event['time']}\n"
    
    deletion_prompt = f"""
    You are an AI assistant that identifies which events to delete based on user requests.
    
    Today is {today}.
    Current time: {datetime.now(IST).strftime('%H:%M')}
    
    User message: "{user_message}"
    
    {events_context}
    
    The user wants to delete/cancel events. Based on their message, determine which events should be deleted.
    
    IMPORTANT: Use the actual database ID numbers shown above (like "ID 35", "ID 40", etc.)
    
    Consider:
    - Specific titles mentioned
    - Time references (today, tomorrow, this week)  
    - Event types (meeting, appointment, etc.)
    - Partial matches (user says "cancel meeting" matches any event with "meeting" in title)
    
    Respond with ONLY this JSON format using the ACTUAL database IDs:
    {{
        "delete_events": [
            {{
                "id": actual_database_id_number,
                "title": "Event Title",
                "reason": "Why this event matches the deletion request"
            }}
        ]
    }}
    
    If no events match the deletion criteria, respond with:
    {{"delete_events": []}}
    """
    
    # Get AI analysis for which events to delete
    deletion_analysis = None
    
    try:
        # Try Gemini first (primary AI)
        if api_key:
            model = genai.GenerativeModel('gemini-1.5-pro')
            response = model.generate_content(deletion_prompt)
            deletion_analysis = response.text.strip()
            print(f"Gemini deletion analysis: {deletion_analysis}")
    except Exception as gemini_error:
        print(f"Gemini deletion analysis failed: {gemini_error}")
        
        try:
            # Fallback to Cohere
            if co:
                response = co.chat(
                    model='command-a-03-2025',
                    message=deletion_prompt,
                    max_tokens=500,
                    temperature=0.1
                )
                if hasattr(response, 'text'):
                    deletion_analysis = response.text.strip()
                else:
                    deletion_analysis = str(response).strip()
                print(f"Cohere deletion analysis: {deletion_analysis}")
        except Exception as cohere_error:
            print(f"Cohere deletion analysis failed: {cohere_error}")
            
            try:
                # Final fallback to Groq
                if groq_client:
                    response = groq_client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": deletion_prompt}],
                        max_tokens=500,
                        temperature=0.1
                    )
                    deletion_analysis = response.choices[0].message.content.strip()
                    print(f"Groq deletion analysis: {deletion_analysis}")
            except Exception as groq_error:
                print(f"All AI deletion analysis failed: {groq_error}")
                return False, "AI deletion analysis services unavailable"
    
    # Parse deletion analysis
    if deletion_analysis:
        try:
            # Extract JSON from response - handle malformed JSON
            clean_json = deletion_analysis
            
            # Remove markdown code blocks if present
            if '```json' in clean_json:
                json_start = clean_json.find('```json') + 7
                json_end = clean_json.find('```', json_start)
                if json_end != -1:
                    clean_json = clean_json[json_start:json_end].strip()
            elif '```' in clean_json:
                json_start = clean_json.find('```') + 3
                json_end = clean_json.find('```', json_start)
                if json_end != -1:
                    clean_json = clean_json[json_start:json_end].strip()
            
            # Find JSON boundaries
            json_start = clean_json.find('{')
            json_end = clean_json.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                clean_json = clean_json[json_start:json_end]
            
            # Fix common JSON issues
            clean_json = clean_json.replace('\\n', ' ').replace('\\t', ' ')
            
            # Handle truncated JSON by finding the last complete object
            if clean_json.count('{') > clean_json.count('}'):
                # JSON is truncated, try to fix it
                lines = clean_json.split('\n')
                fixed_lines = []
                brace_count = 0
                
                for line in lines:
                    brace_count += line.count('{') - line.count('}')
                    fixed_lines.append(line)
                    if brace_count == 0:  # Complete JSON object
                        break
                
                clean_json = '\\n'.join(fixed_lines)
                
                # Add missing closing braces
                while brace_count > 0:
                    clean_json += '}'
                    brace_count -= 1
            
            print(f"Attempting to parse JSON: {clean_json[:200]}...")
            deletion_data = json.loads(clean_json)
            
            if 'delete_events' in deletion_data and deletion_data['delete_events']:
                deleted_count = 0
                deleted_titles = []
                
                for event_to_delete in deletion_data['delete_events']:
                    event_id = event_to_delete.get('id')
                    if event_id and delete_event_from_db(user_id, event_id):
                        deleted_count += 1
                        deleted_titles.append(event_to_delete.get('title', 'Unknown'))
                
                if deleted_count > 0:
                    titles_text = ', '.join(deleted_titles)
                    return True, f"✅ Successfully deleted {deleted_count} event(s): {titles_text}"
                else:
                    return False, "Failed to delete events from database"
            else:
                return False, "No matching events found to delete"
                    
        except json.JSONDecodeError as e:
            print(f"JSON parsing error in deletion: {e}")
            return False, "Could not parse deletion analysis"
        except Exception as e:
            print(f"Event deletion error: {e}")
            return False, f"Error processing deletion: {str(e)}"
    
    return False, "Could not analyze deletion request"


def fix_date_interpretation(user_message, ai_date):
    """
    Fix common date interpretation errors by the AI
    Enhanced to handle multiple months and date patterns
    """
    import re
    from datetime import datetime, timedelta
    
    current_date = datetime.now()
    today = current_date.strftime('%Y-%m-%d')
    current_day = current_date.day
    current_month = current_date.month
    
    # Extract "on X" patterns from user message
    on_pattern = re.search(r'\bon\s+(\d+)\b', user_message.lower())
    
    if on_pattern:
        day_number = int(on_pattern.group(1))
        
        # If AI used today's date but user said "on X", fix it
        if ai_date == today and day_number != current_day:
            if 1 <= day_number <= 31:
                # Determine the target month based on context
                target_month = current_month
                target_year = current_date.year
                
                from calendar import monthrange
                current_month_max_day = monthrange(target_year, target_month)[1]
                
                # Check if the day makes sense in the current month context
                if day_number < current_day or day_number > current_month_max_day:
                    # Move to next month
                    target_month += 1
                    if target_month > 12:
                        target_month = 1
                        target_year += 1
                
                # Ensure day exists in target month
                max_day_in_month = monthrange(target_year, target_month)[1]
                
                if day_number <= max_day_in_month:
                    return f"{target_year}-{target_month:02d}-{day_number:02d}"
                else:
                    # Day doesn't exist in target month, try next month
                    target_month += 1
                    if target_month > 12:
                        target_month = 1
                        target_year += 1
                    max_day_in_month = monthrange(target_year, target_month)[1]
                    if day_number <= max_day_in_month:
                        return f"{target_year}-{target_month:02d}-{day_number:02d}"
    
    # Extract month + day patterns (e.g., "October 7", "Nov 15", "December 25")
    month_day_pattern = re.search(
        r'\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d+)\b',
        user_message.lower()
    )
    
    if month_day_pattern:
        month_name = month_day_pattern.group(1).lower()
        day_number = int(month_day_pattern.group(2))
        
        # Month name to number mapping
        month_map = {
            'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
            'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
            'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9,
            'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12
        }
        
        if month_name in month_map:
            target_month = month_map[month_name]
            target_year = current_date.year
            
            # If the month has passed, use next year
            if target_month < current_month or (target_month == current_month and day_number < current_day):
                target_year += 1
            
            # Validate day exists in target month
            from calendar import monthrange
            max_day_in_month = monthrange(target_year, target_month)[1]
            
            if 1 <= day_number <= max_day_in_month:
                return f"{target_year}-{target_month:02d}-{day_number:02d}"
    
    return ai_date


def check_event_conflicts(user_id, new_event_date, new_event_time, new_event_title):
    """
    Check for potential conflicts with existing events on the same date/time
    """
    try:
        conn = get_db_connection()
        if not conn:
            return []
            
        cursor = conn.cursor(dictionary=True)
        
        # Check for events on the same date
        query = """
        SELECT id, title, date, time, category 
        FROM events 
        WHERE user_id = %s AND date = %s AND done = FALSE
        ORDER BY time
        """
        
        cursor.execute(query, (user_id, new_event_date))
        existing_events = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        conflicts = []
        
        if existing_events:
            # Parse new event time
            new_hour, new_min = map(int, new_event_time.split(':'))
            new_minutes_total = new_hour * 60 + new_min
            
            for event in existing_events:
                existing_time = event['time']
                existing_hour, existing_min = map(int, existing_time.split(':'))
                existing_minutes_total = existing_hour * 60 + existing_min
                
                # Check if times are close (within 2 hours)
                time_diff = abs(new_minutes_total - existing_minutes_total)
                
                if time_diff <= 120:  # Within 2 hours
                    conflicts.append({
                        'id': event['id'],
                        'title': event['title'],
                        'time': existing_time,
                        'category': event['category'],
                        'time_diff_minutes': time_diff
                    })
        
        return conflicts
        
    except Exception as e:
        print(f"Error checking conflicts: {e}")
        return []


def create_conflict_warning_message(conflicts, new_event_title, new_event_date, new_event_time):
    """
    Generate a user-friendly conflict warning message
    """
    if not conflicts:
        return None
        
    warning = f"⚠️ **SCHEDULING CONFLICT DETECTED**\n\n"
    warning += f"You want to add: **{new_event_title}** on {new_event_date} at {new_event_time}\n\n"
    warning += f"But you already have:\n"
    
    for conflict in conflicts:
        time_diff = conflict['time_diff_minutes']
        if time_diff == 0:
            warning += f"• **{conflict['title']}** at {conflict['time']} (EXACT SAME TIME!)\n"
        elif time_diff <= 30:
            warning += f"• **{conflict['title']}** at {conflict['time']} (only {time_diff} minutes apart)\n"
        else:
            hours = time_diff // 60
            minutes = time_diff % 60
            if hours > 0:
                warning += f"• **{conflict['title']}** at {conflict['time']} ({hours}h {minutes}m apart)\n"
            else:
                warning += f"• **{conflict['title']}** at {conflict['time']} ({minutes} minutes apart)\n"
    
    warning += f"\n🤔 **Are you sure you want to add this event?**\n"
    warning += f"Reply 'yes' to confirm or 'no' to cancel."
    
    return warning


def get_user_events_for_deletion(user_id):
    """Get user's upcoming events for deletion analysis."""
    try:
        conn = get_db_connection()
        if not conn:
            return []
            
        cursor = conn.cursor()
        
        # Get events from today onwards
        today = datetime.now(IST).strftime('%Y-%m-%d')
        query = """
        SELECT id, title, description, date, time, category 
        FROM events 
        WHERE user_id = %s AND date >= %s AND done = 0
        ORDER BY date, time
        """
        
        cursor.execute(query, (user_id, today))
        events = []
        
        for row in cursor.fetchall():
            events.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'date': row[3],
                'time': row[4],
                'category': row[5]
            })
        
        cursor.close()
        conn.close()
        
        return events
        
    except Error as e:
        print(f"Database error getting events for deletion: {e}")
        return []
    except Exception as e:
        print(f"Error getting events for deletion: {e}")
        return []


def delete_event_from_db(user_id, event_id):
    """Delete a specific event from the database."""
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        cursor = conn.cursor()
        
        # Delete the event (with user_id check for security)
        query = "DELETE FROM events WHERE id = %s AND user_id = %s"
        cursor.execute(query, (event_id, user_id))
        
        deleted_rows = cursor.rowcount
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print(f"✅ Deleted event ID {event_id} for user {user_id}")
        return deleted_rows > 0
        
    except Error as e:
        print(f"Database error deleting event: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False
    except Exception as e:
        print(f"Error deleting event: {e}")
        return False


def create_event_in_db(user_id, event_data):
    """Helper function to create a single event in the database with exact JSON format."""
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        cursor = conn.cursor()
        
        # Validate and fix time format
        event_time = event_data.get('time', '09:00')
        if event_time == 'TBD' or not event_time or ':' not in event_time:
            event_time = '09:00'  # Default time
        
        # Ensure time is in HH:MM format
        if len(event_time.split(':')[0]) == 1:
            event_time = '0' + event_time  # Convert "9:00" to "09:00"
        
        event_data['time'] = event_time  # Update the event data
        
        # Calculate reminder_datetime based on reminder_setting
        event_datetime_str = f"{event_data['date']} {event_time}"
        event_datetime = datetime.strptime(event_datetime_str, '%Y-%m-%d %H:%M')
        
        # Parse reminder setting and calculate reminder_datetime
        reminder_setting = event_data.get('reminder_setting', '15 minutes')
        reminder_datetime = None
        
        if reminder_setting and reminder_setting != "No Reminder":
            if "minute" in reminder_setting:
                minutes = int(reminder_setting.split()[0])
                reminder_datetime = event_datetime - timedelta(minutes=minutes)
            elif "hour" in reminder_setting:
                hours = int(reminder_setting.split()[0])
                reminder_datetime = event_datetime - timedelta(hours=hours)
            elif "day" in reminder_setting:
                days = int(reminder_setting.split()[0])
                reminder_datetime = event_datetime - timedelta(days=days)
            else:
                # Default to 15 minutes
                reminder_datetime = event_datetime - timedelta(minutes=15)
        
        # Insert event into database
        query = """
        INSERT INTO events (user_id, title, description, category, date, time, done, reminder_setting, reminder_datetime)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            user_id,
            event_data['title'],
            event_data.get('description', ''),
            event_data.get('category', 'personal'),  # Default to personal if not specified
            event_data['date'],
            event_data['time'],
            0,  # done = False (0)
            reminder_setting,
            reminder_datetime
        )
        
        cursor.execute(query, values)
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print(f"✅ Event created: {event_data['title']} on {event_data['date']} at {event_data['time']}")
        print(f"   Category: {event_data.get('category', 'personal')}")
        print(f"   Reminder: {reminder_setting} -> {reminder_datetime}")
        
        return True
        
    except Error as e:
        print(f"Database error creating event: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False
    except Exception as e:
        print(f"Error creating event: {e}")
        return False


# --- PATTERN-BASED FALLBACK FUNCTIONS (Kept for backup) ---
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "user", "content": extraction_prompt}
                ],
                model="llama3-8b-8192",  # Try standard model if available
                temperature=0.1
            )
            response_text = chat_completion.choices[0].message.content.strip()
            
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                event_details = json.loads(json_match.group())
        except Exception as e:
            print(f"Groq extraction failed: {e}")
            # If Groq fails too, try another model
            try:
                chat_completion = groq_client.chat.completions.create(
                    messages=[
                        {"role": "user", "content": extraction_prompt}
                    ],
                    model="llama-3.1-8b-instant",  # Alternative Groq model
                    temperature=0.1
                )
                response_text = chat_completion.choices[0].message.content.strip()
                
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    event_details = json.loads(json_match.group())
            except Exception as e2:
                print(f"Groq alternative model also failed: {e2}")
    
    if not event_details or 'events' not in event_details:
        # PATTERN-BASED FALLBACK: Create events even when AI APIs fail
        print("AI APIs failed - attempting pattern-based event extraction")
        event_details = extract_events_with_patterns(user_message)
        
        if not event_details or 'events' not in event_details or len(event_details['events']) == 0:
            return False, "Could not extract event details"
    
    # Create all events in the database
    created_events = []
    conn = get_db_connection()
    
    if not conn:
        return False, "Database connection failed"
    
    try:
        cursor = conn.cursor()
        
        for event in event_details['events']:
            if all(key in event for key in ['title', 'date', 'time']):
                query = "INSERT INTO events (user_id, title, description, date, time, done) VALUES (%s, %s, %s, %s, %s, %s)"
                values = (
                    user_id,
                    event['title'],
                    event.get('description', ''),
                    event['date'],
                    event['time'],
                    0
                )
                cursor.execute(query, values)
                created_events.append(event['title'])
        
        conn.commit()
        
        if created_events:
            return True, f"Created {len(created_events)} events: {', '.join(created_events)}"
        else:
            return False, "No valid events to create"
            
    except Error as e:
        print(f"Database error creating events: {e}")
        return False, f"Database error: {e}"
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def extract_events_with_patterns(user_message):
    """
    Pattern-based event extraction as fallback when AI APIs are unavailable.
    Extracts events using regex patterns and basic natural language processing.
    """
    from datetime import datetime, timedelta
    import re
    
    # Normalize the message
    message_lower = user_message.lower()
    
    # Date extraction and parsing
    today = datetime.now()
    date_map = {
        'today': today.strftime('%Y-%m-%d'),
        'tomorrow': (today + timedelta(days=1)).strftime('%Y-%m-%d'),
        'monday': get_next_weekday(today, 0).strftime('%Y-%m-%d'),
        'tuesday': get_next_weekday(today, 1).strftime('%Y-%m-%d'),
        'wednesday': get_next_weekday(today, 2).strftime('%Y-%m-%d'),
        'thursday': get_next_weekday(today, 3).strftime('%Y-%m-%d'),
        'friday': get_next_weekday(today, 4).strftime('%Y-%m-%d'),
        'saturday': get_next_weekday(today, 5).strftime('%Y-%m-%d'),
        'sunday': get_next_weekday(today, 6).strftime('%Y-%m-%d'),
    }
    
    # Extract date
    event_date = today.strftime('%Y-%m-%d')  # Default to today
    for day_word, day_date in date_map.items():
        if day_word in message_lower:
            event_date = day_date
            break
    
    events = []
    
    # Pattern 1: Look for multiple events with "and" - "meeting at 10am and lunch at 1pm"
    and_pattern = r'(\w+(?:\s+\w+)*?)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s+and\s+(\w+(?:\s+\w+)*?)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)'
    and_matches = re.findall(and_pattern, message_lower)
    
    if and_matches:
        for match in and_matches:
            title1, time1, title2, time2 = match
            
            # Parse first event
            parsed_time1 = parse_time(time1)
            if parsed_time1:
                events.append({
                    "title": clean_title(title1),
                    "date": event_date,
                    "time": parsed_time1,
                    "description": f"Event created from: {user_message}"
                })
            
            # Parse second event
            parsed_time2 = parse_time(time2)
            if parsed_time2:
                events.append({
                    "title": clean_title(title2),
                    "date": event_date,
                    "time": parsed_time2,
                    "description": f"Event created from: {user_message}"
                })
    
    # Pattern 2: Look for comma-separated events - "gym at 7am, dentist at 9am, call at 2pm"
    if not events:
        comma_pattern = r'(\w+(?:\s+\w+)*?)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)'
        comma_matches = re.findall(comma_pattern, message_lower)
        
        if len(comma_matches) > 1:
            for title, time in comma_matches:
                parsed_time = parse_time(time)
                if parsed_time:
                    events.append({
                        "title": clean_title(title),
                        "date": event_date,
                        "time": parsed_time,
                        "description": f"Event created from: {user_message}"
                    })
    
    # Pattern 3: Single event patterns
    if not events:
        single_patterns = [
            r'(?:i have|got|scheduled|planning)\s+(?:a\s+)?(\w+(?:\s+\w+)*?)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)',
            r'(\w+(?:\s+\w+)*?)\s+(?:appointment|meeting|call|session)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)',
            r'(\w+(?:\s+\w+)*?)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)',
        ]
        
        for pattern in single_patterns:
            matches = re.findall(pattern, message_lower)
            if matches:
                for match in matches:
                    if isinstance(match, tuple) and len(match) == 2:
                        title, time = match
                        parsed_time = parse_time(time)
                        if parsed_time:
                            clean_event_title = clean_title(title)
                            # Avoid duplicates
                            if not any(event['title'] == clean_event_title and event['time'] == parsed_time for event in events):
                                events.append({
                                    "title": clean_event_title,
                                    "date": event_date,
                                    "time": parsed_time,
                                    "description": f"Event created from: {user_message}"
                                })
                break  # Found matches, don't try other patterns
    
    return {"events": events} if events else {"events": []}

def parse_time(time_str):
    """Parse time string and return formatted 24-hour time"""
    import re
    
    time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', time_str.lower())
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        period = time_match.group(3)
        
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        elif not period and hour < 8:  # Assume PM for times before 8 without AM/PM
            hour += 12
            
        return f"{hour:02d}:{minute:02d}"
    return None

def clean_title(title):
    """Clean and format the event title"""
    # Remove common filler words
    title = re.sub(r'\b(i have|got|scheduled|planning|a|an|the|and|then|also)\b', '', title.lower()).strip()
    
    # Handle special cases
    title_mappings = {
        'meeting': 'Meeting',
        'lunch': 'Lunch',
        'dinner': 'Dinner',
        'gym': 'Gym workout',
        'dentist': 'Dentist appointment',
        'doctor': 'Doctor appointment',
        'call': 'Phone call',
        'conference': 'Conference',
        'appointment': 'Appointment',
    }
    
    # Check if title matches common event types
    for key, value in title_mappings.items():
        if key in title.lower():
            return value
    
    # Otherwise capitalize words
    return ' '.join(word.capitalize() for word in title.split() if word)

def get_next_weekday(current_date, weekday):
    """Get the next occurrence of a weekday (0=Monday, 6=Sunday)"""
    days_ahead = weekday - current_date.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return current_date + timedelta(days_ahead)


@ai_assistant_bp.route("/api/ai/test", methods=['POST'])
def ai_test_no_auth():
    """
    TEST ENDPOINT: AI chat without authentication (for debugging)
    Remove this in production!
    """
    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        # Use your actual user ID from the database
        actual_user_id = "8620b861-ea55-478a-b1b4-f266cb6a999d"  # rakesh user
        
        print(f"[DEBUG] Testing message: '{user_message}' for user: {actual_user_id}")
        
        # Test both creation and deletion
        result = detect_and_create_events(user_message, actual_user_id)
        
        if isinstance(result, tuple):
            success, message = result
            
            response_data = {
                "success": success,
                "message": message,
                "user_message": user_message,
                "user_id": actual_user_id,
                "test_mode": True,
                "timestamp": datetime.now(IST).isoformat()
            }
            
            if success:
                # Check if it was deletion or creation
                if "deleted" in message.lower():
                    response_data["action"] = "deletion"
                    response_data["events_deleted"] = message
                elif "created" in message.lower() or "event" in message.lower():
                    response_data["action"] = "creation" 
                    response_data["events_created"] = message
            
            return jsonify(response_data)
        else:
            return jsonify({
                "success": True,
                "message": "Events processed",
                "events_created": result,
                "user_message": user_message,
                "user_id": actual_user_id,
                "test_mode": True
            })

    except Exception as e:
        print(f"An error occurred in ai_test_no_auth: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Debug error: {str(e)}"}), 500


# --- HELPER FUNCTION TO GET SCHEDULE ---
def _get_user_schedule(user_id):
    """Fetches all the user's upcoming events from the database."""
    conn = get_db_connection()
    if not conn:
        return "Database connection failed."
    
    try:
        cursor = conn.cursor(dictionary=True)
        # Get all events from today onwards
        today = datetime.now(IST).strftime('%Y-%m-%d')
        
        query = "SELECT title, date, time FROM events WHERE user_id = %s AND date >= %s AND done = FALSE ORDER BY date, time"
        cursor.execute(query, (user_id, today))
        events = cursor.fetchall()
        
        if not events:
            return "The user's schedule is currently clear."
            
        # Format the events into a clean string for the AI
        schedule_string = "Here is the user's complete schedule:\n"
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
def ai_chat_automatic():
    """
    Enhanced AI chat with AUTOMATIC multiple event detection and creation.
    This route processes messages and automatically creates calendar events when detected.
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    user_message = request.json.get("message")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        # Check if user is responding to a conflict warning
        if user_message.lower().strip() in ['yes', 'y', 'confirm', 'ok']:
            # Check if there's a pending event in session
            pending_event = session.get('pending_event_with_conflict')
            if pending_event:
                # Create the event despite conflict
                if create_event_in_db(user_id, pending_event):
                    session.pop('pending_event_with_conflict', None)  # Clear pending event
                    return jsonify({
                        "reply": f"✅ Event '{pending_event['title']}' created successfully despite the conflict!",
                        "events_created": True
                    })
                else:
                    return jsonify({
                        "reply": "❌ Sorry, there was an error creating the event. Please try again.",
                        "events_created": False
                    })
        
        if user_message.lower().strip() in ['no', 'n', 'cancel', 'nevermind']:
            # Check if there's a pending event in session
            pending_event = session.get('pending_event_with_conflict')
            if pending_event:
                session.pop('pending_event_with_conflict', None)  # Clear pending event
                return jsonify({
                    "reply": f"✅ Cancelled creating '{pending_event['title']}'. No event was added.",
                    "events_created": False
                })
        
        # 1. FIRST: Check for automatic event creation (including multiple events)
        event_created, creation_message = detect_and_create_events(user_message, user_id)
        
        # Handle conflict warnings
        if not event_created and "SCHEDULING CONFLICT DETECTED" in creation_message:
            # This is a conflict warning - we need to store the pending event for user confirmation
            # For now, just return the conflict message
            return jsonify({
                "reply": creation_message,
                "events_created": False,
                "conflict_detected": True
            })
        
        # 2. Get updated schedule after potential event creation
        schedule_context = _get_user_schedule(user_id)
        
        # 3. Prepare chat history
        history = session.get('chat_history', [])
        history.append({'role': 'user', 'parts': [{'text': user_message}]})

        # 4. Create enhanced system prompt
        system_prompt = f"""
        You are Scout, a friendly and professional AI assistant integrated into the HelpScout application.
        Your goal is to help users organize their work, plan tasks, and manage schedules effectively.
        
        IMPORTANT: You have AUTOMATIC event detection enabled. When users mention events naturally in conversation 
        (like "I have a meeting at 10am and lunch at 1pm tomorrow"), you automatically create them in their calendar.
        
        - Be concise, encouraging, and clear in your responses.
        - When asked to generate lists, always use markdown bullet points.
        - Use the current date of {datetime.now(IST).strftime('%A, %Y-%m-%d')} for any time-related questions.
        - You can handle multiple events in a single message automatically.

        ---
        CURRENT SCHEDULE:
        {schedule_context}
        ---
        """
        
        # 5. Generate AI response with 3-tier fallback (Groq first since it's working)
        ai_response_text = None
        
        # Try Gemini first (primary AI)
        if api_key:
            try:
                model = genai.GenerativeModel('gemini-1.5-pro')
                chat = model.start_chat(history=history)
                response = chat.send_message(user_message)
                ai_response_text = response.text
                print("✓ Used Gemini API for chat response")
            except Exception as e:
                print(f"Gemini API failed: {e}")
        
        # Fallback to Cohere if Gemini fails
        if not ai_response_text and co:
            try:
                # Prepare chat history for Cohere
                cohere_messages = []
                for msg in history:
                    if msg['role'] == 'user':
                        cohere_messages.append({"role": "user", "content": msg['parts'][0]['text']})
                    elif msg['role'] == 'model':
                        cohere_messages.append({"role": "assistant", "content": msg['parts'][0]['text']})
                
                response = co.chat(
                    model='command-a-03-2025',
                    message=f"{system_prompt}\n\nUser: {user_message}\n\nAssistant:",
                    max_tokens=1000,
                    temperature=0.3
                )
                if hasattr(response, 'text'):
                    ai_response_text = response.text
                else:
                    ai_response_text = str(response)
                print("✓ Used Cohere API as fallback for chat response")
            except Exception as e:
                print(f"Cohere API failed: {e}")
        
        # Final fallback to Groq if both fail
        if not ai_response_text and groq_client:
            try:
                # Convert history to Groq format
                groq_messages = [{"role": "system", "content": system_prompt}]
                for msg in history:
                    if msg['role'] == 'user':
                        groq_messages.append({"role": "user", "content": msg['parts'][0]['text']})
                    elif msg['role'] == 'model':
                        groq_messages.append({"role": "assistant", "content": msg['parts'][0]['text']})
                
                chat_completion = groq_client.chat.completions.create(
                    messages=groq_messages,
                    model="llama-3.1-8b-instant",  # Using the working model
                    temperature=0.3,
                    max_tokens=1000
                )
                ai_response_text = chat_completion.choices[0].message.content
                print("✓ Used Groq API as final fallback for chat response")
            except Exception as e:
                print(f"Groq API failed: {e}")
                try:
                    # Try Cohere as final fallback
                    if cohere_api_key:
                        co_fallback = cohere.Client(cohere_api_key)
                        response = co_fallback.chat(
                            message=f"{system_prompt}\n\nUser: {user_message}",
                            model="command-a-03-2025",
                            temperature=0.3
                        )
                        if hasattr(response, 'text'):
                            ai_response_text = response.text.strip()
                        else:
                            ai_response_text = str(response).strip()
                        print("✓ Used Cohere API as final fallback for chat response")
                except Exception as e:
                    print(f"Cohere API failed: {e}")
        
        # If all APIs failed
        if not ai_response_text:
            return jsonify({"error": "All AI services are currently unavailable. Please try again later."}), 503

        # 6. Add event creation confirmation to response if events were created
        if event_created:
            ai_response_text = f"✅ {creation_message}\n\n{ai_response_text}"

        # 7. Update chat history
        history.append({'role': 'model', 'parts': [{'text': ai_response_text}]})
        session['chat_history'] = history
        session.modified = True

        return jsonify({
            "reply": ai_response_text,
            "events_created": event_created,
            "creation_message": creation_message if event_created else None
        })

    except Exception as e:
        print(f"An error occurred in ai_chat_automatic: {e}")
        return jsonify({"error": "An error occurred while processing your message."}), 500