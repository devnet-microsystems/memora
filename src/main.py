"""
Main entry point for Memora.
Initializes the agent, sets up dependencies, and starts the FastAPI application.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import os

from src.agent import MemoraAgent

# Setup logging
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
logger = logging.getLogger("memora.api")

# Pydantic Models
class ChatRequest(BaseModel):
    user_input: str
    lang: str = "en"

class ChatResponse(BaseModel):
    response: str

class HealthResponse(BaseModel):
    status: str
    encrypted: Optional[bool] = None

class ReportResponse(BaseModel):
    report: str
    stats: Optional[Dict[str, Any]] = None

class SOSRequest(BaseModel):
    patient_id: str
    type: str

class DiaryTurnRequest(BaseModel):
    session_id: str
    text: str
    lang: str = "en"

class DiaryEndRequest(BaseModel):
    session_id: str

class ApprovePendingRequest(BaseModel):
    content: Optional[str] = None

# FastAPI App Setup
app = FastAPI(title="Memora API", description="Personal AI Backend")

# Enable CORS for local dashboard and specific origins
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5001")
allow_origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def verify_api_key_middleware(request: Request, call_next):
    if request.url.path in ["/health", "/docs", "/openapi.json"]:
        return await call_next(request)
    
    if request.method == "OPTIONS":
        return await call_next(request)

    import hmac
    
    memora_key = os.getenv("MEMORA_API_KEY")
    if not memora_key:
        logger.warning("MEMORA_API_KEY non è impostata: modalità aperta!")
        return await call_next(request)
        
    x_memora_key = request.headers.get("X-Memora-Key")
    if x_memora_key is None or not hmac.compare_digest(x_memora_key.encode("utf-8"), memora_key.encode("utf-8")):
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    return await call_next(request)

# Global agent instance
agent: MemoraAgent = None

import sys
import threading
import time

def medication_scheduler_loop():
    logger.info("Medication scheduler started.")
    from src.schedule import med_state
    while True:
        try:
            if not agent:
                time.sleep(5)
                continue
            
            now = now_local()
            for node_id, data in agent.memory.graph.nodes(data=True):
                if data.get("type") == "med":
                    state = med_state(data, now)
                    if state == "missed":
                        meta = data.get("meta") or {}
                        today_str = now.strftime("%Y-%m-%d")
                        if meta.get("last_escalation_date") != today_str:
                            content = data.get("content", "Medication")
                            schedule = data.get("schedule", "Unknown time")
                            
                            logger.warning(f"Escalating missed medication: {node_id}")
                            # operational alert (no embedding call: it must be instant and never reach the LLM context)
                            alert_id = f"alert_missed_{node_id}_{int(time.time()*1000)}"
                            agent.memory.add_nodes([{
                                "id": alert_id, "type": "alert", "skip_embedding": True,
                                "content": f"Missed medication: {content} at {schedule}",
                                "meta": {"status": "open", "source": "med_scheduler", "med_id": node_id},
                            }])

                            meta["last_escalation_date"] = today_str
                            agent.memory.update_node(node_id, meta_patch={"last_escalation_date": today_str},
                                                     last_status="no_response")

                            agent.memory.log_event("med_missed", {"med_id": node_id})
                            
        except Exception as e:
            logger.error(f"Error in medication scheduler loop: {e}")
            
        time.sleep(30)

from src.timeutil import now_local

@app.on_event("startup")
async def startup_event():
    """Initialize agent and dependencies on startup."""
    global agent
    logger.info(f"Python: {sys.executable}")
    logger.info(f"sys.path: {sys.path[:3]}")
    logger.info("Initializing Memora Agent and dependencies...")
    agent = MemoraAgent()
    
    # Auto-seed if DB is empty
    import os
    if os.getenv("AUTO_SEED", "1") != "0":
        logger.info("Checking if database needs seeding...")
        agent.memory.load_seed_if_empty()
        
    scheduler_thread = threading.Thread(target=medication_scheduler_loop, daemon=True)
    scheduler_thread.start()
        
    logger.info("Initialization complete.")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health status."""
    import os
    try:
        from sqlcipher3 import dbapi2 as sqlite
        has_sqlcipher = True
    except ImportError:
        has_sqlcipher = False
    
    db_key = os.getenv("DB_KEY")
    is_encrypted = has_sqlcipher and bool(db_key)
    
    return {"status": "ok", "encrypted": is_encrypted}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat message through the Memora agent.
    """
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    try:
        response_text = agent.respond(request.user_input, lang=request.lang)
        return {"response": response_text}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class MemoryNodeRequest(BaseModel):
    id: str
    type: str
    content: str
    schedule: str = None

class MemoryEdgeRequest(BaseModel):
    source: str
    target: str
    relation: str

@app.get("/memory")
async def get_memory() -> Dict[str, Any]:
    """
    Export the memory graph for the dashboard visualization.
    """
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    return agent.memory.export_graph()

import re
ALLOWED_NODE_TYPES = {"person", "place", "event", "habit", "med", "preference", "patologia", "routine", "caa_button", "interaction", "pending", "alert"}

@app.post("/memory")
async def add_memory(request: MemoryNodeRequest):
    """
    Add a new memory node to the graph.
    """
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    if not re.match(r"^[A-Za-z0-9_-]{1,64}$", request.id):
        raise HTTPException(status_code=422, detail="Invalid ID format")
    if request.type not in ALLOWED_NODE_TYPES:
        raise HTTPException(status_code=422, detail="Invalid node type")
    if request.content and len(request.content) > 500:
        raise HTTPException(status_code=422, detail="Content too long")
    try:
        agent.memory_add(request.id, request.type, request.content, request.schedule)
        return {"status": "success", "id": request.id}
    except Exception as e:
        logger.error(f"Failed to add memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/edge")
async def add_memory_edge(request: MemoryEdgeRequest):
    """
    Add a new edge between memory nodes.
    """
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    try:
        agent.memory.add_edge(request.source, request.target, request.relation)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to add edge: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.delete("/memory/{node_id}")
async def delete_memory(node_id: str):
    """
    Right to be forgotten: delete a memory node by ID.
    """
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    try:
        agent.memory.delete(node_id)
        return {"status": "deleted", "node_id": node_id}
    except Exception as e:
        logger.error(f"Failed to delete node {node_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from src.timeutil import now_local

@app.post("/sos")
async def handle_sos(request: SOSRequest):
    """Handle emergency SOS request."""
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    now = now_local()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    ora = now.strftime("%H:%M")
    
    logger.warning(f"SOS_RECEIVED | patient={request.patient_id} | timestamp={timestamp}")
    
    alert_id = f"sos_{now.strftime('%Y%m%d%H%M%S%f')}"
    try:
        # Written directly as an *open alert* (instant: no embedding, no LLM). The old path went through the
        # human-approval queue and two embedding calls, so a real SOS could take 40+ seconds to appear.
        agent.memory.add_nodes([{
            "id": alert_id, "type": "alert", "skip_embedding": True,
            "content": f"SOS from {request.patient_id} at {ora}",
            "meta": {"status": "open", "source": "patient_sos", "patient_id": request.patient_id},
        }])
        agent.memory.log_event("sos", data={"patient_id": request.patient_id, "type": request.type})
        return {"status": "ok", "alert_id": alert_id}
    except Exception as e:
        logger.error(f"Failed to save SOS alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alerts/{alert_id}")
async def get_alert(alert_id: str):
    """Return the status of an alert so the patient app can wait for a real acknowledgement."""
    if not agent or not agent.memory.graph.has_node(alert_id):
        raise HTTPException(status_code=404, detail="Alert not found")
    data = agent.memory.graph.nodes[alert_id]
    if data.get("type") != "alert":
        raise HTTPException(status_code=404, detail="Alert not found")
    meta = data.get("meta") or {}
    return {"id": alert_id, "status": meta.get("status", "open"), "acknowledged_at": meta.get("acknowledged_at")}

@app.post("/alerts/{alert_id}/ack")
async def ack_alert(alert_id: str):
    """A caregiver acknowledges an alert (taken in charge)."""
    if not agent or not agent.memory.graph.has_node(alert_id):
        raise HTTPException(status_code=404, detail="Alert not found")
    if agent.memory.graph.nodes[alert_id].get("type") != "alert":
        raise HTTPException(status_code=404, detail="Alert not found")
    agent.memory.update_node(alert_id, meta_patch={"status": "acknowledged", "acknowledged_at": time.time()})
    agent.memory.log_event("alert_ack", data={"alert_id": alert_id})
    return {"status": "acknowledged", "id": alert_id}

class MedConfirmRequest(BaseModel):
    med_id: str
    status: str

@app.post("/med/confirm")
async def confirm_med(request: MedConfirmRequest):
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    try:
        now = now_local()
        today_str = now.strftime("%Y-%m-%d")
        
        if agent.memory.graph.has_node(request.med_id):
            node_data = agent.memory.graph.nodes[request.med_id]
            meta = node_data.get("meta") or {}
            content = node_data.get("content", "Medication")
            schedule = node_data.get("schedule", "Unknown time")
            
            if request.status == "snoozed":
                snooze_date = meta.get("snooze_count_date")
                snooze_count = meta.get("snooze_count", 0)
                if snooze_date != today_str:
                    snooze_count = 0
                    
                if snooze_count < 2:
                    meta["snoozed_until"] = now.timestamp() + 600 # 10 min
                    meta["snooze_count"] = snooze_count + 1
                    meta["snooze_count_date"] = today_str
                    agent.memory.update_node(request.med_id, meta_patch=meta)
                else:
                    return {"status": "error", "message": "Max snoozes reached"}
                    
            elif request.status in ["denied", "unsure"]:
                escalation_key = f"last_{request.status}_date"
                if meta.get(escalation_key) != today_str:
                    agent.notify_caregiver(f"{content} alle {schedule} marcato come {request.status}")
                    meta[escalation_key] = today_str
                    agent.memory.update_node(request.med_id, meta_patch=meta)
                    
        if request.status != "snoozed":
            agent.memory.update_med_status(request.med_id, request.status, now.timestamp())
            
        agent.memory.log_event("med_" + request.status, data={"med_id": request.med_id})
        logger.info(f"Medication {request.med_id} marked as {request.status}")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Failed to confirm med: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/med/status")
async def get_med_status():
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    meds = []
    from datetime import datetime
    now = now_local()
    from src.schedule import med_state, occurs_on
    for node_id, data in agent.memory.graph.nodes(data=True):
        if data.get("type") == "med":
            last_status = data.get("last_status")
            last_conf = data.get("last_confirmation")
            status = "none"
            if last_status and last_conf:
                conf_date = datetime.fromtimestamp(last_conf, now.tzinfo).date()
                if conf_date == now.date():
                    status = last_status
            
            due_time_str = None
            occ_time = occurs_on(data.get("schedule", ""), now.date())
            if occ_time:
                due_time_str = occ_time.strftime("%H:%M")
                
            meds.append({
                "id": node_id,
                "content": data.get("content"),
                "schedule": data.get("schedule"),
                "last_status": status,
                "last_confirmation": last_conf,
                "med_state": med_state(data, now),
                "due_time": due_time_str
            })
    return {"meds": meds}

from src.schedule import occurs_on

@app.get("/today")
async def get_today(lang: str = "en"):
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
        
    from datetime import datetime
    now = now_local()
    now_iso = now.isoformat()
    
    # Weekday & Date Label
    weekdays_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekdays_it = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    months_en = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    months_it = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    
    wd = weekdays_it[now.weekday()] if lang == "it" else weekdays_en[now.weekday()]
    mo = months_it[now.month - 1] if lang == "it" else months_en[now.month - 1]
    date_label = f"{now.day} {mo} {now.year}"
    
    # Part of day
    hour = now.hour
    if hour < 12:
        part_of_day = "Buongiorno" if lang == "it" else "Good morning"
    elif hour < 18:
        part_of_day = "Buon pomeriggio" if lang == "it" else "Good afternoon"
    else:
        part_of_day = "Buonasera" if lang == "it" else "Good evening"
        
    # Patient name
    patient_name = None
    if agent.memory.graph.has_node("patient"):
        patient_data = agent.memory.graph.nodes["patient"]
        meta = patient_data.get("meta", {})
        if "name" in meta and meta["name"]:
            patient_name = meta["name"]
        else:
            content = patient_data.get("content", "")
            if content:
                patient_name = content.split()[0].rstrip(",.")
                
    items = []
    
    # Calculate items
    for node_id, data in agent.memory.graph.nodes(data=True):
        n_type = data.get("type")
        if n_type in ["med", "event", "habit"]:
            schedule = data.get("schedule")
            if schedule:
                occ_time = occurs_on(schedule, now.date())
                if occ_time:
                    status = "none"
                    if n_type == "med":
                        last_status = data.get("last_status")
                        last_conf = data.get("last_confirmation")
                        if last_status and last_conf:
                            conf_date = datetime.fromtimestamp(last_conf, now.tzinfo).date()
                            if conf_date == now.date():
                                status = last_status
                    
                    from src.schedule import med_state
                    items.append({
                        "id": node_id,
                        "kind": n_type,
                        "time": occ_time.strftime("%H:%M"),
                        "text": data.get("content", ""),
                        "status": status,
                        "med_state": med_state(data, now) if n_type == "med" else None,
                        "due_time": occ_time.strftime("%H:%M")
                    })
                    
    # Sort items by time
    items.sort(key=lambda x: x["time"])
    
    return {
        "now_iso": now_iso,
        "weekday": wd,
        "date_label": date_label,
        "part_of_day": part_of_day,
        "patient_name": patient_name,
        "items": items
    }

import os
import json

class OnboardingRequest(BaseModel):
    interview_text: str

@app.post("/onboarding")
async def onboarding_interview(request: OnboardingRequest):
    """
    Process caregiver onboarding interview and populate memory graph.
    """
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    result = agent.process_onboarding_interview(request.interview_text)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("detail"))
    return result




@app.get("/stats")
async def get_stats(days: int = 7):
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")
    return agent.memory.get_stats(days)

@app.post("/report", response_model=ReportResponse)
async def generate_report(lang: str = "en"):
    """
    Generate a weekly report using the Ultra model based on stats.
    """
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
        
    try:
        stats = agent.memory.get_stats(7)
        patient_name = "Patient"
        if agent.memory.graph.has_node("patient"):
            p_data = agent.memory.graph.nodes["patient"]
            meta_name = p_data.get("meta", {}).get("name")
            if meta_name:
                patient_name = meta_name
            else:
                content = p_data.get("content", "")
                if content:
                    patient_name = content.split(",")[0]

        import json
        stats_json = json.dumps(stats, indent=2)
        
        prompt = (
            f"Write a caregiver report from this data only. Max 180 words. Sections: Summary, Changes vs previous week, Notes. "
            f"Quote numbers exactly. If fewer than 3 days of data, say so. No diagnosis, no clinical conclusions, no medical advice; "
            f"you may say the caregiver can share these numbers with the patient's clinician. If simulated=true start with 'SIMULATED DEMO DATA'.\n"
            f"Patient: {patient_name}\n"
            f"Data:\n{stats_json}"
        )
        messages = [{"role": "user", "content": prompt}]
        
        try:
            report_text = agent.nebius.chat(model=agent.nebius.model_ultra, messages=messages)
        except Exception as llm_err:
            logger.error(f"Ultra LLM error: {llm_err}")
            report_text = "Error generating AI report text, but stats are available."
            
        return {"report": report_text, "stats": stats}
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/diary/turn")
async def diary_turn(req: DiaryTurnRequest):
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")
    reply = agent.diary_turn(req.session_id, req.text, req.lang)
    return {"reply": reply}

@app.post("/diary/end")
async def diary_end(req: DiaryEndRequest):
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")
    saved = agent.diary_end(req.session_id)
    return {"saved": saved}

@app.get("/pending")
async def get_pending():
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")
    pendings = []
    for node_id, data in agent.memory.graph.nodes(data=True):
        if data.get("type") == "pending":
            meta = data.get("meta", {})
            pendings.append({
                "id": node_id,
                "content": data.get("content", ""),
                "proposed_type": meta.get("proposed_type", "fact"),
                "event_date": meta.get("event_date", ""),
                "source": meta.get("source", "")
            })
    return pendings

@app.post("/pending/{id}/approve")
async def approve_pending(id: str, req: ApprovePendingRequest):
    if not agent or not agent.memory.graph.has_node(id):
        raise HTTPException(status_code=404, detail="Node not found")
    data = agent.memory.graph.nodes[id]
    if data.get("type") != "pending":
        raise HTTPException(status_code=403, detail="Only pending nodes can be approved")
    meta = data.get("meta", {})
    new_type = meta.get("proposed_type", "fact")
    new_content = req.content if req.content else data.get("content", "")
    agent.memory.update_node(id, type=new_type, content=new_content, meta_patch={"approved": True})
    if agent.memory.graph.has_node("patient"):
        agent.memory.add_edge("patient", id, "remembers")
    agent.memory.log_event("approved")
    return {"status": "success"}

@app.get("/timeline")
async def get_timeline():
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")
    nodes = []
    for node_id, data in agent.memory.graph.nodes(data=True):
        if data.get("type") != "pending" and data.get("meta", {}).get("source") == "diary":
            meta = data.get("meta", {})
            date_val = meta.get("event_date", "")
            if not date_val:
                date_val = str(data.get("timestamp", ""))
            nodes.append({
                "id": node_id,
                "content": data.get("content", ""),
                "event_date": date_val
            })
    nodes.sort(key=lambda x: x["event_date"])
    return nodes

@app.get("/usage")
async def get_usage():
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")
    return agent.nebius.get_usage()

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)
