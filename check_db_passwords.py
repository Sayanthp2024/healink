import sqlite3
import os

# Standardized path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'health.db')

def check_db():
    print(f"Checking database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"Database not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        users = cursor.execute("SELECT id, username, password FROM users").fetchall()
        print(f"Found {len(users)} users.")
        for user in users:
            print(f"ID: {user['id']}, Username: {user['username']}")
            print(f"Hash starts with: {user['password'][:20]}...")
            if user['password'].startswith('$2y$'):
                print("  [!] Still PHP hash")
            else:
                print("  [OK] Likely Werkzeug hash")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    check_db()
