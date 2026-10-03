import requests

def test_auth_bypass():
    url = "http://127.0.0.1:5001/api/memory"
    print(f"Testing Auth Bypass on {url}")
    
    # We send a request to the dashboard WITHOUT any authentication
    try:
        response = requests.get(url, timeout=5)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("VULNERABLE! Successfully accessed /api/memory via dashboard proxy without authentication.")
            data = response.json()
            print(f"Returned {len(data.get('nodes', []))} memory nodes.")
        else:
            print("NOT VULNERABLE. Response was not 200 OK.")
            print(response.text[:200])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_auth_bypass()
