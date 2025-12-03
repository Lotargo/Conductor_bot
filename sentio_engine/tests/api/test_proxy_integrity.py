import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from sentio_engine.api.main import app

# Need to import Report for the mock above to work if strictly typed, but MagicMock handles it.
from sentio_engine.schemas.sentio_pb2 import Report

# Mock Dependencies
@pytest.fixture
def mock_deps():
    # Patching methods directly to ensure they are AsyncMocks
    with patch("sentio_engine.api.proxy.llm_client") as mock_llm, \
         patch("sentio_engine.api.proxy.ClientRepository.validate_api_key", new_callable=AsyncMock) as mock_validate, \
         patch("sentio_engine.api.proxy.StateRepository.load_state", new_callable=AsyncMock) as mock_load, \
         patch("sentio_engine.api.proxy.StateRepository.save_state", new_callable=AsyncMock) as mock_save, \
         patch("sentio_engine.api.proxy.MessageBufferRepository.add_message", new_callable=AsyncMock) as mock_add_msg, \
         patch("sentio_engine.api.proxy.MessageBufferRepository.get_recent_messages", new_callable=AsyncMock) as mock_get_msgs, \
         patch("sentio_engine.api.proxy.HistoryRepository.log_event", new_callable=AsyncMock) as mock_log_event, \
         patch("sentio_engine.api.proxy.engine") as mock_engine:

        # Setup Auth
        mock_validate.return_value = {"client_name": "test"}

        # Setup State
        mock_load.return_value = {}

        # Setup Buffer
        mock_get_msgs.return_value = []

        # Setup Engine
        mock_engine.create_initial_state = MagicMock()
        mock_engine.process_stimulus = MagicMock(return_value=None)
        mock_engine.get_report = MagicMock()

        mock_state = MagicMock()
        mock_state.emotions = {}
        mock_state.primary_mood = "Neutral"
        mock_state.SerializeToString.return_value = b""
        mock_engine.create_initial_state.return_value = mock_state
        mock_engine.get_report.return_value = Report() # Dummy report

        # Setup LLM Subconscious
        mock_llm.generate_emotional_reaction = AsyncMock(return_value={
            "emotions": {},
            "instruction": "Be kind."
        })

        # Setup LLM Chat Completion (Async Generator)
        async def mock_stream(*args, **kwargs):
            yield b"Hello"
        mock_llm.chat_completion = MagicMock(side_effect=mock_stream)

        yield mock_llm

def test_proxy_integrity_user_message_preserved(mock_deps):
    client = TestClient(app)

    original_text = "I am very sad and I need help."
    messages = [
        {"role": "system", "content": "You are a bot."},
        {"role": "user", "content": original_text}
    ]

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-3.5-turbo",
            "messages": messages,
            "stream": True
        },
        headers={"Authorization": "Bearer test_key"}
    )

    assert response.status_code == 200

    # Verify what was sent to the upstream LLM
    mock_llm = mock_deps
    mock_llm.chat_completion.assert_called_once()

    call_args = mock_llm.chat_completion.call_args
    sent_messages = call_args[0][0] # First arg is messages list

    # 1. Verify User Message is UNTOUCHED
    user_msg = next(m for m in sent_messages if m["role"] == "user")
    assert user_msg["content"] == original_text

    # 2. Verify System Message was MODIFIED (Injection)
    system_msg = next(m for m in sent_messages if m["role"] == "system")
    assert "You are a bot." in system_msg["content"]
    assert "INSTRUCTION FROM SUBCONSCIOUS: Be kind." in system_msg["content"]
