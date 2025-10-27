# Caching Strategy

To ensure high performance and reduce redundant computations, Sentio Engine implements a caching layer at the API level. This document outlines the server-side caching mechanism and provides recommendations for client-side caching.

## Server-Side Caching: `POST /process_and_report`

The primary caching mechanism is built into the `POST /process_and_report` endpoint. This endpoint is designed for stateless interactions where the same input should consistently produce the same initial output.

### How It Works

1.  **Request Hashing:** When a request is received, the engine computes a **SHA-256 hash** of the binary `Stimulus` message content. This hash serves as a unique key for the request.

2.  **Cache Lookup:** The engine checks for the existence of this key in the **Redis cache**.

3.  **Cache Hit:** If the key is found, the corresponding `Report` message is retrieved from Redis and returned directly to the client. The Core Engine is not engaged, and the internal state of the engine is not modified. This is extremely fast.

4.  **Cache Miss:** If the key is not found, the request is processed normally:
    *   The `Stimulus` is sent to the Core Engine.
    *   The engine's internal state is updated.
    *   A new `Report` is generated.
    *   The new `Report` is stored in Redis using the hash key.
    *   The `Report` is returned to the client.

5.  **Time-to-Live (TTL):** Cached entries are set to expire after **1 hour**. This strikes a balance between performance and ensuring that the state does not become excessively stale if the underlying personality configuration changes.

### Sequence Diagram (Cache Flow)

This diagram illustrates the decision-making process at the API level when a request is received.

```mermaid
graph TD
    A[Client sends POST /process_and_report] --> B{Compute hash of Stimulus};
    B --> C{Key exists in Redis?};
    C -- Yes (Cache Hit) --> D[Fetch Report from Redis];
    D --> F[Return cached Report to Client];
    C -- No (Cache Miss) --> E[Process Stimulus with Core Engine];
    E --> G[Generate new Report];
    G --> H[Store Report in Redis (key=hash, TTL=1h)];
    H --> I[Return new Report to Client];
```

## Client-Side Caching (Recommended)

For applications that frequently send the same stimuli, we highly recommend implementing a local caching layer on the client side. This can prevent even making a network request, further reducing latency.

### Example (Python)

Here is a simple example using a dictionary as an in-memory cache. For more robust needs, libraries like `cachetools` could be used.

```python
import requests
from sentio_engine.schemas.sentio_pb2 import Stimulus, Report

# A simple in-memory cache
client_side_cache = {}

def get_cached_report(stimulus: Stimulus) -> Report:
    """
    Processes a stimulus, using a local cache to avoid redundant API calls.
    """
    # Create a cache key from the stimulus data
    cache_key = stimulus.SerializeToString()

    # Check local cache first
    if cache_key in client_side_cache:
        print("Client cache hit!")
        report = Report()
        report.ParseFromString(client_side_cache[cache_key])
        return report

    # If not in local cache, call the API
    print("Client cache miss. Calling API...")
    response = requests.post(
        "http://127.0.0.1:8000/process_and_report",
        data=cache_key,
        headers={'Content-Type': 'application/protobuf'}
    )

    if response.status_code == 200:
        # Store the response in the local cache
        client_side_cache[cache_key] = response.content

        # Parse and return the report
        report = Report()
        report.ParseFromString(response.content)
        return report
    else:
        # Handle errors appropriately
        response.raise_for_status()

# --- Usage ---
stimulus_A = Stimulus()
stimulus_A.emotions["joy"] = 0.8

# First call: will be a cache miss on the client and server
print("First call for Stimulus A:")
get_cached_report(stimulus_A)

# Second call: will be a cache hit on the client
print("\nSecond call for Stimulus A:")
get_cached_report(stimulus_A)
```

---

**Next:** [Testing Guide](./07_testing.md)
