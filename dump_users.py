import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'health.db')

def dump_users():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    with open('users_dump.txt', 'w') as f:
        users = cursor.execute("SELECT id, username, role FROM users").fetchall()
        for user in users:
            f.write(f"ID: {user['id']} | Username: {user['username']} | Role: {user['role']}\n")
    
    conn.close()
    print("Users dumped to users_dump.txt")

if __name__ == '__main__':
    dump_users()
