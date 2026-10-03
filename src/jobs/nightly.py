"""
Nightly Consolidation Job for Memora.
Designed to run on Nebius Serverless Jobs or locally via cron.
Consolidates memories, regenerates embeddings, and creates a daily report.
"""

import os
import time
import shutil
import logging
from datetime import datetime
from src.timeutil import now_local
from dotenv import load_dotenv

from src.memory import MemoryGraph
from src.nebius_client import NebiusClient

# Load environment variables
load_dotenv()

# Configure logging for jobs (console + file)
log_formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")

# File handler
os.makedirs("logs", exist_ok=True)
file_handler = logging.FileHandler("logs/nightly_job.log")
file_handler.setFormatter(log_formatter)

# Stream handler (stdout)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)

logger = logging.getLogger("memora.jobs.nightly")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


def check_medications(memory: MemoryGraph):
    """Check if any medication is overdue by more than 30 minutes."""
    logger.info("Checking medications schedule...")
    now = now_local()
    from src.schedule import occurs_on
    for node_id, data in memory.graph.nodes(data=True):
        if data.get("type") == "med" and data.get("schedule"):
            schedule = data.get("schedule")
            try:
                occ_time = occurs_on(schedule, now.date())
                if not occ_time:
                    continue
                sched_dt = datetime.combine(now.date(), occ_time)
                diff = (now.replace(tzinfo=None) - sched_dt).total_seconds() / 60.0
                if diff > 30:
                    last_status = data.get("last_status")
                    last_conf = data.get("last_confirmation")
                    status = "none"
                    if last_status and last_conf:
                        conf_date = datetime.fromtimestamp(last_conf, now.tzinfo).date()
                        if conf_date == now.date():
                            status = last_status
                    if status in ["none", "no_response"]:
                        logger.warning(f"MEDICATION OVERDUE: {node_id} was scheduled for {schedule}. Status: {status}")
            except Exception as e:
                logger.error(f"Error checking schedule for {node_id}: {e}")

def run_nightly_consolidation():
    """Execute the nightly batch operations."""
    logger.info("--- Starting Nightly Consolidation Job ---")
    
    # Initialize standalone modules (No dependency on FastAPI)
    memory = MemoryGraph()
    nebius = NebiusClient()
    
    current_time = time.time()
    one_day_ago = current_time - (24 * 3600)
    
    # 0. Check medications
    check_medications(memory)
    
    # 1. Retrieve new interactions of the day
    logger.info("1. Retrieving new interactions from the last 24h...")
    new_nodes = []
    for node_id, data in memory.graph.nodes(data=True):
        ts = data.get("timestamp", 0)
        if ts >= one_day_ago:
            new_nodes.append((node_id, data))
    logger.info(f"Found {len(new_nodes)} new interactions.")
    
    # 2. Regenerate missing embeddings
    logger.info("2. Checking for missing embeddings...")
    missing_count = 0
    for node_id, data in memory.graph.nodes(data=True):
        content = data.get("content")
        if content and not data.get("embedding"):
            logger.info(f"Regenerating embedding for node: {node_id}")
            try:
                # NebiusClient automatically handles redaction for API privacy
                new_emb = nebius.embed(content)
                # Overwrite node to save new embedding locally
                memory.add_node(node_id, data.get("type", "unknown"), content)
                missing_count += 1
            except Exception as e:
                logger.error(f"Failed to embed node {node_id}: {e}")
    logger.info(f"Regenerated {missing_count} missing embeddings.")
    
    # 3. Consolidate duplicate or similar nodes
    logger.info("3. Consolidating duplicate nodes...")
    consolidated = 0
    nodes_to_delete = []
    all_nodes = list(memory.graph.nodes(data=True))
    
    for i in range(len(all_nodes)):
        for j in range(i + 1, len(all_nodes)):
            id1, data1 = all_nodes[i]
            id2, data2 = all_nodes[j]
            
            # Skip if already marked for deletion
            if id1 in nodes_to_delete or id2 in nodes_to_delete:
                continue
                
            emb1, emb2 = data1.get("embedding"), data2.get("embedding")
            if emb1 and emb2:
                # Use internal cosine similarity method for the batch job
                score = memory._cosine_similarity(emb1, emb2)
                if score > 0.95 and data1.get("type") == data2.get("type"):
                    logger.info(f"Found duplicates: {id1} and {id2} (score: {score:.2f})")
                    nodes_to_delete.append(id2)  # Retain id1, drop id2
                    consolidated += 1

    for nid in nodes_to_delete:
        memory.delete(nid)
    logger.info(f"Consolidated {consolidated} redundant memories.")
    
    # 4. Generate daily report with Nemotron 3 Ultra
    logger.info("4. Generating daily report via Nemotron 3 Ultra...")
    try:
        if new_nodes:
            summary_text = "\n".join([f"- {d.get('content')}" for _, d in new_nodes])
            prompt = (
                "Genera un report giornaliero sintetico basato su questi nuovi ricordi:\n"
                f"{summary_text}\n"
                "Usa un tono professionale da caregiver e analizza eventuali cambiamenti o segnali da monitorare."
            )
            report = nebius.chat(
                model=nebius.model_ultra,
                messages=[{"role": "user", "content": prompt}]
            )
            logger.info("Daily report generated successfully.")
            # In production, save to DB or email the report.
        else:
            logger.info("No new interactions today. Skipping report.")
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
    
    # 5. Encrypted Backup of the graph
    logger.info("5. Performing database backup...")
    try:
        db_path = memory.db_path
        if os.path.exists(db_path):
            backup_dir = os.path.join(os.path.dirname(db_path), "backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = now_local().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"memora_backup_{timestamp}.db")
            
            # Local DB is already encrypted via SQLCipher if configured
            shutil.copy2(db_path, backup_path)
            logger.info(f"Backup saved to {backup_path}")
        else:
            logger.warning(f"Source DB {db_path} not found. Cannot backup.")
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        
    logger.info("--- Nightly Consolidation Job Completed ---")

if __name__ == "__main__":
    run_nightly_consolidation()
