from fastapi import APIRouter, Header, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from typing import Annotated, List, Optional, Dict, Any
import logging
import json
from pydantic import BaseModel

from sentio_engine.data.repositories import ClientRepository, StateRepository, HistoryRepository, MessageBufferRepository
from sentio_engine.core.engine import SentioEngine
from sentio_engine.llm.client import LLMGatewayClient
from sentio_engine.schemas.sentio_pb2 import EmotionalState, Stimulus
from pathlib import Path

# Initialize Router
router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize LLM Client
config_dir = Path(__file__).resolve().parent.parent.parent / "config"
llm_client = LLMGatewayClient(config_dir)

# Initialize Engine (Singleton reference from main usually, but we can re-instantiate as it is stateless)
engine = SentioEngine(config_dir)

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Dict[str, str]]
    stream: Optional[bool] = False
    # OpenAI allows other params, but we mainly care about these for proxying context

async def verify_api_key_proxy(
    authorization: Annotated[str, Header()]
) -> str:
    """
    Extracts Bearer token.
    In this Proxy mode, the client sends 'Authorization: Bearer <SENTIO_API_KEY>'.
    We validate it against our ClientRepository.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

    token = authorization.split(" ")[1]
    client = await ClientRepository.validate_api_key(token)
    if not client:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return token

@router.post("/v1/chat/completions", summary="OpenAI-compatible Proxy with Emotional Injection")
async def chat_completions_proxy(
    request: ChatCompletionRequest,
    api_key: str = Depends(verify_api_key_proxy),
    x_session_id: Optional[str] = Header(None)
):
    # 1. Determine Session ID
    session_id = x_session_id or "default_session"

    # 2. Extract User Message
    user_message = next((m for m in reversed(request.messages) if m["role"] == "user"), None)
    if user_message:
        content = user_message.get("content", "")
        # Save to Buffer
        await MessageBufferRepository.add_message(api_key, session_id, "user", content)

        # 3. Load Context
        state_doc = await StateRepository.load_state(api_key, session_id)
        emotional_state = EmotionalState()
        last_update = None
        if state_doc and state_doc.get("state_blob"):
            emotional_state.ParseFromString(state_doc["state_blob"])
            last_update = state_doc.get("last_update")
        else:
            emotional_state = engine.create_initial_state()

        recent_history = await MessageBufferRepository.get_recent_messages(api_key, session_id, limit=20)

        # 4. "Gatekeeper" & "Synthesizer" (Subconscious Processing)
        # Call Upstream LLM to analyze emotions and generate instruction
        current_emotions_dict = dict(emotional_state.emotions)
        reaction = await llm_client.generate_emotional_reaction(current_emotions_dict, recent_history, content)

        # 5. Update State with Delta
        delta_emotions = reaction.get("emotions", {})
        stimulus = Stimulus()
        for emotion, value in delta_emotions.items():
            # We assume value is the NEW intensity or delta?
            # Ideally the LLM returns the *new* value or an addition.
            # Let's assume it returns absolute values for simplicity or 0-1 range.
            # Or we treat it as a stimulus intensity.
            # Let's treat it as a Stimulus (intensity 0-1) to be processed by engine mechanics.
            if isinstance(value, (int, float)):
                stimulus.emotions[emotion] = float(value)

        new_timestamp = engine.process_stimulus(emotional_state, stimulus, last_update_time=last_update)

        # Log update
        await StateRepository.save_state(api_key, session_id, emotional_state.SerializeToString(), new_timestamp)
        await HistoryRepository.log_event(api_key, session_id, emotional_state, f"Subconscious Reaction: {delta_emotions}")

        # 6. Inject Instruction
        instruction = reaction.get("instruction", "")

        # Format emotions for context
        emotions_str = ", ".join([f"{k}: {v:.2f}" for k, v in emotional_state.emotions.items() if v > 0.1])
        mood = emotional_state.primary_mood

        system_injection = (
            f"\n[SENTIO SYSTEM CONTEXT]\n"
            f"User Session: {session_id}\n"
            f"Your Emotional State: {mood}\n"
            f"Active Emotions: {emotions_str}\n"
            f"INSTRUCTION FROM SUBCONSCIOUS: {instruction}"
        )

        # Insert into messages
        modified_messages = list(request.messages)
        if modified_messages and modified_messages[0]["role"] == "system":
            modified_messages[0]["content"] += system_injection
        else:
            modified_messages.insert(0, {"role": "system", "content": system_injection})

    else:
        modified_messages = request.messages

    # 7. Proxy to Upstream LLM
    async def response_generator():
        async for chunk in llm_client.chat_completion(modified_messages, stream=request.stream):
            yield chunk
            # Note: We are missing the "Save Assistant Response" step here because streaming makes it hard
            # to capture the full text without a complex accumulator.
            # For a production system, we'd need to parse the stream or use a callback.
            # We skip saving the assistant response to buffer for now to keep proxy latency low.

    return StreamingResponse(response_generator(), media_type="text/event-stream")
