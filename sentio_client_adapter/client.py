import requests
import json
from dataclasses import dataclass
from typing import Optional, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SentioClient")

@dataclass
class SentioConfig:
    base_url: str
    client_name: str
    api_key: Optional[str] = None

class SentioClient:
    """
    Reference Python adapter for Sentio Engine.
    Handles registration and session management.
    """
    def __init__(self, base_url: str, client_name: str):
        self.config = SentioConfig(base_url=base_url, client_name=client_name)
        self.session = requests.Session()

    def register(self) -> str:
        """
        Registers the client with the engine and obtains an API Key.
        """
        url = f"{self.config.base_url}/register_client"
        try:
            response = self.session.post(url, json={"client_name": self.config.client_name})
            response.raise_for_status()
            data = response.json()
            self.config.api_key = data["api_key"]
            logger.info(f"Registered successfully. API Key: {self.config.api_key}")
            return self.config.api_key
        except requests.exceptions.RequestException as e:
            logger.error(f"Registration failed: {e}")
            raise

    def _get_headers(self, session_id: str) -> Dict[str, str]:
        if not self.config.api_key:
            raise ValueError("Client not registered. Call register() first.")

        return {
            "x-api-key": self.config.api_key,
            "x-session-id": session_id
        }

    def send_stimulus_pb(self, session_id: str, protobuf_data: bytes):
        """
        Sends a raw protobuf stimulus to the engine.
        """
        url = f"{self.config.base_url}/stimulus"
        headers = self._get_headers(session_id)
        headers["Content-Type"] = "application/protobuf"

        response = self.session.post(url, data=protobuf_data, headers=headers)
        response.raise_for_status()
        return True

    def send_text(self, session_id: str, text: str):
        """
        Sends text (possibly containing [SENTIO_EMO_STATE] tags) to the engine.
        """
        url = f"{self.config.base_url}/process_agent_text"
        headers = self._get_headers(session_id)
        # Note: headers for API Key are separate from payload in the current implementation

        payload = {
            "text": text,
            "session_id": session_id
        }

        # We need to pass the API Key in the header, not query param, as per our API implementation
        response = self.session.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return True

    def get_report(self, session_id: str) -> bytes:
        """
        Fetches the current report (protobuf bytes) for a session.
        """
        url = f"{self.config.base_url}/report"
        headers = self._get_headers(session_id)

        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        return response.content

# Usage Example
if __name__ == "__main__":
    # Assumes engine is running on localhost:8000
    client = SentioClient("http://localhost:8000", "TestClient_Py")

    try:
        client.register()

        # Simulate User A
        session_a = "user_session_123"
        print(f"Sending text for {session_a}...")
        client.send_text(session_a, "Hello! [SENTIO_EMO_STATE]{\"joy\": 0.8}[/SENTIO_EMO_STATE]")

        report_a = client.get_report(session_a)
        print(f"Received report for {session_a} ({len(report_a)} bytes)")

        # Simulate User B
        session_b = "user_session_456"
        print(f"Sending text for {session_b}...")
        client.send_text(session_b, "Oh no. [SENTIO_EMO_STATE]{\"sadness\": 0.9}[/SENTIO_EMO_STATE]")

        report_b = client.get_report(session_b)
        print(f"Received report for {session_b} ({len(report_b)} bytes)")

    except Exception as e:
        print(f"Error: {e}")
