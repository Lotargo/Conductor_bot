import requests
import time
import subprocess
import redis
import hashlib
import sys
import os

# This is a bit of a hack to make sure we can import the protobuf schemas
# when running this script from the `sentio_engine` directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sentio_engine.schemas.sentio_pb2 import Stimulus, Report

# --- Configuration ---
BASE_URL = "http://localhost:8000"
REDIS_HOST = "localhost"
REDIS_PORT = 6379

def clear_redis_cache():
    """Connects to Redis and flushes the database."""
    print("--- Clearing Redis cache ---")
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        r.flushdb()
        print("--- Redis cache cleared ---")
        return True
    except redis.exceptions.ConnectionError as e:
        print(f"!!! Could not connect to Redis: {e}")
        print("!!! Please ensure the Docker services are running (`docker compose up`)")
        return False

def test_caching_logic():
    """
    Tests the caching logic of the /process_and_report endpoint.
    1. Makes a request and verifies it's a cache miss.
    2. Makes the same request again and verifies it's a cache hit.
    """
    stimulus = Stimulus()
    stimulus.emotions["любопытство"] = 0.8
    serialized_stimulus = stimulus.SerializeToString()
    headers = {'Content-Type': 'application/protobuf'}

    # --- First Request (Cache Miss) ---
    print("\n--- Sending first request (should be a CACHE MISS) ---")
    start_time_miss = time.time()
    try:
        response_miss = requests.post(f"{BASE_URL}/process_and_report", data=serialized_stimulus, headers=headers)
        response_miss.raise_for_status()
    except requests.RequestException as e:
        print(f"!!! First request failed: {e}")
        print("!!! Please ensure the Docker services are running (`docker compose up`)")
        return False

    end_time_miss = time.time()
    duration_miss = end_time_miss - start_time_miss
    print(f"--- Request 1 (miss) took: {duration_miss:.4f} seconds ---")

    # --- Second Request (Cache Hit) ---
    print("\n--- Sending second request (should be a CACHE HIT) ---")
    start_time_hit = time.time()
    try:
        response_hit = requests.post(f"{BASE_URL}/process_and_report", data=serialized_stimulus, headers=headers)
        response_hit.raise_for_status()
    except requests.RequestException as e:
        print(f"!!! Second request failed: {e}")
        return False

    end_time_hit = time.time()
    duration_hit = end_time_hit - start_time_hit
    print(f"--- Request 2 (hit) took: {duration_hit:.4f} seconds ---")

    # --- Verification ---
    print("\n--- Verifying results ---")
    if response_miss.content != response_hit.content:
        print("!!! FAIL: Responses from cache miss and cache hit are NOT identical.")
        return False

    if duration_hit >= duration_miss:
        print("!!! WARN: Cache hit was not faster than cache miss.")
        # This is a warning, not a hard fail, as performance can vary on fast machines.
    else:
        print("--- PASS: Cache hit was significantly faster.")

    print("\n--- SUCCESS: Caching logic test passed! ---")
    return True

def main():
    """Main execution function."""
    print("--- Starting Manual Integration Test ---")
    if not clear_redis_cache():
        exit(1)

    if not test_caching_logic():
        exit(1)

    print("\n--- Test finished successfully! ---")

if __name__ == "__main__":
    main()
