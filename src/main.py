"""
Main entry point for Memora.
Initializes the agent, sets up dependencies, and starts the FastAPI application.
"""

import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

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

class ChatResponse(BaseModel):
    response: str

class HealthResponse(BaseModel):
    status: str

class ReportResponse(BaseModel):
    report: str

# FastAPI App Setup
app = FastAPI(title="Memora API", description="Personal AI Backend")

# Enable CORS for local dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
agent: MemoraAgent = None

import sys

@app.on_event("startup")
async def startup_event():
    """Initialize agent and dependencies on startup."""
    global agent
    logger.info(f"Python: {sys.executable}")
    logger.info(f"sys.path: {sys.path[:3]}")
    logger.info("Initializing Memora Agent and dependencies...")
    agent = MemoraAgent()
    logger.info("Initialization complete.")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health status."""
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat message through the Memora agent.
    """
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    try:
        response_text = agent.respond(request.user_input)
        return {"response": response_text}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class MemoryNodeRequest(BaseModel):
    id: str
    type: str
    content: str

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

@app.post("/memory")
async def add_memory(request: MemoryNodeRequest):
    """
    Add a new memory node to the graph.
    """
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    try:
        agent.memory_add(request.id, request.type, request.content)
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

@app.post("/report", response_model=ReportResponse)
async def generate_report():
    """
    Generate a weekly report using the Ultra model.
    """
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
        
    try:
        graph_data = agent.memory.export_graph()
        nodes = graph_data.get("nodes", [])
        
        if not nodes:
            memory_text = "Nessun ricordo registrato."
        else:
            memory_text = "\n".join([f"- [{n.get('group', 'unknown')}] {n.get('label', '')}" for n in nodes])
            
        prompt = (
            "Genera un report settimanale sintetico sullo stato cognitivo e "
            "comportamentale dell'utente basandoti *esclusivamente* sui seguenti ricordi estratti dalla memoria.\n"
            "Non inventare dati. Se mancano informazioni, dillo esplicitamente.\n"
            "Non dire 'non ho accesso alla memoria' perché ti sto passando il contesto qui sotto.\n"
            "Mantieni un tono professionale da caregiver.\n\n"
            "RICORDI IN MEMORIA:\n"
            f"{memory_text}"
        )
        messages = [{"role": "user", "content": prompt}]
        report_text = agent.nebius.chat(model=agent.nebius.model_ultra, messages=messages)
        return {"report": report_text}
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
