import json
import random
from datetime import datetime

import mysql.connector
import pyrebase
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from thefuzz import fuzz # New import for accuracy

# --- 1. Configurations ---
app = Flask(__name__)
app.static_folder = 'static'
app.config['SECRET_KEY'] = 'cairocoders-ednalan'

#
firebase_config = {
    "apiKey": "AIzaSyAxTQTF_Gfh30xKF337pzfChFRM2IrP-Fs",
    "authDomain": "pythonfacedetection-189b4.firebaseapp.com",
    "databaseURL": "https://pythonfacedetection-189b4-default-rtdb.firebaseio.com/",
    "projectId": "pythonfacedetection-189b4",
    "storageBucket": "pythonfacedetection-189b4.firebasestorage.app",
    "messagingSenderId": "459493321741",
    "appId": "1:459493321741:web:3b2ec7ea6a9ecbf952f944",
    "measurementId": "G-QDBB3PQMCP"
}

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'school'
}

# Common stop words for basic NLP cleaning
STOP_WORDS = {"is", "the", "a", "an", "please", "can", "you", "tell", "me", "what", "of", "about"}

# --- 2. Initializations ---
firebase = pyrebase.initialize_app(firebase_config)
db = firebase.database()

# --- 3. Helper Functions ---
def get_db_connection():
    return mysql.connector.connect(**db_config)

def clean_input(text):
    """NLP: Focuses on keywords by removing stop words."""
    words = text.lower().split()
    filtered_words = [w for w in words if w not in STOP_WORDS]
    return " ".join(filtered_words)

def get_attendance_data(roll_number=None, date=None):
    attendance_data = None
    if roll_number:
        attendance_data = db.child("Attendance").order_by_child("Roll_No").equal_to(roll_number).get()
    elif date:
        attendance_data = db.child("Attendance").order_by_child("Date").equal_to(date).get()
    else:
        attendance_data = db.child("Attendance").get()

    if attendance_data and attendance_data.each():
        response = ""
        for entry in attendance_data.each():
            attendance = entry.val()
            response += f"Roll No: {attendance['Roll_No']}, Name: {attendance['Name']}, Time: {attendance['Time']}<br>"
        return response
    return "No attendance data found."

def get_intents():
    try:
        with open('intents.json') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"intents": []}

def match_intent(user_input):
    """Fuzzy Matching + NLP Cleaning for improved intent detection."""
    cleaned_text = clean_input(user_input)
    intents = get_intents().get('intents', [])
    best_match = None
    highest_score = 0
    threshold = 70  # sensitivity level

    for intent in intents:
        for pattern in intent['patterns']:
            # Uses partial_ratio to handle typos and patterns buried in sentences
            score = fuzz.partial_ratio(pattern.lower(), cleaned_text)
            if score > highest_score:
                highest_score = score
                best_match = intent

    return best_match if highest_score >= threshold else None

# --- 4. Routes: Views ---
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/chat')
def chat():
    if 'user_email' not in session:
        flash("Please login first!", "error")
        return redirect(url_for('index'))
    return render_template('chat.html')

@app.route('/register')
def register():
    return render_template('form.html')

# --- 5. Routes: Auth Logic ---
@app.route('/login_validation', methods=['POST'])
def login_validation():
    email = request.form.get('email', '').strip()
    password = request.form.get('password')
    user_type = request.form.get('user_type')

    table_map = {"Student": "students", "Staff": "staff", "Faculty": "faculty"}
    target_table = table_map.get(user_type)

    if not target_table:
        flash("Please select a valid User Type.", "error")
        return redirect(url_for('index'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = f"SELECT email, password FROM {target_table} WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user[1], password):
            session['user_email'] = email
            session['user_type'] = user_type # Save user type for context awareness
            flash(f"Logged in as {user_type}!", "success")
            return redirect(url_for('chat'))
        else:
            flash("Invalid email or password.", "error")
    except Exception as e:
        flash(f"Database Error: {e}", "error")
    
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('index'))

# --- 6. Routes: Chat Logic ---
@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form.get('message', '').lower()
    user_email = session.get('user_email') #

    # 1. Handle "My Profile" (Context Awareness)
    if "my details" in user_input or "who am i" in user_input:
        if user_email:
            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                # Fetches data automatically based on the logged-in email
                query = f"SELECT roll_or_id, name, department_or_class FROM students WHERE email = %s"
                cursor.execute(query, (user_email,))
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                if result:
                    return jsonify({'response': f"👤 <b>Name:</b> {result['name']}<br>🆔 <b>ID:</b> {result['roll_or_id']}<br>🏫 <b>Class:</b> {result['department_or_class']}"})
                return jsonify({'response': "I couldn't find your profile in the student database."})
            except Exception as e:
                return jsonify({'response': f"Database Error: {e}"})

    # 2. Database Queries (Specific Student Info)
    if user_input.startswith('student'):
        try:
            roll_number = [int(s) for s in user_input.split() if s.isdigit()][0] # Extracts ID
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            query = "SELECT roll_or_id, name, age, department_or_class, email FROM students WHERE roll_or_id = %s"
            cursor.execute(query, (roll_number,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            if result:
                response = f"🆔 <b>ID:</b> {result['roll_or_id']}<br>👤 <b>Name:</b> {result['name']}<br>🏫 <b>Class:</b> {result['department_or_class']}"
            else:
                response = "⚠️ Student not found."
        except:
            response = "Please provide a valid student ID (e.g., 'student 123')."

    # 3. Attendance Logic
    elif "attendance" in user_input:
        if "today" in user_input:
            response = get_attendance_data(date=datetime.now().strftime("%Y-%m-%d"))
        else:
            try:
                roll = [int(s) for s in user_input.split() if s.isdigit()][0]
                response = get_attendance_data(roll_number=roll)
            except:
                response = "Please provide an ID for attendance check."

    # 4. Fuzzy Intent Matching (accuracy increased)
    else:
        intent = match_intent(user_input)
        if intent:
            response = random.choice(intent['responses'])
        else:
            response = "I'm not quite sure. You can ask about admissions, fees, or say 'Show my details'."

    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True)