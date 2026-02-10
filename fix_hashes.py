import sqlite3
import os
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'health.db')

def fix_hashes():
    print(f"Fixing database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    passwords = {
        'admin': 'admin123',
        'patient': 'patient123',
        'worker': 'worker123',
        'nurse': 'nurse123',
        'caregiver': 'caregiver123'
    }

    try:
        total_updated = 0
        for username, password in passwords.items():
            new_hash = generate_password_hash(password)
            # Use LOWER() to match case-insensitively
            cursor.execute("UPDATE users SET password = ? WHERE LOWER(username) = LOWER(?)", (new_hash, username))
            total_updated += cursor.rowcount
            print(f"Updated {username} ({cursor.rowcount} records)")
        
        conn.commit()
        print(f"Successfully updated {total_updated} total user records.")
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    fix_hashes()
