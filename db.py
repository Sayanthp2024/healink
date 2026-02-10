import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'health.db')
API_KEY = "HEALINK_v1_KEY"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(os.path.dirname(DB_PATH)):
        os.makedirs(os.path.dirname(DB_PATH))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Initial schema setup
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS health_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            heart_rate INTEGER,
            blood_pressure_sys INTEGER,
            blood_pressure_dia INTEGER,
            oxygen_level INTEGER,
            temperature REAL,
            sugar_level REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medication_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            med_name TEXT,
            dosage TEXT,
            time TEXT,
            taken INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visit_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            worker_id INTEGER,
            note TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (worker_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            address TEXT,
            contact_person TEXT,
            email TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sos_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            status TEXT DEFAULT 'active',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            full_name TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_associations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monitor_id INTEGER,
            patient_id INTEGER,
            FOREIGN KEY (monitor_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patient_clinical_info (
            patient_id INTEGER PRIMARY KEY,
            diseases TEXT,
            doctors TEXT,
            medications TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # Seed default users
    default_users = [
        ('admin', 'admin123', 'admin', 'System Administrator'),
        ('patient', 'patient123', 'patient', 'Robert Johnson'),
        ('worker', 'worker123', 'migrant_worker', 'Juan Garcia'),
        ('nurse', 'nurse123', 'home_nurse', 'Sarah Smith'),
        ('caregiver', 'caregiver123', 'caregiver', 'Emily Johnson')
    ]

    for username, password, role, full_name in default_users:
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if not cursor.fetchone():
            pwd_hash = generate_password_hash(password)
            cursor.execute("INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)", 
                         (username, pwd_hash, role, full_name))

    # Universal Migration: Fix legacy hashes for users added via older systems (e.g. PHP)
    all_users = cursor.execute("SELECT id, username, password, role FROM users").fetchall()
    
    # Map roles to default fallback passwords ONLY if we must reset them
    role_password_map = {
        'admin': 'admin123',
        'patient': 'patient123',
        'migrant_worker': 'worker123',
        'home_nurse': 'nurse123',
        'caregiver': 'caregiver123'
    }

    for user in all_users:
        # Check for PHP/BCrypt legacy hashes
        if user['password'] and user['password'].startswith('$2y$'):
            # Only reset if it's strictly necessary. 
            # If the user is a known default account, we definitely reset it.
            # If it's a new account, we use the role default but log a warning.
            new_password = role_password_map.get(user['role'], 'healink123')
            new_hash = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (new_hash, user['id']))
            print(f"[*] Migrated legacy PHP hash for user: {user['username']} -> Reset to default {user['role']} password.")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized.")
