import os
import PyPDF2
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import mysql.connector
from services.graph_query import ask_edugen
from services.ai_tools import optimize_resume, analyze_skills
from services.mock_interview import generate_interview_panel
from services.job_analyzer import generate_fit_analysis
from datetime import datetime
from neo4j import GraphDatabase
from services.job_analyzer import cloud_llm


# LOAD THE HIDDEN SAFE (.env file)
load_dotenv()

app = Flask(__name__)

# --- CONFIGURATION ---
# Allow all origins to prevent browser CORS blocking
CORS(app, resources={r"/*": {"origins": "*"}})

# EMAIL CONFIGURATION (Now pulling from .env)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)

# --- NEO4J CLOUD CONFIGURATION ---
NEO4J_URI = os.getenv('NEO4J_URI')
NEO4J_USER = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')

# Initialize the secure cloud driver
try:
    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    print("✅ Successfully connected to Neo4j Cloud Database!")
except Exception as e:
    print(f"❌ Failed to connect to Neo4j: {e}")

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# DATABASE CONFIGURATION
db_config = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD') or '', 
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_NAME')
}

def get_db_connection():
    return mysql.connector.connect(**db_config)



def extract_text_from_cv(file):
    """Extracts text from an uploaded PDF or TXT file."""
    text = ""
    try:
        if file.filename.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        elif file.filename.endswith('.txt'):
            text = file.read().decode('utf-8')
    except Exception as e:
        print(f"Error reading file: {e}")
    return text


