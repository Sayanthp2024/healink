from flask import Blueprint, request, jsonify, Response, session, stream_with_context
from db import get_db_connection, API_KEY
import json
import time

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/update', methods=['POST'])
def update_health_data():
    data = request.json
    api_key_header = request.headers.get('X-API-Key')
    
    if api_key_header != API_KEY and data.get('api_key') != API_KEY:
        return jsonify({'error': 'Unauthorized: Invalid API Key'}), 401
    
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400

    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO health_data (user_id, heart_rate, blood_pressure_sys, blood_pressure_dia, oxygen_level, temperature, sugar_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            data.get('heart_rate', 0),
            data.get('blood_pressure_sys', 0),
            data.get('blood_pressure_dia', 0),
            data.get('oxygen_level', 0),
            data.get('temperature', 0),
            data.get('sugar_level', 0)
        ))
        conn.commit()
        return jsonify({'status': 'success', 'message': 'Data updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@api_bp.route('/history')
def get_history():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400
    
    conn = get_db_connection()
    history = conn.execute('SELECT * FROM health_data WHERE user_id = ? ORDER BY timestamp DESC LIMIT 50', (user_id,)).fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in reversed(history)])

@api_bp.route('/stream')
def stream_data():
    user_id = request.args.get('user_id') or session.get('user_id')
    if not user_id:
        return Response(status=401)

    # Security check: Porting association check from stream.php
    if int(user_id) != session.get('user_id') and session.get('role') != 'admin':
        conn = get_db_connection()
        assoc = conn.execute('SELECT 1 FROM user_associations WHERE monitor_id = ? AND patient_id = ?', (session.get('user_id'), user_id)).fetchone()
        conn.close()
        if not assoc:
            return Response(status=403)

    def generate():
        last_id = 0
        while True:
            conn = get_db_connection()
            try:
                data = conn.execute('SELECT * FROM health_data WHERE id > ? AND user_id = ? ORDER BY id DESC LIMIT 1', (last_id, user_id)).fetchone()
                if data:
                    last_id = data['id']
                    yield f"data: {json.dumps(dict(data))}\n\n"
            finally:
                conn.close()
            time.sleep(1)

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@api_bp.route('/trigger_sos')
def trigger_sos():
    patient_id = session.get('user_id')
    if not patient_id: return jsonify({'success': False}), 401
    
    conn = get_db_connection()
    conn.execute('INSERT INTO sos_alerts (patient_id) VALUES (?)', (patient_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@api_bp.route('/meds_update')
def meds_update():
    med_id = request.args.get('id')
    if not med_id: return Response(status=400)
    
    conn = get_db_connection()
    conn.execute('UPDATE medication_alerts SET taken = 1 WHERE id = ?', (med_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@api_bp.route('/save_note', methods=['POST'])
def save_note():
    # Port save_note.php logic
    pass

@api_bp.route('/check_sos')
def check_sos():
    if 'user_id' not in session:
        return Response(status=403)
        
    patient_id = request.args.get('patient_id')
    if not patient_id:
        return Response(status=400)
        
    conn = get_db_connection()
    alert = conn.execute("SELECT id FROM sos_alerts WHERE patient_id = ? AND status = 'active' LIMIT 1", (patient_id,)).fetchone()
    conn.close()
    
    return jsonify({'active': bool(alert)})
