import uuid
import secrets
from typing import Optional, List, Dict
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from sentio_engine.data.mongo import MongoManager
from sentio_engine.schemas.sentio_pb2 import EmotionalState

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
        collection = await cls.get_collection()
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
        collection = await cls.get_collection()
        doc = await collection.find_one({
            "api_key": api_key,
            "session_id": session_id
        })
        return doc

    @classmethod
    async def save_state(cls, api_key: str, session_id: str, state_data: bytes, last_update: datetime):
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

class HistoryRepository:
    """
    Manages historical logging of emotional events for complex state analysis.
    Collection: `emotional_history`
    """
    COLLECTION_NAME = "emotional_history"

    @classmethod
    async def get_collection(cls):
        db = MongoManager.get_db()
        return db[cls.COLLECTION_NAME]

    @classmethod
    async def log_event(cls, api_key: str, session_id: str, state: EmotionalState, cause: str):
        """
        Logs the current emotional snapshot to history.
        """
        collection = await cls.get_collection()

        # Convert map to dict for Mongo
        emotions_dict = dict(state.emotions)

        doc = {
            "api_key": api_key,
            "session_id": session_id,
            "timestamp": datetime.utcnow(),
            "emotions": emotions_dict,
            "cause": cause
        }
        await collection.insert_one(doc)

    @classmethod
    async def get_stats_in_window(cls, api_key: str, session_id: str, emotion: str, start_time: datetime) -> Dict[str, float]:
        """
        Calculates stats for a specific emotion in a time window.
        Returns: {"avg": float, "min": float, "max": float, "count": int}
        """
        collection = await cls.get_collection()

        pipeline = [
            {
                "$match": {
                    "api_key": api_key,
                    "session_id": session_id,
                    "timestamp": {"$gte": start_time},
                    f"emotions.{emotion}": {"$exists": True}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "avg": {"$avg": f"$emotions.{emotion}"},
                    "min": {"$min": f"$emotions.{emotion}"},
                    "max": {"$max": f"$emotions.{emotion}"},
                    "count": {"$sum": 1}
                }
            }
        ]

        cursor = collection.aggregate(pipeline)
        result = await cursor.to_list(length=1)

        if not result:
            return {"avg": 0.0, "min": 0.0, "max": 0.0, "count": 0}

        return result[0]
