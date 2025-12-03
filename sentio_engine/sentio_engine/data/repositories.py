import uuid
import secrets
from typing import Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from sentio_engine.data.mongo import MongoManager

class ClientRepository:
    """
    Manages client registration and authentication.
    Collection: `clients`
    """
    COLLECTION_NAME = "clients"

    @classmethod
    async def get_collection(cls):
        db = MongoManager.get_db()
        return db[cls.COLLECTION_NAME]

    @classmethod
    async def register_client(cls, client_name: str) -> str:
        """
        Registers a new client and returns an API key.
        """
        collection = await cls.get_collection()

        # Check if client name exists (optional, maybe allow duplicates with different keys)
        # For now, let's just create a new one.

        api_key = secrets.token_urlsafe(32)
        client_doc = {
            "client_name": client_name,
            "api_key": api_key,
            "created_at": datetime.utcnow(),
            "is_active": True
        }

        await collection.insert_one(client_doc)
        return api_key

    @classmethod
    async def validate_api_key(cls, api_key: str) -> Optional[dict]:
        """
        Validates the API key and returns the client document if valid.
        """
        collection = await cls.get_collection()
        client = await collection.find_one({"api_key": api_key, "is_active": True})
        return client

class StateRepository:
    """
    Manages persistent storage of emotional states for each client session.
    Collection: `emotional_states`
    """
    COLLECTION_NAME = "emotional_states"

    @classmethod
    async def get_collection(cls):
        db = MongoManager.get_db()
        return db[cls.COLLECTION_NAME]

    @classmethod
    async def load_state(cls, api_key: str, session_id: str) -> dict:
        """
        Loads the state for a specific client session.
        Returns a dict containing the serialized state and metadata.
        """
        collection = await cls.get_collection()
        doc = await collection.find_one({
            "api_key": api_key,
            "session_id": session_id
        })
        return doc

    @classmethod
    async def save_state(cls, api_key: str, session_id: str, state_data: bytes, last_update: datetime):
        """
        Upserts the emotional state.
        state_data: Serialized Protobuf bytes
        """
        collection = await cls.get_collection()

        filter_query = {
            "api_key": api_key,
            "session_id": session_id
        }

        update_doc = {
            "$set": {
                "state_blob": state_data,
                "last_update": last_update,
                "updated_at": datetime.utcnow()
            }
        }

        await collection.update_one(filter_query, update_doc, upsert=True)
