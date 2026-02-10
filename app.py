from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
import os
import secrets
from db import init_db, get_db_connection

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Initialize Database and Logs on Start
with app.app_context():
    init_db()
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

from routes_api import api_bp
from routes_admin import admin_bp
app.register_blueprint(api_bp)
app.register_blueprint(admin_bp)

from werkzeug.security import check_password_hash
from auth_utils import login_required, roles_required, redirect_if_logged_in

@app.route('/')
@login_required
def home():
    role = session.get('role')
    username = session.get('username')
    
    # Detailed logging for debugging role redirection
    log_path = os.path.join(os.path.dirname(__file__), 'logs', 'auth_debug.log')
    with open(log_path, 'a') as f:
        import datetime
        f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Home access: user={username}, role={role}\n")

    if role == 'admin':
        return redirect(url_for('admin.index'))
    elif role == 'patient':
        return redirect(url_for('patient_dashboard'))
    elif role == 'home_nurse':
        return redirect(url_for('nurse_dashboard'))
    elif role == 'migrant_worker':
        return redirect(url_for('worker_dashboard'))
    elif role == 'caregiver':
        return redirect(url_for('caregiver_dashboard'))
    return f"Logged in as {role} (Unknown redirect)"

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE LOWER(username) = LOWER(?)', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            # Clear old session data before setting new user data
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            
            # Logging (porting from login.php update)
            log_path = os.path.join(os.path.dirname(__file__), 'logs', 'auth_debug.log')
            with open(log_path, 'a') as f:
                import datetime
                f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Login successful for: {username}\n")
            
            return redirect(url_for('home'))
        else:
            reason = "User not found" if not user else "Password mismatch"
            log_path = os.path.join(os.path.dirname(__file__), 'logs', 'auth_debug.log')
            with open(log_path, 'a') as f:
                import datetime
                f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Login failed for: {username} ({reason})\n")
            error = "Invalid username or password."

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Dashboard Redirection
@app.route('/admin')
@roles_required('admin')
def admin_redirect():
    return redirect(url_for('admin.index'))

