import requests

def verify_auth():
    print("--- 1. Testing Protected Endpoint (No Token) ---")
    try:
        resp = requests.get("http://localhost:8000/api/dashboard")
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 401:
            print("✅ SUCCESS: Access Denied (401)")
        else:
            print(f"❌ FAILURE: Expected 401, got {resp.status_code}")
    except Exception as e:
        print("Error:", e)

    print("\n--- 2. Testing Login (Bad Credentials) ---")
    try:
        data = {"username": "fakeuser", "password": "badpassword"}
        resp = requests.post("http://localhost:8000/token", data=data)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 401:
            print("✅ SUCCESS: Login Rejected (401)")
        else:
            print(f"❌ FAILURE: Expected 401, got {resp.status_code}")
            print(resp.json())
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    verify_auth()
