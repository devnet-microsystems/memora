"""
Dashboard Application for Memora.
Provides a UI for caregivers and users to interact with the system.
"""

import os
import time
import hmac
import requests
from collections import defaultdict
from flask import Flask, render_template, jsonify, request, Response, send_from_directory, session
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__, static_folder='../dashboard/static/dist', static_url_path='/static/dist')
# Behind Render/Fly the real client IP is in X-Forwarded-For; without this every visitor shares one rate-limit bucket.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024  # 16 KB

# Sessione caregiver: cookie HttpOnly, SameSite=Lax, scade alla chiusura del browser
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(24)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = os.getenv("FLASK_COOKIE_SECURE", "0") == "1"
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = 'memora_caregiver_session'

API_URL = os.getenv("API_URL", "http://localhost:8000")
SPA_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'dist')

# In-memory rate limiting state
rate_limits = defaultdict(list)
daily_llm_calls = 0
daily_llm_day = None

def check_auth(username, password):
    expected_user = os.getenv("CAREGIVER_USER")
    expected_pass = os.getenv("CAREGIVER_PASSWORD")
    if not expected_user or not expected_pass:
        return False
    return (hmac.compare_digest(username.encode(), expected_user.encode())
            and hmac.compare_digest(password.encode(), expected_pass.encode()))

def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Memora Caregiver"'}
    )

def get_api_headers():
    headers = {}
    memora_key = os.getenv("MEMORA_API_KEY")
    if memora_key:
        headers["X-Memora-Key"] = memora_key
    return headers

@app.before_request
def proxy_checks():
    global daily_llm_calls, daily_llm_day
    
    path = request.path
    method = request.method
    ip = request.remote_addr
    now = time.time()

    # 1. Routing classification
    is_public_patient = False
    
    if path == '/api/chat' and method == 'POST': is_public_patient = True
    elif path == '/api/sos' and method == 'POST': is_public_patient = True
    elif path == '/api/diary/turn' and method == 'POST': is_public_patient = True
    elif path == '/api/diary/end' and method == 'POST': is_public_patient = True
    elif path == '/api/today' and method == 'GET': is_public_patient = True
    elif path == '/api/aac' and method == 'GET': is_public_patient = True
    elif path.startswith('/api/alerts/') and method == 'GET': is_public_patient = True
    elif path == '/api/med/confirm' and method == 'POST':
        # Must check if status is valid
        data = request.get_json(silent=True) or {}
        if data.get('status') in ['confirmed', 'snoozed', 'unsure', 'denied'] and 'med_id' in data:
            # Type and ID exist check will be handled in the endpoint or backend
            is_public_patient = True
    elif path.startswith('/api/voice/preview') and method == 'POST': is_public_patient = True
    elif path.startswith('/api/voice/confirm') and method == 'POST': is_public_patient = True

    demo_readonly = os.getenv("DEMO_PUBLIC_READONLY", "1") == "1"
    is_public_readonly = False
    if demo_readonly:
        if method == 'GET' and path in ['/api/memory', '/api/med/status', '/api/stats', '/api/pending', '/api/timeline', '/api/usage']:
            is_public_readonly = True
        elif method == 'GET' and path == '/api/health':
            is_public_readonly = True

    # Check protection: operazioni di scrittura e letture non pubbliche
    # richiedono sessione caregiver autenticata. Il polling pubblico di
    # sola lettura resta aperto solo dove l'architettura lo prevede.
    if path.startswith('/api/'):
        if not is_public_patient and not is_public_readonly:
            if path == '/api/caregiver/login' and method == 'POST':
                pass  # login è pubblico per definizione
            elif path == '/api/caregiver/me':
                pass  # endpoint di autoconfigurazione, non richiede sessione
            elif not session.get('caregiver_authenticated'):
                if not os.getenv("CAREGIVER_USER") or not os.getenv("CAREGIVER_PASSWORD"):
                    return jsonify({"error": "caregiver auth not configured"}), 503
                return jsonify({"error": "caregiver authentication required"}), 401

    # 2. Rate limiting
    limit = None
    key = None
    if path == '/api/chat': limit = 20; key = f"chat_{ip}"
    elif path == '/api/sos': limit = 5; key = f"sos_{ip}"
    elif path.startswith('/api/diary'): limit = 20; key = f"diary_{ip}"
    elif path == '/api/med/confirm': limit = 10; key = f"med_{ip}"
    elif path == '/api/voice/preview' or path == '/api/voice/preview/': limit = 20; key = f"voice_preview_{ip}"
    elif path == '/api/voice/confirm' or path == '/api/voice/confirm/': limit = 10; key = f"voice_confirm_{ip}"
    
    if key and limit:
        timestamps = rate_limits[key]
        timestamps = [t for t in timestamps if now - t < 60]
        if len(timestamps) >= limit:
            return jsonify({"error": "Rate limit exceeded"}), 429
        timestamps.append(now)
        rate_limits[key] = timestamps

    # 3. Message size limit for patient chat
    if path == '/api/chat' and method == 'POST':
        data = request.get_json(silent=True) or {}
        if len(data.get('user_input', data.get('message', '')) or '') > 500:
            return jsonify({"error": "Text too long"}), 422

    # 4. Global LLM call limit
    if path in ['/api/chat', '/api/diary/turn', '/api/onboarding', '/api/report', '/api/voice/preview', '/api/voice/preview/'] and method == 'POST':
        today = time.strftime("%Y-%m-%d")
        if daily_llm_day != today:
            daily_llm_day, daily_llm_calls = today, 0
        max_calls = int(os.getenv("MAX_DAILY_LLM_CALLS", "500"))
        if daily_llm_calls >= max_calls:
            return jsonify({"response": "Demo limit reached"}), 429
        daily_llm_calls += 1

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response

