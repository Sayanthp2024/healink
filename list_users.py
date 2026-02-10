import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'health.db')

def list_all_users():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        users = cursor.execute("SELECT id, username, role, password FROM users").fetchall()
        print(f"Total users: {len(users)}")
        print("-" * 60)
        for user in users:
            is_php = user['password'].startswith('$2y$')
            status = "[PHP]" if is_php else "[WZK]"
            print(f"ID: {user['id']:2} | Username: {user['username']:10} | Role: {user['role']:15} | Status: {status} | Hash: {user['password'][:20]}...")
        print("-" * 60)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    list_all_users()
