import requests
import hashlib
import redis
import time
# To generate the Protobuf client code, run this command in the 'examples' directory:
# python -m grpc_tools.protoc -I. --python_out=. sentio.proto
from sentio_pb2 import Stimulus, Report

# --- Redis Client (for client-side caching) ---
redis_client = redis.Redis(host='localhost', port=6379, db=1) # Use a different DB for the client

# --- Sentio Engine Client ---
SENTIO_ENGINE_URL = "http://localhost:8000"

def get_emotional_report(stimulus: Stimulus) -> Report:
    """Sends a stimulus to Sentio Engine and gets a report."""
    serialized_stimulus = stimulus.SerializeToString()
    response = requests.post(
        f"{SENTIO_ENGINE_URL}/process_and_report",
        data=serialized_stimulus,
        headers={"Content-Type": "application/protobuf"}
    )
    response.raise_for_status()
    report = Report()
    report.ParseFromString(response.content)
    return report

# --- Example: Embedding Cache ---
def get_embedding(text: str):
    """
    Example of a function that gets embeddings, with client-side caching.
    """
    embedding_cache_key = f"embedding:{hashlib.sha256(text.encode()).hexdigest()}"
    cached_embedding = redis_client.get(embedding_cache_key)

    if cached_embedding:
        print("Embedding cache hit!")
        return cached_embedding.decode()

    print("Embedding cache miss. Generating new embedding...")
    # In a real application, you would call your embedding model here.
    # We'll just simulate it.
    embedding = f"embedding_for_{text}"
    redis_client.set(embedding_cache_key, embedding)
    return embedding

# --- Example: Prompt Cache (OAI-compatible LLM) ---
def get_llm_response(prompt: str):
    """
    Example of a function that gets a response from an OAI-compatible LLM,
    with client-side prompt caching.
    """
    prompt_cache_key = f"prompt:{hashlib.sha256(prompt.encode()).hexdigest()}"
    cached_response = redis_client.get(prompt_cache_key)

    if cached_response:
        print("Prompt cache hit!")
        return cached_response.decode()

    print("Prompt cache miss. Calling LLM...")
    # In a real application, you would make an API call to your LLM here.
    # We'll simulate it.
    response = f"LLM response to: {prompt}"
    redis_client.setex(prompt_cache_key, 600, response) # Cache for 10 minutes
    return response

# --- Main Example Flow ---
if __name__ == "__main__":
    # 1. Create a stimulus
    stimulus = Stimulus()
    stimulus.emotions['joy'] = 0.8
    stimulus.emotions['trust'] = 0.5

    # 2. Get emotional report from Sentio Engine
    print("--- Calling Sentio Engine ---")
    report = get_emotional_report(stimulus)
    print(f"Received report: Primary mood is {report.emotional_state.primary_mood}")

    # 3. Use the report to create a system prompt
    system_prompt = f"You are a helpful AI. Your current mood is {report.emotional_state.primary_mood}."
    user_query = "Tell me a joke."
    full_prompt = f"{system_prompt}\nUser: {user_query}"

    # 4. Get LLM response (will be a cache miss first)
    print("\n--- First LLM Call ---")
    response1 = get_llm_response(full_prompt)
    print(f"LLM Response 1: {response1}")

    # 5. Call it again (should be a cache hit)
    print("\n--- Second LLM Call (should be cached) ---")
    time.sleep(1) # To emphasize the speed of cache
    response2 = get_llm_response(full_prompt)
    print(f"LLM Response 2: {response2}")

    # 6. Example of embedding caching
    print("\n--- Embedding Cache Example ---")
    text_to_embed = "This is a sample text for RAG."
    embedding1 = get_embedding(text_to_embed)
    print(f"Embedding 1: {embedding1}")
    embedding2 = get_embedding(text_to_embed)
    print(f"Embedding 2: {embedding2}")
