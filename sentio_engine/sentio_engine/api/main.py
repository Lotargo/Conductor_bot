from fastapi import FastAPI, Request, Response, Depends, HTTPException, Header, Body
from pathlib import Path
import hashlib
import datetime
import logging
from typing import Annotated, Optional

from sentio_engine.core.engine import SentioEngine
from sentio_engine.schemas.sentio_pb2 import Stimulus, Report, HealthStatus, PersonalityProfile, PersonalityTrait, EmotionalState
from contextlib import asynccontextmanager
from sentio_engine.data.mongo import MongoManager
from sentio_engine.data.repositories import ClientRepository, StateRepository, HistoryRepository
from sentio_engine.api import proxy # Import the new proxy module
from pydantic import BaseModel

# --- Models ---
class RegisterClientRequest(BaseModel):
    client_name: str

class AgentText(BaseModel):
    text: str
    session_id: str

logger = logging.getLogger(__name__)

# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application lifecycle."""
    print("App starting...")
    # Trigger DB connection
    MongoManager.get_client()
    yield
    print("App stopping...")
    MongoManager.close()

# --- App & Engine Init ---
app = FastAPI(title="Sentio Engine API", lifespan=lifespan)

# Include the Proxy Router
app.include_router(proxy.router)

config_path = Path(__file__).resolve().parent.parent.parent / "config"
# Engine is now stateless singleton
engine = SentioEngine(config_path=config_path)

# --- Dependencies ---
async def verify_api_key(
    x_api_key: Annotated[str, Header()]
) -> str:
    """Verifies API key and returns it if valid."""
    client = await ClientRepository.validate_api_key(x_api_key)
    if not client:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

# --- Helper Functions ---

async def _check_and_update_complex_states(api_key: str, session_id: str) -> list[str]:
    """
    Checks for active complex states (feelings) based on history.
    This is a simplified implementation. In a real scenario, we would iterate
    over engine.feelings_definitions and run queries for each.
    """
    active_states = []

    # Example: Check for "depression" (assuming definition exists)
    # Definition: Sadness > 0.5 for a period (simplified here to average > 0.5 in last 14 days)
    # We use a shorter window for testing/demo or load from config.

    # Load feeling definitions from engine to be dynamic
    if not hasattr(engine, 'feelings_definitions'):
        return []

    now = datetime.datetime.utcnow()

    for feeling_name, definition in engine.feelings_definitions.items():
         # Simplified logic: If "sadness" is a condition, check average sadness
         # This is an adaptation of the SQL logic to Mongo aggregation
         conditions = definition.get("conditions", [])
         is_active = True

         if not conditions:
             is_active = False

         for condition in conditions:
             emotion = condition["emotion"]
             threshold = condition["threshold"]
             operator = condition["operator"]

             # Check stats for the last 14 days (or defined duration)
             duration_hours = definition.get("required_duration_hours", 24 * 14)
             start_time = now - datetime.timedelta(hours=duration_hours)

             stats = await HistoryRepository.get_stats_in_window(api_key, session_id, emotion, start_time)

             if stats["count"] == 0:
                 is_active = False
                 break

             # A very basic check: is the AVERAGE intensity matching the condition?
             # The SQL logic was strict (NO violation). The Mongo logic here is "Average is matching".
             # This is a heuristic change for performance in hybrid memory.
             val = stats["avg"]

             if operator == ">=" and val < threshold:
                 is_active = False
             elif operator == "<=" and val > threshold:
                 is_active = False

             if not is_active:
                 break

         if is_active:
             active_states.append(feeling_name)

    return active_states

# --- Endpoints ---

@app.post("/register_client", summary="Register a new client adapter")
async def register_client(request: RegisterClientRequest):
    """
    Registers a new client application/adapter and returns an API Key.
    """
    api_key = await ClientRepository.register_client(request.client_name)
    return {"api_key": api_key, "client_name": request.client_name}

