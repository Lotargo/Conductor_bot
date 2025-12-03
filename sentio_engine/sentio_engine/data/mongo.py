import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

class MongoManager:
    """
    Manages the asynchronous connection to MongoDB.
    """
    client: Optional[AsyncIOMotorClient] = None
    db_name: str = "sentio_db"

    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        if cls.client is None:
            mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            cls.client = AsyncIOMotorClient(mongo_url)
        return cls.client

    @classmethod
    def get_db(cls):
        client = cls.get_client()
        return client[cls.db_name]

    @classmethod
    def close(cls):
        if cls.client:
            cls.client.close()
            cls.client = None
