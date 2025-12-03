import pytest
import asyncio
from mongomock_motor import AsyncMongoMockClient
from sentio_engine.data.mongo import MongoManager
from sentio_engine.data.repositories import ClientRepository, StateRepository
from sentio_engine.schemas.sentio_pb2 import EmotionalState

@pytest.fixture(scope="session")
def mongo_client():
    """
    Returns a MOCK motor client.
    """
    client = AsyncMongoMockClient()
    yield client
    client.close()

@pytest.fixture(autouse=True)
async def clear_db(mongo_client):
    """Clears the test database before each test."""
    # Patch the manager to use test DB
    original_client = MongoManager.client
    MongoManager.client = mongo_client
    yield
    # Cleanup (not strictly necessary with mock but good practice)
    # await mongo_client.drop_database("sentio_db")
    MongoManager.client = original_client

@pytest.mark.asyncio
async def test_client_registration():
    client_name = "TestClient"
    api_key = await ClientRepository.register_client(client_name)
    assert api_key is not None
    assert len(api_key) > 10

    # Verify we can find it
    client_doc = await ClientRepository.validate_api_key(api_key)
    assert client_doc is not None
    assert client_doc["client_name"] == client_name

@pytest.mark.asyncio
async def test_state_isolation():
    api_key = "test_api_key_123"
    session_1 = "session_A"
    session_2 = "session_B"

    # Create distinct states
    state_1 = EmotionalState()
    state_1.emotions["joy"] = 0.9

    state_2 = EmotionalState()
    state_2.emotions["sadness"] = 0.9

    import datetime
    now = datetime.datetime.utcnow()

    # Save them
    await StateRepository.save_state(api_key, session_1, state_1.SerializeToString(), now)
    await StateRepository.save_state(api_key, session_2, state_2.SerializeToString(), now)

    # Load and verify
    doc_1 = await StateRepository.load_state(api_key, session_1)
    loaded_state_1 = EmotionalState()
    loaded_state_1.ParseFromString(doc_1["state_blob"])

    doc_2 = await StateRepository.load_state(api_key, session_2)
    loaded_state_2 = EmotionalState()
    loaded_state_2.ParseFromString(doc_2["state_blob"])

    assert loaded_state_1.emotions["joy"] == pytest.approx(0.9)
    assert "sadness" not in loaded_state_1.emotions or loaded_state_1.emotions["sadness"] == 0.0

    assert loaded_state_2.emotions["sadness"] == pytest.approx(0.9)
    assert "joy" not in loaded_state_2.emotions or loaded_state_2.emotions["joy"] == 0.0
