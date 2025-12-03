import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from sentio_engine.data.mongo import MongoManager
from sentio_engine.data.repositories import ClientRepository, StateRepository
from sentio_engine.schemas.sentio_pb2 import EmotionalState

@pytest.fixture(scope="function")
async def mongo_client():
    """
    Returns a REAL motor client connected to the dockerized database.
    """
    # Connect to localhost since ports are mapped in docker-compose
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    yield client
    client.close()

@pytest.fixture(autouse=True)
async def clear_db(mongo_client):
    """Clears the test database before each test."""
    # Use a specific test database
    db_name = "sentio_db_test_real"
    await mongo_client.drop_database(db_name)

    # Patch the manager to use test DB
    original_client = MongoManager.client
    original_db_name = MongoManager.db_name

    MongoManager.client = mongo_client
    MongoManager.db_name = db_name

    yield

    # Cleanup (drop db again to leave it clean)
    await mongo_client.drop_database(db_name)

    # Restore original state
    MongoManager.client = original_client
    MongoManager.db_name = original_db_name

@pytest.mark.asyncio
async def test_full_integration_flow():
    # --- Part 1: Registration ---
    client_name = "TestClient"
    api_key = await ClientRepository.register_client(client_name)
    assert api_key is not None
    assert len(api_key) > 10

    # Verify we can find it
    client_doc = await ClientRepository.validate_api_key(api_key)
    assert client_doc is not None
    assert client_doc["client_name"] == client_name

    print("\n[OK] Client Registration verified.")

    # --- Part 2: State Isolation ---
    # api_key is reused from above
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

    print("[OK] State Isolation verified.")
