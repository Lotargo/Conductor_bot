import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from sentio_engine.data.mongo import MongoManager
from sentio_engine.data.repositories import ClientRepository, StateRepository, HistoryRepository
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
    print("\n[OK] Client Registration verified.")

    # --- Part 2: State Isolation ---
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

    assert loaded_state_1.emotions["joy"] == pytest.approx(0.9)
    assert "sadness" not in loaded_state_1.emotions or loaded_state_1.emotions["sadness"] == 0.0
    print("[OK] State Isolation verified.")

    # --- Part 3: History & Complex States ---
    # Simulate a history of sadness for Session 2 to trigger "Depression" (hypothetically)
    # We log 3 events
    await HistoryRepository.log_event(api_key, session_2, state_2, "Bad event 1")
    await HistoryRepository.log_event(api_key, session_2, state_2, "Bad event 2")
    await HistoryRepository.log_event(api_key, session_2, state_2, "Bad event 3")

    # Verify we can retrieve stats
    start_time = now - datetime.timedelta(hours=1)
    stats = await HistoryRepository.get_stats_in_window(api_key, session_2, "sadness", start_time)

    assert stats["count"] == 3
    assert stats["avg"] == pytest.approx(0.9)
    assert stats["max"] == pytest.approx(0.9)

    # Verify Session 1 has no sadness history
    stats_1 = await HistoryRepository.get_stats_in_window(api_key, session_1, "sadness", start_time)
    assert stats_1["count"] == 0

    print("[OK] History & Stats verified.")
