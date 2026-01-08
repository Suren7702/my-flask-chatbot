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
# Render-la deploy pannum pothu intha secret key-ah environment variable-la vai
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'cairocoders-ednalan')

# Firebase Config (Better to use Env Variables for these too)
firebase_config = {
    "apiKey": os.environ.get("FIREBASE_API_KEY", "AIzaSyAxTQTF_Gfh30xKF337pzfChFRM2IrP-Fs"),
    "authDomain": "pythonfacedetection-189b4.firebaseapp.com",
    "databaseURL": "https://pythonfacedetection-189b4-default-rtdb.firebaseio.com/",
    "projectId": "pythonfacedetection-189b4",
    "storageBucket": "pythonfacedetection-189b4.firebasestorage.app",
    "messagingSenderId": "459493321741",
    "appId": "1:459493321741:web:3b2ec7ea6a9ecbf952f944"
}


def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'mysql-2987be86-my-flask-chatbot.f.aivencloud.com'),
        port=os.environ.get('DB_PORT', '16405'),
        user=os.environ.get('DB_USER', 'avnadmin'),
        password=os.environ.get('DB_PASSWORD', 'AVNS_x6TxPLEDV1fg320VVrY'), # Inga Aiven password podu
        database=os.environ.get('DB_NAME', 'defaultdb'),
        ssl_disabled=False # Aiven requires SSL usually
    )
# app.py-la connection-ku kila ithai podu
def create_tables():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Students Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                roll_or_id VARCHAR(50) NOT NULL UNIQUE,
                name VARCHAR(100) NOT NULL,
                age INT,
                department_or_class VARCHAR(100),
                email VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            )
        """)
        
        # Staff Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS staff (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Tables checked/created successfully!")
    except Exception as e:
        print(f"Error creating tables: {e}")

# App start aagum pothu ithai call pannu
create_tables()
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
    attendance_data = None
    # Changed 'db' to 'firebase_db' to avoid confusion with mysql db
    if roll_number:
        attendance_data = firebase_db.child("Attendance").order_by_child("Roll_No").equal_to(roll_number).get()
    elif date:
        attendance_data = firebase_db.child("Attendance").order_by_child("Date").equal_to(date).get()
    else:
        attendance_data = firebase_db.child("Attendance").get()

    if attendance_data and attendance_data.each():
        response = ""
        for entry in attendance_data.each():
            attendance = entry.val()
            response += f"Roll No: {attendance['Roll_No']}, Name: {attendance['Name']}, Time: {attendance['Time']}<br>"
        return response
    return "No attendance data found."

def get_intents():
    try:
        # Render-la file path correct-ah irukanum
        base_path = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base_path, 'intents.json')) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"intents": []}

def match_intent(user_input):
    cleaned_text = clean_input(user_input)
    intents_data = get_intents().get('intents', [])
    best_match = None
    highest_score = 0
    threshold = 70

    for intent in intents_data:
        for pattern in intent['patterns']:
            score = fuzz.partial_ratio(pattern.lower(), cleaned_text)
            if score > highest_score:
                highest_score = score
                best_match = intent

    return best_match if highest_score >= threshold else None

# --- 4. Routes ---
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
            session['user_type'] = user_type
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

@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form.get('message', '').lower()
    user_email = session.get('user_email')

    if "my details" in user_input or "who am i" in user_input:
        if user_email:
            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                query = "SELECT roll_or_id, name, department_or_class FROM students WHERE email = %s"
                cursor.execute(query, (user_email,))
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                if result:
                    return jsonify({'response': f"👤 <b>Name:</b> {result['name']}<br>🆔 <b>ID:</b> {result['roll_or_id']}<br>🏫 <b>Class:</b> {result['department_or_class']}"})
                return jsonify({'response': "I couldn't find your profile in the student database."})
            except Exception as e:
                return jsonify({'response': f"Database Error: {e}"})

    if user_input.startswith('student'):
        try:
            roll_number = [int(s) for s in user_input.split() if s.isdigit()][0]
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

    elif "attendance" in user_input:
        if "today" in user_input:
            response = get_attendance_data(date=datetime.now().strftime("%Y-%m-%d"))
        else:
            try:
                roll = [int(s) for s in user_input.split() if s.isdigit()][0]
                response = get_attendance_data(roll_number=roll)
            except:
                response = "Please provide an ID for attendance check."

    else:
        intent = match_intent(user_input)
        if intent:
            response = random.choice(intent['responses'])
        else:
            response = "I'm not quite sure. You can ask about admissions, fees, or say 'Show my details'."

    return jsonify({'response': response})

if __name__ == '__main__':
    # Live deployment-la port environment variable-la irunthu varanum
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)