@app.route('/patient')
@roles_required('patient')
def patient_dashboard():
    conn = get_db_connection()
    meds = conn.execute('SELECT * FROM medication_alerts WHERE user_id = ? AND taken = 0 ORDER BY time ASC', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('patient/index.html', medication_alerts=meds)

@app.route('/patient/care_team')
@roles_required('patient')
def care_team():
    conn = get_db_connection()
    members = conn.execute("""
        SELECT u.id, u.full_name, u.role, ua.id as association_id
        FROM users u
        JOIN user_associations ua ON u.id = ua.monitor_id
        WHERE ua.patient_id = ?
    """, (session['user_id'],)).fetchall()
    conn.close()
    return render_template('patient/care_team.html', care_team=members)

@app.route('/nurse', methods=['GET', 'POST'])
@roles_required('home_nurse')
def nurse_dashboard():
    view_user_id = request.args.get('user_id')
    conn = get_db_connection()
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_note':
            conn.execute("INSERT INTO visit_notes (patient_id, worker_id, note) VALUES (?, ?, ?)",
                         (request.form['patient_id'], session['user_id'], request.form['note']))
            conn.commit()
        elif action == 'update_clinical_info':
            conn.execute("INSERT OR REPLACE INTO patient_clinical_info (patient_id, diseases, doctors, medications, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                         (request.form['patient_id'], request.form['diseases'], request.form['doctors'], request.form['medications']))
            conn.commit()
        return redirect(url_for('nurse_dashboard', user_id=request.form['patient_id']))

    # Fetch assigned patients
    assigned_patients = conn.execute("""
        SELECT u.id, u.full_name, MAX(hd.timestamp) as last_seen 
        FROM users u
        JOIN user_associations ua ON u.id = ua.patient_id
        LEFT JOIN health_data hd ON u.id = hd.user_id
        WHERE ua.monitor_id = ?
        GROUP BY u.id
    """, (session['user_id'],)).fetchall()

    clinical_info = None
    medication_alerts = []
    observation_history = []
    if view_user_id:
        clinical_info = conn.execute("SELECT * FROM patient_clinical_info WHERE patient_id = ?", (view_user_id,)).fetchone()
        medication_alerts = conn.execute("SELECT * FROM medication_alerts WHERE user_id = ? AND taken = 0 ORDER BY time ASC", (view_user_id,)).fetchall()
        observation_history = conn.execute("""
            SELECT vn.*, u.full_name as worker_name 
            FROM visit_notes vn 
            JOIN users u ON vn.worker_id = u.id 
            WHERE vn.patient_id = ? 
            ORDER BY vn.timestamp DESC
        """, (view_user_id,)).fetchall()

    conn.close()
    return render_template('nurse/index.html', 
                           assigned_patients=assigned_patients,
                           view_user_id=view_user_id,
                           clinical_info=clinical_info,
                           medication_alerts=medication_alerts,
                           observation_history=observation_history)

@app.route('/worker', methods=['GET', 'POST'])
@roles_required('migrant_worker')
def worker_dashboard():
    view_user_id = request.args.get('user_id')
    conn = get_db_connection()
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_note':
            conn.execute("INSERT INTO visit_notes (patient_id, worker_id, note) VALUES (?, ?, ?)",
                         (request.form['patient_id'], session['user_id'], request.form['note']))
            conn.commit()
        return redirect(url_for('worker_dashboard', user_id=request.form['patient_id']))

    assigned_patients = conn.execute("""
        SELECT u.id, u.full_name, MAX(hd.timestamp) as last_seen 
        FROM users u
        JOIN user_associations ua ON u.id = ua.patient_id
        LEFT JOIN health_data hd ON u.id = hd.user_id
        WHERE ua.monitor_id = ?
        GROUP BY u.id
    """, (session['user_id'],)).fetchall()

    observation_history = []
    if view_user_id:
        observation_history = conn.execute("""
            SELECT vn.*, u.full_name as worker_name 
            FROM visit_notes vn 
            JOIN users u ON vn.worker_id = u.id 
            WHERE vn.patient_id = ? 
            ORDER BY vn.timestamp DESC
        """, (view_user_id,)).fetchall()

    conn.close()
    return render_template('worker/index.html', 
                           assigned_patients=assigned_patients,
                           view_user_id=view_user_id,
                           observation_history=observation_history)

@app.route('/caregiver', methods=['GET', 'POST'])
@roles_required('caregiver')
def caregiver_dashboard():
    # Exactly same as worker logic for this app
    view_user_id = request.args.get('user_id')
    conn = get_db_connection()
    if request.method == 'POST':
        conn.execute("INSERT INTO visit_notes (patient_id, worker_id, note) VALUES (?, ?, ?)",
                     (request.form['patient_id'], session['user_id'], request.form['note']))
        conn.commit()
        return redirect(url_for('caregiver_dashboard', user_id=request.form['patient_id']))

    assigned_patients = conn.execute("""
        SELECT u.id, u.full_name, MAX(hd.timestamp) as last_seen 
        FROM users u
        JOIN user_associations ua ON u.id = ua.patient_id
        LEFT JOIN health_data hd ON u.id = hd.user_id
        WHERE ua.monitor_id = ?
        GROUP BY u.id
    """, (session['user_id'],)).fetchall()

    observation_history = []
    if view_user_id:
        observation_history = conn.execute("""
            SELECT vn.*, u.full_name as worker_name 
            FROM visit_notes vn 
            JOIN users u ON vn.worker_id = u.id 
            WHERE vn.patient_id = ? 
            ORDER BY vn.timestamp DESC
        """, (view_user_id,)).fetchall()
    conn.close()
    return render_template('caregiver/index.html', 
                           assigned_patients=assigned_patients,
                           view_user_id=view_user_id,
                           observation_history=observation_history)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
