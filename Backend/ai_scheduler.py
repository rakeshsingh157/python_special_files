import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
import re
import requests
from datetime import datetime, timedelta
import cohere

load_dotenv()

class AIScheduler:
    def __init__(self):
        # Gemini API setup
        self.google_gemini_api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        if self.google_gemini_api_key:
            try:
                genai.configure(api_key=self.google_gemini_api_key)
                print("Gemini API configured successfully")
            except Exception as e:
                print(f"Gemini API configuration failed: {e}")
                self.google_gemini_api_key = None
        
        # Groq API setup (third fallback)
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_base_url = "https://api.groq.com/openai/v1"
        self.groq_model = "meta-llama/llama-4-scout-17b-16e-instruct"  # Working fast model
        
        # Cohere API setup (second fallback)
        self.cohere_api_key = os.getenv("COHERE_API_KEY")
        if self.cohere_api_key:
            self.co = cohere.ClientV2(self.cohere_api_key)
            self.cohere_model = "command-r-plus-08-2024"  # Latest Cohere model
        else:
            self.co = None
        
        if not self.google_gemini_api_key and not self.cohere_api_key and not self.groq_api_key:
            print("Warning: No AI API keys found in environment variables")
        else:
            print(f"AIScheduler initialized - Gemini: {'✓' if self.google_gemini_api_key else '✗'}, Cohere: {'✓' if self.cohere_api_key else '✗'}, Groq: {'✓' if self.groq_api_key else '✗'}")
    
    def _call_groq_api(self, prompt):
        """Fallback function to call Groq API when Gemini fails."""
        if not self.groq_api_key:
            raise Exception("Groq API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.groq_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1500,
            "stream": False
        }
        
        try:
            response = requests.post(f"{self.groq_base_url}/chat/completions", 
                                   headers=headers, 
                                   json=data,
                                   timeout=60)  # Increased timeout to 60 seconds
            
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            else:
                raise Exception("No valid response from Groq API")
                
        except requests.exceptions.Timeout:
            raise Exception("Groq API request timed out after 60 seconds")
        except requests.exceptions.ConnectionError:
            raise Exception("Failed to connect to Groq API")
        except Exception as e:
            raise Exception(f"Groq API request failed: {str(e)}")
    
    def _call_cohere_api(self, prompt):
        """Second fallback function to call Cohere API when Gemini fails."""
        if not self.cohere_api_key or not self.co:
            raise Exception("Cohere API key not configured")
        
        try:
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            response = self.co.chat(
                model=self.cohere_model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            # Extract content from Cohere response
            if hasattr(response, 'message') and hasattr(response.message, 'content'):
                if isinstance(response.message.content, list):
                    # Handle list of content objects
                    return ''.join([item.text for item in response.message.content if hasattr(item, 'text')])
                else:
                    return str(response.message.content)
            else:
                raise Exception("No valid response from Cohere API")
                
        except Exception as e:
            if "rate limit" in str(e).lower():
                raise Exception("Cohere API rate limit exceeded - please try again later")
            elif "auth" in str(e).lower() or "unauthorized" in str(e).lower():
                raise Exception("Cohere API authentication failed - check API key")
            else:
                raise Exception(f"Cohere API request failed: {str(e)}")
    
    def generate_tasks(self, user_input):
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        prompt = f"""
        Analyze the following user input and generate a list of tasks with specific details.
        Current Time: {current_datetime}
        The user said: "{user_input}"
        
        Return ONLY a JSON array with tasks in this exact format:
        [
            {{
                "title": "Task title",
                "description": "Generate a helpful, detailed description that includes context, purpose, or actionable details. Make it useful for the user when they see this task later.",
                "category": "Choose from: work, home, sports, fun, health, fitness, personal, learning, finance, errands, cleaning, gardening, cooking, pets, meeting, commute, networking, admin, social, entertainment, travel, hobby, volunteering, important, to-do, later, family",
                "date": "YYYY-MM-DD",
                "time": "HH:MM",
                "reminder_setting": "15 minutes"
            }}
        ]
        
        CATEGORY GUIDELINES:
        - "meeting" for meetings, calls, appointments
        - "health" for doctor, dentist, medical appointments  
        - "fitness" for gym, workout, sports activities
        - "errands" for shopping, banking, errands
        - "work" for work-related tasks
        - "family" for family events and activities
        - "personal" for general personal tasks
        - "learning" for education, courses, studying
        - "finance" for financial tasks, budgeting
        - "entertainment" for movies, games, fun activities
        
        IMPORTANT FOR DESCRIPTIONS:
        - Create meaningful, context-aware descriptions that add value
        - Include purpose, preparation steps, or important details
        - Make descriptions actionable and informative
        - Examples of good descriptions:
          * For "Buy groceries" → "Weekly grocery shopping - check pantry, review meal plan, don't forget fruits and vegetables"
          * For "Call dentist" → "Schedule 6-month dental checkup and cleaning appointment"
          * For "Meeting prep" → "Prepare presentation slides and review agenda items for tomorrow's client meeting"
          * For "Workout" → "45-minute cardio and strength training session - bring water bottle and towel"
        
        Rules:
        1. Extract or infer dates and times from the input
        2. If no specific date is mentioned, use today's date: {datetime.now().strftime('%Y-%m-%d')}
        3. If no specific time is mentioned, use a reasonable time like "09:00"
        4. Choose the most appropriate category from the allowed list
        5. Generate at least 1 task and at most 5 tasks
        6. Use "reminder_setting" field with values like "15 minutes", "30 minutes", "1 hour", "2 hours", or "1 day"
        7. Always create helpful, detailed descriptions that provide context and actionable information
        """
        
        response_text = None
        api_used = "gemini"
        
        # Try Gemini first, then Cohere, then Groq as fallbacks
        try:
            if not self.google_gemini_api_key:
                raise Exception("Gemini API key not configured")
            
            # Use faster model to conserve quota
            model = genai.GenerativeModel('gemini-2.0-flash')  # Faster, more quota-friendly
            response = model.generate_content(prompt)
            response_text = response.text
            print("Successfully used Gemini API for task generation")
            
        except Exception as gemini_error:
            print(f"Gemini API failed: {gemini_error}")
            api_used = "cohere"
            
            # Fallback to Cohere API
            try:
                if not self.cohere_api_key:
                    raise Exception("Cohere API key not configured")
                
                response_text = self._call_cohere_api(prompt)
                print("Successfully used Cohere API as fallback for task generation")
                
            except Exception as cohere_error:
                print(f"Cohere API failed: {cohere_error}")
                api_used = "groq"
                
                # Second fallback to Groq API
                try:
                    if not self.groq_api_key:
                        raise Exception("Groq API key not configured")
                    
                    response_text = self._call_groq_api(prompt)
                    print("Successfully used Groq API as second fallback for task generation")
                    
                except Exception as groq_error:
                    print(f"All APIs failed. Gemini: {gemini_error}, Cohere: {cohere_error}, Groq: {groq_error}")
                    # Return a default task if all APIs fail
                    return [{
                        "title": "Complete your task",
                        "description": user_input,
                        "category": "personal",
                        "date": datetime.now().strftime('%Y-%m-%d'),
                        "time": "09:00",
                        "reminder_setting": "15 minutes"
                    }]
        
        # Extract JSON from response
        try:
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            
            if json_match:
                tasks_json = json_match.group(0)
                tasks = json.loads(tasks_json)
                
                # Ensure each task has the reminder_setting field
                for task in tasks:
                    if 'reminder_setting' not in task:
                        task['reminder_setting'] = '15 minutes'
                    # Also ensure compatibility with old 'reminder' field
                    if 'reminder' not in task and 'reminder_setting' in task:
                        task['reminder'] = task['reminder_setting']
                        
                return tasks
            else:
                # Fallback if JSON parsing fails
                return [{
                    "title": "Complete your task",
                    "description": user_input,
                    "category": "personal",
                    "date": datetime.now().strftime('%Y-%m-%d'),
                    "time": "09:00",
                    "reminder_setting": "15 minutes"
                }]
                
        except Exception as parse_error:
            print(f"Error parsing JSON response: {parse_error}")
            # Return a default task if JSON parsing fails
            return [{
                "title": "Complete your task",
                "description": user_input,
                "category": "personal",
                "date": datetime.now().strftime('%Y-%m-%d'),
                "time": "09:00",
                "reminder": "15 minutes"
            }]