# --- AUTH ROUTES ---

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password') 
    role = 'user' 

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"success": False, "message": "Email already registered"}), 400

        query = "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (name, email, password, role))
        conn.commit()
        return jsonify({"success": True, "message": "Registration successful!"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'user') 

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        query = "SELECT * FROM users WHERE email = %s AND password = %s AND role = %s"
        cursor.execute(query, (email, password, role))
        user = cursor.fetchone()

        if user:
            return jsonify({
                "success": True,
                "message": "Login successful",
                "user": {
                    "id": user['id'],
                    "name": user['name'],
                    "email": user['email'],
                    "role": user['role']
                }
            })
        else:
            return jsonify({"success": False, "message": "Invalid credentials or wrong role selected."}), 401
            
    finally:
        cursor.close()
        conn.close()

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    email = data.get('email')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            token = serializer.dumps(email, salt='password-reset-salt')
            link = f"http://localhost/EduGEN_full/frontend/reset-password.html?token={token}"
            
            msg = Message("Reset Your Password - EduGEN", recipients=[email])
            msg.body = f"Hello {user['name']},\n\nClick here to reset: {link}"
            mail.send(msg)

            return jsonify({"success": True, "message": "Reset link sent!"})
        else:
            return jsonify({"success": False, "message": "Email not found."}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/reset-password-confirm', methods=['POST'])
def reset_password_confirm():
    data = request.json
    token = data.get('token')
    new_password = data.get('new_password')

    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=1800)
    except:
        return jsonify({"success": False, "message": "Invalid or expired token."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET password = %s WHERE email = %s", (new_password, email))
        conn.commit()
        return jsonify({"success": True, "message": "Password updated!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# --- ADMIN ROUTES ---

@app.route('/admin/users', methods=['GET'])
def get_all_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name, email, role, created_at FROM users ORDER BY id DESC")
        users = cursor.fetchall()
        return jsonify({"users": users})
    except Exception as e:
        print("Error fetching users:", e)
        return jsonify({"users": []}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return jsonify({"success": True, "message": "User deleted"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

        # --- ADMIN: MANAGE DATASETS (JOB MARKET) ---

@app.route('/api/admin/jobs', methods=['GET', 'OPTIONS'])
def get_all_market_jobs():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM job_market ORDER BY created_at DESC")
        jobs = cursor.fetchall()
        return jsonify({"success": True, "jobs": jobs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/admin/jobs', methods=['POST', 'OPTIONS'])
def add_market_job():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    data = request.json
    title = data.get('title')
    cluster = data.get('cluster')
    level = data.get('level')
    location = data.get('location')
    tags = data.get('tags') # Expecting a comma-separated string like "Java, Spring, SQL"

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = "INSERT INTO job_market (title, cluster, level, location, tags) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql, (title, cluster, level, location, tags))
        conn.commit()
        return jsonify({"success": True, "message": "Job added to the database!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/admin/jobs/<int:job_id>', methods=['DELETE', 'OPTIONS'])
def delete_market_job(job_id):
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM job_market WHERE id = %s", (job_id,))
        conn.commit()
        return jsonify({"success": True, "message": "Job deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


        # --- ADMIN: NEO4J GRAPH DATA (REAL CLOUD DATA) ---
@app.route('/api/admin/graph_data', methods=['GET', 'OPTIONS'])
def get_graph_data():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    try:
        # Open a session with your Cloud Database
        with neo4j_driver.session() as session:
            # Grabs 50 relationships from your live GraphRAG database
            result = session.run("MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50")
            
            nodes = []
            edges = []
            node_ids = set()

            for record in result:
                n = record["n"]
                m = record["m"]
                r = record["r"]

                # Process Source Node
                if n.element_id not in node_ids:
                    label = list(n.labels)[0] if n.labels else "Unknown"
                    # THE FIX: Tell it to look for 'id' first!
                    name = n.get("id", n.get("name", n.get("title", "Unnamed")))
                    nodes.append({"id": n.element_id, "label": name, "group": label.lower()})
                    node_ids.add(n.element_id)

                # Process Target Node
                if m.element_id not in node_ids:
                    label = list(m.labels)[0] if m.labels else "Unknown"
                    # THE FIX: Tell it to look for 'id' first!
                    name = m.get("id", m.get("name", m.get("title", "Unnamed")))
                    nodes.append({"id": m.element_id, "label": name, "group": label.lower()})
                    node_ids.add(m.element_id)

                # Process Edge (Relationship)
                edges.append({
                    "from": n.element_id,
                    "to": m.element_id,
                    "label": r.type
                })

        return jsonify({"success": True, "nodes": nodes, "edges": edges})

    except Exception as e:
        print(f"Neo4j Query Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# --- ADMIN: USER ACTIVITY LOGS ---
@app.route('/api/admin/activity_logs', methods=['GET', 'OPTIONS'])
def get_activity_logs():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Real SQL Query joining your users table and AI_INTERACTION_LOG table
        cursor.execute("""
            SELECT 
                u.name as user, 
                'Triggered AI Tool' as action, 
                a.message_content as target, 
                a.timestamp as time
            FROM AI_INTERACTION_LOG a
            JOIN users u ON a.user_id = u.id
            ORDER BY a.timestamp DESC
            LIMIT 10
        """)
        
        # Fetch the real rows from the database
        real_logs = cursor.fetchall()
        
        # Convert MySQL DATETIME objects to ISO string format so JSON can send them to JS safely
        for log in real_logs:
            if isinstance(log['time'], datetime):
                log['time'] = log['time'].isoformat()
        
        return jsonify({"success": True, "logs": real_logs})

    except Exception as e:
        print(f"Error fetching logs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

        # --- ADMIN: SYSTEM ANALYTICS ---
@app.route('/api/admin/analytics', methods=['GET', 'OPTIONS'])
def get_analytics():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Count Total Users (Assuming your table is named 'users')
        try:
            cursor.execute("SELECT COUNT(*) as count FROM users")
            total_users = cursor.fetchone()['count']
        except:
            total_users = 0 # Fallback if table doesn't exist yet

        # 2. Count Total Jobs
        cursor.execute("SELECT COUNT(*) as count FROM job_market")
        total_jobs = cursor.fetchone()['count']

        # 3. Get Job distribution for the Pie Chart
        cursor.execute("SELECT cluster, COUNT(*) as count FROM job_market GROUP BY cluster")
        cluster_data = cursor.fetchall()

        return jsonify({
            "success": True, 
            "total_users": total_users,
            "total_jobs": total_jobs,
            "cluster_data": cluster_data,
            # Simulated data for AI API Calls over the last 7 days
            "ai_usage": [12, 19, 35, 25, 42, 65, 89] 
        })
    except Exception as e:
        print(f"Analytics Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

        # --- ADMIN: ASSESSMENT BANK ---
@app.route('/api/admin/questions', methods=['GET', 'OPTIONS'])
def get_assessment_questions():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM assessment_questions ORDER BY created_at DESC")
        questions = cursor.fetchall()
        return jsonify({"success": True, "questions": questions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/admin/questions', methods=['POST', 'OPTIONS'])
def add_assessment_question():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    data = request.json
    question_text = data.get('question_text')
    trait_category = data.get('trait_category')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO assessment_questions (question_text, trait_category) VALUES (%s, %s)", 
                       (question_text, trait_category))
        conn.commit()
        return jsonify({"success": True, "message": "Question added!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/admin/questions/<int:q_id>', methods=['DELETE', 'OPTIONS'])
def delete_assessment_question(q_id):
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM assessment_questions WHERE id = %s", (q_id,))
        conn.commit()
        return jsonify({"success": True, "message": "Question deleted!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

        # --- ADMIN: STUDENT REPORTS ---
@app.route('/api/admin/users', methods=['GET', 'OPTIONS'])
def get_admin_users():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch users, hide passwords, order by newest
        cursor.execute("SELECT id, name, email, role, created_at FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        return jsonify({"success": True, "users": users})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# --- GRAPHRAG AI ROUTE ---

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat_with_ai():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    try:
        # 1. Safely grab data from the new FormData format (NOT request.json)
        user_message = request.form.get('message', '')

        # 2. Prevent empty messages
        if not user_message or not user_message.strip():
            return jsonify({"error": "No message provided"}), 400
            
        # 3. Log it and send to GraphRAG / EduGen
        print(f"\n💬 AE-GEN Chat received: {user_message}")
        
        ai_response = ask_edugen(user_message)
        
        return jsonify({"response": ai_response, "success": True})
        
    except Exception as e:
        # If it crashes, this ensures it STILL returns JSON so the frontend doesn't break!
        print(f"🚨 Error in chat route: {e}")
        return jsonify({"error": "Failed to generate response. Check Python terminal for details.", "success": False}), 500


# --- AI TOOL ROUTES ---

@app.route('/api/resume', methods=['POST', 'OPTIONS'])
def handle_resume():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    # 1. Grab text data from the form (Not JSON!)
    text = request.form.get('message', '')
    user_id = request.form.get('user_id') 

    # 2. Extract CV Text if attached
    cv_text = ""
    if 'cv_file' in request.files:
        file = request.files['cv_file']
        if file and file.filename != '':
            cv_text = extract_text_from_cv(file)

    # 3. Combine prompt
    final_prompt = text
    if cv_text:
        final_prompt += f"\n\n--- UPLOADED CV CONTENT ---\n{cv_text}"

    print(f"\n--- 🤖 RESUME ROUTE TRIGGERED ---")
    print(f"User ID received: {user_id}")

    if not final_prompt.strip(): 
        return jsonify({"error": "No text or CV provided"}), 400
    
    # Trigger the AI Tool
    response = optimize_resume(final_prompt)

    # LOG THE ACTIVITY TO THE DATABASE
    if user_id and user_id != 'null':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            sql = "INSERT INTO AI_INTERACTION_LOG (user_id, message_content) VALUES (%s, %s)"
            cursor.execute(sql, (user_id, "Triggered CrewAI: Resume Optimizer"))
            conn.commit()
            print("✅ SUCCESS: Saved log to database!")
        except Exception as e:
            print(f"❌ DATABASE ERROR: {e}")
        finally:
            if 'cursor' in locals(): cursor.close()
            if 'conn' in locals(): conn.close()
    
    print("----------------------------------\n")
    return jsonify({"response": response})


@app.route('/api/skills', methods=['POST', 'OPTIONS'])
def handle_skills():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    text = request.form.get('message', '')
    
    # Extract CV Text if attached
    cv_text = ""
    if 'cv_file' in request.files:
        file = request.files['cv_file']
        if file and file.filename != '':
            cv_text = extract_text_from_cv(file)

    final_prompt = text
    if cv_text:
        final_prompt += f"\n\n--- UPLOADED CV CONTENT ---\n{cv_text}"

    if not final_prompt.strip(): 
        return jsonify({"error": "No text or CV provided"}), 400
    
    response = analyze_skills(final_prompt)
    return jsonify({"response": response})


@app.route('/api/mock_interview', methods=['POST', 'OPTIONS'])
def handle_mock_interview():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    role = request.form.get('role', '')
    skills = request.form.get('skills', 'General knowledge')
    
    # Extract CV Text if attached
    cv_text = ""
    if 'cv_file' in request.files:
        file = request.files['cv_file']
        if file and file.filename != '':
            cv_text = extract_text_from_cv(file)

    if cv_text:
        # If they uploaded a CV, we inject it into the skills parameter so the HR Agent can read it!
        skills += f"\n\nCandidate's Attached CV:\n{cv_text}"

    if not role or not skills:
        return jsonify({"error": "Missing role or skills/CV"}), 400
    
    try:
        # Trigger the CrewAI agents
        ai_response = generate_interview_panel(role, skills)
        return jsonify({"response": ai_response})
    except Exception as e:
        print(f"🚨 CrewAI Error: {e}")
        return jsonify({"error": "Failed to generate interview panel."}), 500


# --- JOB ENGINE ROUTES ---

@app.route('/api/save_job', methods=['POST', 'OPTIONS'])
def save_job():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    data = request.json
    user_id = data.get('user_id')
    job_title = data.get('job_title')

    if not user_id or not job_title:
        return jsonify({"success": False, "error": "Missing info"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM saved_jobs WHERE user_id = %s AND job_title = %s", (user_id, job_title))
        if cursor.fetchone():
            return jsonify({"success": True, "message": "Already saved"})

        sql = "INSERT INTO saved_jobs (user_id, job_title) VALUES (%s, %s)"
        cursor.execute(sql, (user_id, job_title))
        conn.commit()
        return jsonify({"success": True, "message": "Saved!"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()



        
# THIS WAS THE ROUTE MISSING IN YOUR CODE!
@app.route('/api/saved_jobs/<int:user_id>', methods=['GET', 'OPTIONS'])
def get_saved_jobs(user_id):
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT job_title, saved_at FROM saved_jobs WHERE user_id = %s ORDER BY saved_at DESC", (user_id,))
        jobs = cursor.fetchall()
        return jsonify({"success": True, "jobs": jobs}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

        
@app.route('/api/analyze_job', methods=['POST', 'OPTIONS'])
def analyze_job():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    data = request.json
    job_title = data.get('job_title')
    user_skills = data.get('skills', 'General knowledge')
    academic_level = data.get('level', 'Undergraduate')

    if not job_title:
        return jsonify({"success": False, "error": "Missing job title"}), 400

    try:
        # Trigger the CrewAI analysis
        report = generate_fit_analysis(job_title, user_skills, academic_level)
        return jsonify({"success": True, "report": report})
    except Exception as e:
        print(f"🚨 Job Analysis Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
        


# --- PROFILE ROUTES ---

@app.route('/api/profile/<int:user_id>', methods=['GET', 'OPTIONS'])
def get_profile(user_id):
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM user_profiles WHERE user_id = %s", (user_id,))
        profile = cursor.fetchone()
        return jsonify({"success": True, "profile": profile})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/profile', methods=['POST', 'OPTIONS'])
def save_profile():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    data = request.json
    uid = data.get('user_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = """
            REPLACE INTO user_profiles (user_id, age, academic_level, domains, work_style, strengths, skills, about)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            uid, data.get('age'), data.get('academicLevel'), 
            ",".join(data.get('preferredDomains')), data.get('workStyle'),
            data.get('strengths'), data.get('skills'), data.get('about')
        ))
        conn.commit()
        return jsonify({"success": True, "message": "Profile synced to database!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

 # --- AI ASSESSMENT GENERATOR (FULLY DYNAMIC LLM ROUTE) ---
@app.route('/api/generate_options', methods=['POST', 'OPTIONS'])
def generate_ai_options():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    data = request.json
    scenario = data.get('scenario', '').strip()

    if not scenario:
        return jsonify({"success": False, "error": "No scenario provided"}), 400

    try:
        # 1. CONSTRUCT A STRICT STRUCTURED PROMPT FOR YOUR LLM
        prompt_text = f"""You are a psychometric engine for the EduGEN Career Platform.
A student is responding to this specific personal statement or situational challenge:
"{scenario}"

Generate exactly 4 distinct, contextual answer options tailored to this situation. Each option must reflect one of these target mindsets:
- logic: Action focused on backend code, algorithmic optimization, or data logic.
- design: Action focused on user interface, aesthetics, styling, or frontend empathy.
- business: Action focused on project scope, roadmaps, market viability, or product strategy.
- social: Action focused on communication, team collaboration, or stakeholder alignment.

Rules:
- Keep options under 12 words. Make them concise and natural.
- DO NOT repeat the scenario text itself.
- Customize them to match the technical context of the statement.
- Output ONLY a raw valid JSON array containing exactly 4 objects structured like this:
[
  {{"trait": "logic", "text": "Short customized response description"}},
  {{"trait": "design", "text": "Short customized response description"}},
  {{"trait": "business", "text": "Short customized response description"}},
  {{"trait": "social", "text": "Short customized response description"}}
]
Do not wrap your output in ```json markdown formatting blocks. Return the raw string directly.
"""

        # 2. CALL YOUR LIVE CLOUD LLM
        response = cloud_llm.call(prompt_text)
        
        # Clean up any accidental markdown code wrappers from the LLM string
        clean_response = response.strip()
        if clean_response.startswith("```"):
            clean_response = clean_response.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            if clean_response.startswith("json"):
                clean_response = clean_response[4:].strip()

        # 3. PARSE INTO RAW JSON FOR FRONTEND RENDERING
        import json
        import random
        ai_responses = json.loads(clean_response)
        
        # Shuffle choices so 'Logic' is not always index 0
        random.shuffle(ai_responses)

        return jsonify({
            "success": True, 
            "options": ai_responses
        })

    except Exception as e:
        print(f"🚨 Dynamic Options Engine Error: {e}")
        # Secure fallback array if the LLM api fails or runs into a network timeout
        fallback_responses = [
            {"trait": "logic", "text": "Analyze requirements and optimize structural technical logic."},
            {"trait": "design", "text": "Prioritize user-centric wireframing, interface layout, and frontend styling."},
            {"trait": "business", "text": "Evaluate project scale, milestone tracking, and strategic market fit."},
            {"trait": "social", "text": "Coordinate cross-functional updates to maintain unified team alignment."}
        ]
        return jsonify({
            "success": True, 
            "options": fallback_responses,
            "note": "Fallback triggered due to generation anomaly"
        })
    

    # Reseacrh Job route
@app.route('/api/research_job', methods=['POST', 'OPTIONS'])
def research_job():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    data = request.json
    job_title = data.get('job_title')
    user_id = data.get('user_id')

    if not job_title:
        return jsonify({"success": False, "error": "Missing job title"}), 400

    try:
        # Import your new deep research function (we will create this next)
        from services.job_analyzer import generate_deep_web_research
        
        # Trigger the web-browsing agent
        report = generate_deep_web_research(job_title)

        # Log the activity to the database!
        if user_id:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO AI_INTERACTION_LOG (user_id, message_content) VALUES (%s, %s)", 
                              (user_id, f"Triggered Agent: Web Research for {job_title}"))
                conn.commit()
            except Exception as e:
                print("DB Log Error:", e)
            finally:
                if 'cursor' in locals(): cursor.close()
                if 'conn' in locals(): conn.close()

        return jsonify({"success": True, "report": report})
    except Exception as e:
        print(f"🚨 Web Research Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    

    # --- FEEDBACK ROUTES ---

@app.route('/api/submit_feedback', methods=['POST', 'OPTIONS'])
def submit_feedback():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    data = request.json
    user_id = data.get('user_id')
    user_name = data.get('user_name', 'Anonymous')
    rating = data.get('rating')
    comment = data.get('comment')

    if not rating or not comment:
        return jsonify({"success": False, "error": "Rating and comment are required."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = "INSERT INTO user_feedback (user_id, user_name, rating, comment) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (user_id, user_name, rating, comment))
        conn.commit()
        return jsonify({"success": True, "message": "Feedback submitted successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/admin/feedback', methods=['GET', 'OPTIONS'])
def get_all_feedback():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM user_feedback ORDER BY created_at DESC")
        feedback = cursor.fetchall()
        return jsonify({"success": True, "feedback": feedback})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/admin/feedback/<int:fb_id>', methods=['DELETE', 'OPTIONS'])
def delete_feedback(fb_id):
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM user_feedback WHERE id = %s", (fb_id,))
        conn.commit()
        return jsonify({"success": True, "message": "Feedback deleted"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

#--ADMIN GENERATE QUESTION--
@app.route('/api/admin/generate_question', methods=['POST', 'OPTIONS'])
def generate_assessment_question():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    try:
        data = request.json
        trait = data.get('trait_category', 'logic')

        # Expanded to support role-specific prompt guidance
        trait_mapping = {
            "logic": "Logical, analytical, backend programming, and data analysis.",
            "design": "Creative, UI/UX design, frontend development, and visual aesthetics.",
            "business": "Business strategy, project management, leadership, and product planning.",
            "software_engineer": "Software Engineering, covering writing clean code, data structures, debugging code, and system architecture structures.",
            "data_analyst": "Data Analytics, focusing on data manipulation, database querying, statistical calculations, and graph interpretation.",
            "ui_ux_designer": "UI/UX Design, including wireframing, component accessibility, interface aesthetics, and user research empathy.",
            "cybersecurity_analyst": "Cybersecurity, focusing on network vulnerability analysis, threat mitigation, and evaluating script execution risks."
        }
        
        target_trait = trait_mapping.get(trait, "General technology")

        prompt_text = f"""You are an expert psychometric assessment designer.
        Write ONE single, high-quality assessment statement designed to test if a student has a strong situational aptitude or preference for: {target_trait}
        
        Rules:
        - Write it in the first person (e.g., "I enjoy...", "When presented with...").
        - Make the text represent a realistic technical challenge, scenario, or preference matching that specialization.
        - It must be a statement that a user can strongly agree or disagree with.
        - Keep it under 2 sentences.
        - Do not include quotes, prefixes, or any extra conversational text. Just output the statement directly.
        """
        
        response = cloud_llm.call(prompt_text)
        clean_question = response.replace('"', '').strip()

        return jsonify({"success": True, "generated_question": clean_question})

    except Exception as e:
        print(f"🚨 AI Generation Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

    


if __name__ == '__main__':
    app.run(debug=True, port=5001)