@app.post("/stimulus", status_code=204, summary="Apply stimulus to engine")
async def apply_stimulus(
    request: Request,
    x_session_id: Annotated[str, Header()],
    api_key: str = Depends(verify_api_key)
):
    """
    Applies a stimulus. Requires X-Session-ID header and X-Api-Key.
    """
    body = await request.body()
    stimulus = Stimulus()
    try:
        stimulus.ParseFromString(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Protobuf parsing error.")

    # 1. Load State
    state_doc = await StateRepository.load_state(api_key, x_session_id)

    emotional_state = EmotionalState()
    last_update = None
    if state_doc and state_doc.get("state_blob"):
        emotional_state.ParseFromString(state_doc["state_blob"])
        last_update = state_doc.get("last_update")
    else:
        # Create new default state
        emotional_state = engine.create_initial_state()

    # 2. Process
    new_timestamp = engine.process_stimulus(emotional_state, stimulus, last_update_time=last_update)

    # 3. Log History (Hybrid Memory)
    cause = emotional_state.cause
    await HistoryRepository.log_event(api_key, x_session_id, emotional_state, cause)

    # 4. Save State
    await StateRepository.save_state(
        api_key=api_key,
        session_id=x_session_id,
        state_data=emotional_state.SerializeToString(),
        last_update=new_timestamp
    )

    return Response(status_code=204)

@app.get("/report", response_class=Response, summary="Get current state report")
async def get_engine_report(
    x_session_id: Annotated[str, Header()],
    api_key: str = Depends(verify_api_key)
):
    # 1. Load State
    state_doc = await StateRepository.load_state(api_key, x_session_id)

    emotional_state = EmotionalState()
    last_update = None
    if state_doc and state_doc.get("state_blob"):
        emotional_state.ParseFromString(state_doc["state_blob"])
        last_update = state_doc.get("last_update")
    else:
        emotional_state = engine.create_initial_state()

    # 2. Check Complex States (Hybrid Memory Analysis)
    active_complex_states = await _check_and_update_complex_states(api_key, x_session_id)

    # 3. Generate Report (syncs decay)
    report = engine.get_report(
        emotional_state,
        last_update_time=last_update,
        complex_states=active_complex_states
    )

    # 4. Save State (because decay might have updated it)
    new_timestamp = datetime.datetime.utcnow()

    await StateRepository.save_state(
        api_key=api_key,
        session_id=x_session_id,
        state_data=emotional_state.SerializeToString(),
        last_update=new_timestamp
    )

    serialized_report = report.SerializeToString()
    return Response(content=serialized_report, media_type="application/protobuf")


# --- Text Processing ---
import re
import json

def _parse_emotions_from_text(text: str) -> dict | None:
    match = re.search(r"\[SENTIO_EMO_STATE\](.*?)\[/SENTIO_EMO_STATE\]", text, re.DOTALL)
    if not match:
        return None
    json_str = match.group(1).strip()
    try:
        emotions = json.loads(json_str)
        if isinstance(emotions, dict):
            return emotions
    except json.JSONDecodeError:
        return None
    return None

@app.post("/process_agent_text", status_code=204, summary="Extract emotions from agent text")
async def process_agent_text(
    payload: AgentText,
    api_key: str = Depends(verify_api_key)
):
    """
    Parses [SENTIO_EMO_STATE] tags from text and updates state.
    Payload must include 'session_id'.
    """
    emotions_to_process = _parse_emotions_from_text(payload.text)

    if emotions_to_process:
        stimulus = Stimulus()
        for emotion, intensity in emotions_to_process.items():
            if isinstance(intensity, (int, float)):
                stimulus.emotions[emotion] = float(intensity)

        if stimulus.emotions:
            # Same logic as apply_stimulus
            state_doc = await StateRepository.load_state(api_key, payload.session_id)

            emotional_state = EmotionalState()
            last_update = None
            if state_doc and state_doc.get("state_blob"):
                emotional_state.ParseFromString(state_doc["state_blob"])
                last_update = state_doc.get("last_update")
            else:
                emotional_state = engine.create_initial_state()

            new_timestamp = engine.process_stimulus(emotional_state, stimulus, last_update_time=last_update)

            # Log History
            await HistoryRepository.log_event(api_key, payload.session_id, emotional_state, "Agent Text Reaction")

            await StateRepository.save_state(
                api_key=api_key,
                session_id=payload.session_id,
                state_data=emotional_state.SerializeToString(),
                last_update=new_timestamp
            )

    return Response(status_code=204)

# --- Service Endpoints ---
@app.get("/health", response_class=Response)
def get_health_status():
    health_status = HealthStatus(status="OK")
    return Response(content=health_status.SerializeToString(), media_type="application/protobuf")

# --- Personality Management (Global/Admin?) ---
# Note: Currently personality is loaded from files globally.
# Modifying it at runtime affects ALL clients if we don't move it to DB.
# For now, leaving as is but acknowledging it changes the 'template'.
@app.get("/personality", response_class=Response)
def get_personality_profile():
    profile = PersonalityProfile()
    for trait_name, trait_data in engine.belief_system.items():
        trait = PersonalityTrait(
            value=trait_data["value"],
            description=trait_data["description"]
        )
        profile.traits[trait_name].CopyFrom(trait)
    return Response(content=profile.SerializeToString(), media_type="application/protobuf")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