# ---- HTML ROUTES (React SPA served by Flask) ----
# The React SPA built by Vite is served from dashboard/static/dist/.
# /caregiver and all non-API routes fall back to the SPA index.html for
# client-side routing. Legacy pages are preserved as fallback.

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/static/dist/<path:filename>")
def spa_static(filename):
    return send_from_directory(SPA_DIST, filename)

@app.route("/caregiver")
def caregiver():
    # Serve React SPA index.html; client-side routing handles /caregiver
    spa_index = os.path.join(SPA_DIST, "index.html")
    if os.path.exists(spa_index):
        return send_from_directory(SPA_DIST, "index.html")
    # Fallback to legacy dashboard if SPA not yet built
    status = "offline"
    try:
        resp = requests.get(f"{API_URL}/health", timeout=2)
        if resp.status_code == 200: status = "online"
    except requests.RequestException: pass
    return render_template("index.html", api_url=API_URL, status=status, patient_id="patient_alex")

@app.route("/patient")
def patient():
    # Serve React SPA index.html; client-side routing handles /patient (PatientView)
    spa_index = os.path.join(SPA_DIST, "index.html")
    if os.path.exists(spa_index):
        return send_from_directory(SPA_DIST, "index.html")
    # Fallback to legacy patient page if SPA not yet built
    return render_template("patient.html", api_url=API_URL)

@app.route("/story")
def story():
    # Serve React SPA index.html; client-side routing handles /story (Life Book)
    spa_index = os.path.join(SPA_DIST, "index.html")
    if os.path.exists(spa_index):
        return send_from_directory(SPA_DIST, "index.html")
    # Fallback to legacy story page if SPA not yet built
    return render_template("story.html")

@app.route("/judges")
def judges():
    # Serve React SPA index.html; client-side routing handles /judges (JudgesView)
    spa_index = os.path.join(SPA_DIST, "index.html")
    if os.path.exists(spa_index):
        return send_from_directory(SPA_DIST, "index.html")
    # Fallback to legacy judges page if SPA not yet built
    return render_template("judges.html")

# Catch-all for SPA client-side routes (non-API, non-static)
@app.route("/<path:subpath>")
def spa_fallback(subpath):
    # Don't intercept API routes or static assets
    if subpath.startswith("api/") or subpath.startswith("static/"):
        return jsonify({"error": "not found"}), 404
    spa_index = os.path.join(SPA_DIST, "index.html")
    if os.path.exists(spa_index):
        return send_from_directory(SPA_DIST, "index.html")
    return jsonify({"error": "not found"}), 404

# ---- API ROUTES ----
def _proxy_get(endpoint):
    try:
        resp = requests.get(f"{API_URL}{endpoint}", params=request.args.to_dict(), timeout=10, headers=get_api_headers())
        return jsonify(resp.json()), resp.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

def _proxy_post(endpoint, req_data=None):
    try:
        resp = requests.post(f"{API_URL}{endpoint}", json=req_data, timeout=90, headers=get_api_headers())
        return jsonify(resp.json()), resp.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500
        
def _proxy_delete(endpoint):
    try:
        resp = requests.delete(f"{API_URL}{endpoint}", timeout=10, headers=get_api_headers())
        return jsonify(resp.json()), resp.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/health")
def get_health():
    try:
        resp = requests.get(f"{API_URL}/health", timeout=5, headers=get_api_headers())
        data = resp.json()
        return jsonify({"status": data.get("status"), "encrypted": data.get("encrypted")}), resp.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/aac")
