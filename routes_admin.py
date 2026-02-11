from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_db_connection
from auth_utils import roles_required
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@roles_required('admin')
def index():
    view_user_id = request.args.get('user_id')
    conn = get_db_connection()
    
    patients = conn.execute("SELECT id, full_name, role FROM users WHERE role = 'patient'").fetchall()
    active_sos = conn.execute("SELECT s.*, u.full_name FROM sos_alerts s JOIN users u ON s.patient_id = u.id WHERE s.status = 'active' ORDER BY s.timestamp DESC").fetchall()
    hospitals = conn.execute("SELECT * FROM hospitals").fetchall()
    all_users = conn.execute("SELECT * FROM users").fetchall()
    
    # Association dropdowns
    monitors = conn.execute("SELECT id, username, role FROM users WHERE role IN ('home_nurse', 'caregiver', 'migrant_worker')").fetchall()
    
    conn.close()
    
    clinical_info = None
    medication_alerts = []
    if view_user_id:
        # Fetching extra data for monitoring view
        conn = get_db_connection()
        clinical_info = conn.execute("SELECT * FROM patient_clinical_info WHERE patient_id = ?", (view_user_id,)).fetchone()
        medication_alerts = conn.execute("SELECT * FROM medication_alerts WHERE user_id = ? ORDER BY time ASC", (view_user_id,)).fetchall()
        conn.close()

    return render_template('admin/index.html', 
                           patients=patients, 
                           active_sos=active_sos, 
                           hospitals=hospitals, 
                           all_users=all_users,
                           monitors=monitors,
                           view_user_id=view_user_id,
                           clinical_info=clinical_info,
                           medication_alerts=medication_alerts)

@admin_bp.route('/action', methods=['POST'])
@roles_required('admin')
def action():
    action_type = request.form.get('action')
    conn = get_db_connection()
    
    try:
        if action_type == 'add_user':
            username = request.form['username']
            password = generate_password_hash(request.form['password'])
            role = request.form['role']
            full_name = request.form['full_name']
            conn.execute("INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)", (username, password, role, full_name))
        
        elif action_type == 'add_association':
            conn.execute("INSERT INTO user_associations (monitor_id, patient_id) VALUES (?, ?)", (request.form['monitor_id'], request.form['patient_id']))
            
        elif action_type == 'delete_user':
            conn.execute("DELETE FROM users WHERE id = ?", (request.form['id'],))
            
        elif action_type == 'delete_association':
            conn.execute("DELETE FROM user_associations WHERE id = ?", (request.form['id'],))
            
        elif action_type == 'add_med':
            conn.execute("INSERT INTO medication_alerts (user_id, med_name, dosage, time) VALUES (?, ?, ?, ?)", 
                         (request.form['patient_id'], request.form['med_name'], request.form['dosage'], request.form['time']))
            
        elif action_type == 'add_hospital':
            conn.execute("INSERT INTO hospitals (name, address, contact_person, email) VALUES (?, ?, ?, ?)", 
                         (request.form['h_name'], request.form['h_address'], request.form['h_contact'], request.form['h_email']))
            
        elif action_type == 'dismiss_sos':
            conn.execute("UPDATE sos_alerts SET status = 'dismissed' WHERE id = ?", (request.form['sos_id'],))
            
        conn.commit()
    except Exception as e:
        flash(f"Error: {str(e)}")
    finally:
        conn.close()
        
    return redirect(request.referrer or url_for('admin.index'))

@admin_bp.route('/relationships')
@roles_required('admin')
def relationships():
    conn = get_db_connection()
    
    # Fetch all associations with details
    associations = conn.execute("""
        SELECT ua.id, 
               m.full_name as monitor_name, m.role as monitor_role,
               p.full_name as patient_name
        FROM user_associations ua
        JOIN users m ON ua.monitor_id = m.id
        JOIN users p ON ua.patient_id = p.id
        ORDER BY m.full_name ASC
    """).fetchall()
    
    # Data for the add form
    patients = conn.execute("SELECT id, full_name FROM users WHERE role = 'patient'").fetchall()
    monitors = conn.execute("SELECT id, full_name, role FROM users WHERE role IN ('home_nurse', 'caregiver', 'migrant_worker')").fetchall()
    
    conn.close()
    return render_template('admin/relationships.html', 
                           associations=associations,
                           patients=patients,
                           monitors=monitors)

@admin_bp.route('/migrant_workers')
@roles_required('admin')
def migrant_workers():
    conn = get_db_connection()
    workers = conn.execute("""
        SELECT u.id, u.full_name, u.username, 
        (SELECT COUNT(*) FROM user_associations WHERE monitor_id = u.id) as patient_count
        FROM users u
        WHERE u.role = 'migrant_worker'
    """).fetchall()
    conn.close()
    return render_template('admin/migrant_workers.html', workers=workers)

@admin_bp.route('/caregivers')
@roles_required('admin')
def caregivers():
    conn = get_db_connection()
    caregivers = conn.execute("""
        SELECT u.id, u.full_name, u.username, 
        (SELECT COUNT(*) FROM user_associations WHERE monitor_id = u.id) as patient_count
        FROM users u
        WHERE u.role = 'caregiver'
    """).fetchall()
    conn.close()
    return render_template('admin/caregivers.html', caregivers=caregivers)

@admin_bp.route('/patients')
@roles_required('admin')
def patients_list():
    conn = get_db_connection()
    patients = conn.execute("""
        SELECT u.id, u.full_name, u.username, 
        (SELECT COUNT(*) FROM user_associations WHERE patient_id = u.id) as monitor_count
        FROM users u
        WHERE u.role = 'patient'
    """).fetchall()
    conn.close()
    return render_template('admin/patients.html', patients=patients)
