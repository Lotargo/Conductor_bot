import time
from collections import defaultdict

# In-memory storage for Kafka topics
KAFKA_MOCK_STORAGE = defaultdict(list)

class MockKafkaProducer:
    """A mock Kafka producer that stores messages in memory."""
    def send(self, topic, value):
        print(f"KAFKA_MOCK: Sending message to topic '{topic}': {value}")
        KAFKA_MOCK_STORAGE[topic].append(value)

    def flush(self):
        print("KAFKA_MOCK: Flushing producer.")
        pass

class MockKafkaConsumer:
    """A mock Kafka consumer that reads messages from memory."""
    def __init__(self, topic):
        self.topic = topic
        self.offset = 0

    def __iter__(self):
        return self

    def __next__(self):
        while self.offset >= len(KAFKA_MOCK_STORAGE[self.topic]):
            # Simulate waiting for new messages
            time.sleep(0.1)

        message = KAFKA_MOCK_STORAGE[self.topic][self.offset]
        self.offset += 1
        print(f"KAFKA_MOCK: Consumed message from topic '{self.topic}': {message}")
        # Mock the structure of a Kafka message
        return type('obj', (object,), {'value' : message})()


class MockRAGDatabase:
    """A mock RAG database that returns dummy context."""
    def get_history(self, chat_id: str) -> str:
        print(f"RAG_DB_MOCK: Getting history for chat_id '{chat_id}'")
        return f"This is a dummy conversation history for chat {chat_id}. The last message was about project deadlines."

class MockMagicProxy:
    """A mock Magic Proxy to simulate LLM calls."""
    def decide(self, persona_manifest: dict, rag_context: str, screenshots: list) -> dict:
        print("MAGIC_PROXY_MOCK: Making a decision...")
        # Simulate a decision based on the persona
        if "Corporate Assistant" in persona_manifest.get("persona_name", ""):
            return {
                "action": "send_message",
                "target": "@all",
                "text": "Team, let's sync up on the action items. We need to maintain velocity as per our SLA."
            }
        else:
            return {
                "action": "send_message",
                "target": "@all",
                "text": "Hey guys, what's the status on this?"
            }