def get_aac():
    try:
        resp = requests.get(f"{API_URL}/memory", timeout=5, headers=get_api_headers())
        nodes = resp.json().get("nodes", [])
        aac_nodes = [{"id": n["id"], "content": n.get("label", n["id"])} for n in nodes if n.get("group") == "caa_button"]
        return jsonify(aac_nodes), 200
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500
        
@app.route("/api/memory", methods=["GET", "POST"])
def route_memory():
    if request.method == "GET": return _proxy_get("/memory")
    return _proxy_post("/memory", request.get_json(silent=True))

@app.route("/api/memory/<node_id>", methods=["DELETE"])
def route_delete_memory(node_id):
    return _proxy_delete(f"/memory/{node_id}")

@app.route("/api/memory/edge", methods=["POST"])
def route_memory_edge(): return _proxy_post("/memory/edge", request.get_json(silent=True))

@app.route("/api/chat", methods=["POST"])
def route_chat(): return _proxy_post("/chat", request.get_json(silent=True))

@app.route("/api/sos", methods=["POST"])
def route_sos(): return _proxy_post("/sos", request.get_json(silent=True))

@app.route("/api/med/confirm", methods=["POST"])
def route_med_confirm():
    data = request.get_json(silent=True) or {}
    # Validate med_id and type
    try:
        resp = requests.get(f"{API_URL}/memory", timeout=5, headers=get_api_headers())
        nodes = resp.json().get("nodes", [])
        med_node = next((n for n in nodes if n["id"] == data.get("med_id")), None)
        if not med_node or med_node.get("group") != "med":
            return jsonify({"error": "Invalid med_id"}), 400
    except Exception:
        return jsonify({"error": "Failed to validate med"}), 500
    return _proxy_post("/med/confirm", data)

@app.route("/api/med/status")
def route_med_status(): return _proxy_get("/med/status")


@app.route("/api/report", methods=["POST"])
def route_report(): return _proxy_post("/report")

@app.route("/api/onboarding", methods=["POST"])
def route_onboarding(): return _proxy_post("/onboarding", request.get_json(silent=True))

@app.route("/api/today")
def route_today(): return _proxy_get("/today")

@app.route("/api/diary/turn", methods=["POST"])
def route_diary_turn(): return _proxy_post("/diary/turn", request.get_json(silent=True))

@app.route("/api/diary/end", methods=["POST"])
def route_diary_end(): return _proxy_post("/diary/end", request.get_json(silent=True))

@app.route("/api/pending")
def route_pending(): return _proxy_get("/pending")

@app.route("/api/pending/<node_id>/approve", methods=["POST"])
def route_approve_pending(node_id): return _proxy_post(f"/pending/{node_id}/approve", request.get_json(silent=True))

@app.route("/api/timeline")
def route_timeline(): return _proxy_get("/timeline")

@app.route("/api/stats")
def route_stats(): return _proxy_get("/stats")

@app.route("/api/usage")
def route_usage(): return _proxy_get("/usage")

@app.route("/api/alerts/<alert_id>")
def route_alert_get(alert_id): return _proxy_get(f"/alerts/{alert_id}")

@app.route("/api/alerts/<alert_id>/ack", methods=["POST"])
def route_alert_ack(alert_id): return _proxy_post(f"/alerts/{alert_id}/ack", request.get_json(silent=True))

@app.route("/api/voice/preview", methods=["POST"], strict_slashes=False)
def route_voice_preview(): return _proxy_post("/api/voice/preview", request.get_json(silent=True))

@app.route("/api/voice/confirm", methods=["POST"], strict_slashes=False)
def route_voice_confirm(): return _proxy_post("/api/voice/confirm", request.get_json(silent=True))

# ---- Caregiver session auth ----
@app.route("/api/caregiver/login", methods=["POST"])
def caregiver_login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    if check_auth(username, password):
        session.clear()
        session['caregiver_authenticated'] = True
        session['caregiver_username'] = username
        session.permanent = False
        return jsonify({"status": "ok", "user": username}), 200
    return jsonify({"error": "invalid credentials"}), 401

@app.route("/api/caregiver/logout", methods=["POST"])
def caregiver_logout():
    session.pop('caregiver_authenticated', None)
    session.pop('caregiver_username', None)
    return jsonify({"status": "ok"}), 200

@app.route("/api/caregiver/me", methods=["GET"])
def caregiver_me():
    if session.get('caregiver_authenticated'):
        return jsonify({"authenticated": True, "user": session.get('caregiver_username')}), 200
    return jsonify({"authenticated": False}), 401

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1")
    app.run(host="0.0.0.0", port=5001, debug=debug_mode)
