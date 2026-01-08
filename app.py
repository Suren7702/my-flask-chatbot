import json
import random
import os
from datetime import datetime

import mysql.connector
import pyrebase
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from thefuzz import fuzz

# --- 1. Configurations ---
app = Flask(__name__)
app.static_folder = 'static'
# Flask Secret Key
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'cairocoders-ednalan')

# Firebase Configuration
firebase_config = {
    "apiKey": os.environ.get("FIREBASE_API_KEY", "AIzaSyAxTQTF_Gfh30xKF337pzfChFRM2IrP-Fs"),
    "authDomain": "pythonfacedetection-189b4.firebaseapp.com",
    "databaseURL": "https://pythonfacedetection-189b4-default-rtdb.firebaseio.com/",
    "projectId": "pythonfacedetection-189b4",
    "storageBucket": "pythonfacedetection-189b4.firebasestorage.app",
    "messagingSenderId": "459493321741",
    "appId": "1:459493321741:web:3b2ec7ea6a9ecbf952f944"
}

# --- Database Connection Logic ---
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'mysql-2987be86-my-flask-chatbot.f.aivencloud.com'),
        port=os.environ.get('DB_PORT', '16405'),
        user=os.environ.get('DB_USER', 'avnadmin'),
        password=os.environ.get('DB_PASSWORD'), 
        database=os.environ.get('DB_NAME', 'defaultdb'),
        ssl_disabled=False # Ithu Aiven SSL logic-ku help pannum
    )

def create_tables_on_startup():
    """Live DB-la tables illana auto-va create panna."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        tables = [
            """CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                roll_or_id VARCHAR(50) NOT NULL UNIQUE,
                name VARCHAR(100) NOT NULL,
                age INT,
                department_or_class VARCHAR(100),
                email VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS staff (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS faculty (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            )"""
        ]
        for table in tables:
            cursor.execute(table)
            
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Database Tables synchronized successfully!")
    except Exception as e:
        print(f"❌ Startup DB Error: {e}")

# IMPORTANT: Call this before routes
create_tables_on_startup()

STOP_WORDS = {"is", "the", "a", "an", "please", "can", "you", "tell", "me", "what", "of", "about"}

# --- 2. Initializations ---
firebase = pyrebase.initialize_app(firebase_config)
firebase_db = firebase.database()

# --- 3. Helper Functions ---
def clean_input(text):
    words = text.lower().split()
    filtered_words = [w for w in words if w not in STOP_WORDS]
    return " ".join(filtered_words)

def get_attendance_data(roll_number=None, date=None):
    try:
        if roll_number:
            attendance_data = firebase_db.child("Attendance").order_by_child("Roll_No").equal_to(roll_number).get()
        elif date:
            attendance_data = firebase_db.child("Attendance").order_by_child("Date").equal_to(date).get()
        else:
            attendance_data = firebase_db.child("Attendance").get()

        if attendance_data and attendance_data.each():
            response = ""
            for entry in attendance_data.each():
                att = entry.val()
                response += f"Roll No: {att['Roll_No']}, Name: {att['Name']}, Time: {att['Time']}<br>"
            return response
    except:
        pass
    return "No attendance data found."

def get_intents():
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base_path, 'intents.json')) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"intents": []}

def match_intent(user_input):
    cleaned_text = clean_input(user_input)
    intents_data = get_intents().get('intents', [])
    best_match, highest_score = None, 0
    
    for intent in intents_data:
        for pattern in intent['patterns']:
            score = fuzz.partial_ratio(pattern.lower(), cleaned_text)
            if score > highest_score:
                highest_score, best_match = score, intent
    return best_match if highest_score >= 70 else None

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

# --- 5. Routes: Logic (Registration & Login) ---
@app.route('/submit', methods=['POST'])
def submit():
    """Handles User Registration."""
    name = request.form.get('name')
    email = request.form.get('email', '').strip()
    password = generate_password_hash(request.form.get('password'))
    roll_or_id = request.form.get('roll_or_id')
    user_type = request.form.get('user_type')

    table_map = {"Student": "students", "Staff": "staff", "Faculty": "faculty"}
    target_table = table_map.get(user_type)

    if not target_table:
        flash("Invalid user type.", "error")
        return redirect(url_for('register'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = f"INSERT INTO {target_table} (name, email, password, roll_or_id) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (name, email, password, roll_or_id))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Registration Successful! Please Login.", "success")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Registration Error: {e}", "error")
        return redirect(url_for('register'))

@app.route('/login_validation', methods=['POST'])
def login_validation():
    email = request.form.get('email', '').strip()
    password = request.form.get('password')
    user_type = request.form.get('user_type')

    table_map = {"Student": "students", "Staff": "staff", "Faculty": "faculty"}
    target_table = table_map.get(user_type)

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
            session['user_type'] = user_type
            flash(f"Welcome {user_type}!", "success")
            return redirect(url_for('chat'))
        else:
            flash("Invalid credentials.", "error")
    except Exception as e:
        flash(f"Database Error: {e}", "error")
    
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- 6. Routes: Chat Logic ---
@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form.get('message', '').lower()
    user_email = session.get('user_email')

    # Profile Context
    if any(x in user_input for x in ["my details", "who am i", "profile"]):
        if user_email:
            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT roll_or_id, name, department_or_class FROM students WHERE email = %s", (user_email,))
                res = cursor.fetchone()
                cursor.close()
                conn.close()
                if res:
                    return jsonify({'response': f"👤 <b>Name:</b> {res['name']}<br>🆔 <b>ID:</b> {res['roll_or_id']}<br>🏫 <b>Class:</b> {res['department_or_class']}"})
            except: pass
        return jsonify({'response': "I couldn't fetch your profile details."})

    # Student Inquiry
    if user_input.startswith('student'):
        try:
            rid = [int(s) for s in user_input.split() if s.isdigit()][0]
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT roll_or_id, name, department_or_class FROM students WHERE roll_or_id = %s", (rid,))
            res = cursor.fetchone()
            cursor.close()
            conn.close()
            if res:
                return jsonify({'response': f"🆔 <b>ID:</b> {res['roll_or_id']}<br>👤 <b>Name:</b> {res['name']}<br>🏫 <b>Class:</b> {res['department_or_class']}"})
            return jsonify({'response': "Student not found."})
        except:
            return jsonify({'response': "Please provide a valid ID (e.g., student 101)."})

    # Attendance
    elif "attendance" in user_input:
        if "today" in user_input:
            response = get_attendance_data(date=datetime.now().strftime("%Y-%m-%d"))
        else:
            try:
                roll = [int(s) for s in user_input.split() if s.isdigit()][0]
                response = get_attendance_data(roll_number=roll)
            except:
                response = "Please provide an ID for attendance."
        return jsonify({'response': response})

    # Intent Matching
    intent = match_intent(user_input)
    response = random.choice(intent['responses']) if intent else "I'm not sure about that. Try asking about admissions or your profile."
    return jsonify({'response': response})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)