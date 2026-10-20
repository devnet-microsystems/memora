import pytest
from dashboard.app import app
import base64

def test():
    app.config['TESTING'] = True
    with app.test_client() as client:
        credentials = "admin:secret"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        headers = {'Authorization': f'Basic {encoded_credentials}'}
        
        resp = client.post("/api/report", headers=headers)
        print(f"STATUS: {resp.status_code}")
        print(f"DATA: {resp.data}")

if __name__ == "__main__":
    test()
