import requests
import time
import random
import sys

API_URL = "http://localhost:5000/api/update"
API_KEY = "HEALINK_v1_KEY"

def simulate(user_id):
    print(f"Starting simulation for User {user_id}...")
    while True:
        data = {
            "api_key": API_KEY,
            "user_id": user_id,
            "heart_rate": random.randint(60, 100),
            "blood_pressure_sys": random.randint(110, 140),
            "blood_pressure_dia": random.randint(70, 90),
            "oxygen_level": random.randint(95, 100),
            "temperature": round(random.uniform(36.5, 37.5), 1),
            "sugar_level": round(random.uniform(80, 120), 1)
        }
        
        try:
            response = requests.post(API_URL, json=data)
            if response.status_code == 200:
                print(f"Data sent: HR:{data['heart_rate']} Sys:{data['blood_pressure_sys']}")
            else:
                print(f"Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Connection error: {e}")
            
        time.sleep(5)

if __name__ == '__main__':
    uid = sys.argv[1] if len(sys.argv) > 1 else 2
    simulate(uid)
