import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'health.db')

def check_hashes():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    users = cursor.execute("SELECT id, username, password FROM users").fetchall()
    for user in users:
        is_php = user['password'].startswith('$2y$')
        print(f"ID: {user['id']} | Username: {user['username']} | PHP Hash: {is_php}")
    
    conn.close()

if __name__ == '__main__':
    check_hashes()
