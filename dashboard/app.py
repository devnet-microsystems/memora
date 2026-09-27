"""
Dashboard Application for Memora.
Provides a UI for caregivers and users to interact with the system.
"""

import os
import requests
from flask import Flask, render_template, jsonify

app = Flask(__name__)
API_URL = os.getenv("API_URL", "http://localhost:8000")

@app.route("/")
def landing():
    """Render the landing page."""
    return render_template("landing.html")

@app.route("/caregiver")
def caregiver():
    """Render the main caregiver dashboard."""
    # Try to get health status from FastAPI backend
    status = "offline"
    try:
        resp = requests.get(f"{API_URL}/health", timeout=2)
        if resp.status_code == 200:
            status = "online"
    except requests.RequestException:
        pass

    return render_template("index.html", api_url=API_URL, status=status)

@app.route("/patient")
def patient():
    """Render the patient voice interface."""
    return render_template("patient.html", api_url=API_URL)

@app.route("/judges")
def judges():
    """Render the 60-second summary page for hackathon evaluators."""
    return render_template("judges.html")

@app.route("/api/memory")
def get_memory():
    """Proxy for getting memory graph."""
    try:
        resp = requests.get(f"{API_URL}/memory", timeout=5)
        return jsonify(resp.json()), resp.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/memory/<node_id>", methods=["DELETE"])
def delete_memory(node_id):
    """Proxy for deleting a memory node."""
    try:
        resp = requests.delete(f"{API_URL}/memory/{node_id}", timeout=5)
        return jsonify(resp.json()), resp.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/memory", methods=["POST"])
def post_memory():
    """Proxy for adding a memory node."""
    try:
        resp = requests.post(f"{API_URL}/memory", json=request.json, timeout=30)
        return jsonify(resp.json()), resp.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/memory/edge", methods=["POST"])
def post_memory_edge():
    """Proxy for adding a memory edge."""
    try:
        resp = requests.post(f"{API_URL}/memory/edge", json=request.json, timeout=30)
        return jsonify(resp.json()), resp.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

from flask import request
@app.route("/api/chat", methods=["POST"])
def chat():
    """Proxy for chat endpoint."""
    try:
        data = request.json
        resp = requests.post(f"{API_URL}/chat", json=data, timeout=30)
        return jsonify(resp.json()), resp.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/report", methods=["POST"])
def generate_report():
    """Proxy for generating a report."""
    try:
        resp = requests.post(f"{API_URL}/report", timeout=30)
        return jsonify(resp.json()), resp.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
