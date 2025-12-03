from fastapi import FastAPI, Request, Response, Depends, HTTPException, Header, Body
from pathlib import Path
import hashlib
from typing import Annotated, Optional

from sentio_engine.core.engine import SentioEngine
from sentio_engine.schemas.sentio_pb2 import Stimulus, Report, HealthStatus, PersonalityProfile, PersonalityTrait, EmotionalState
from contextlib import asynccontextmanager
from sentio_engine.data.mongo import MongoManager
from sentio_engine.data.repositories import ClientRepository, StateRepository
from pydantic import BaseModel

# --- Models ---
class RegisterClientRequest(BaseModel):
    client_name: str

class AgentText(BaseModel):
    text: str
    session_id: str

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

    # 3. Save State
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

    # 2. Generate Report (syncs decay)
    report = engine.get_report(emotional_state, last_update_time=last_update)

    # 3. Save State (because decay might have updated it)
    import datetime
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
