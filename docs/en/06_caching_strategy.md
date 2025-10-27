# Caching Strategy

To optimize performance and reduce redundant computations, Sentio Engine employs a caching strategy at the API level. This document outlines the server-side caching implementation and provides recommendations for client-side caching.

## Server-Side Caching: Prompt Cache

The primary server-side cache is implemented for the `POST /process_and_report` endpoint. We refer to this as a "Prompt Cache" because it caches the `Report` generated in response to a specific `Stimulus` (which acts as a "prompt" for the engine).

### How It Works

1.  **Endpoint:** `POST /process_and_report`
2.  **Technology:** **Redis** is used as the caching backend for its high speed and support for time-to-live (TTL) policies.
3.  **Cache Key:** When a `Stimulus` is received, the server computes a **SHA-256 hash** of the binary Protobuf message. This hash serves as a unique key in Redis.
4.  **Cache Logic:**
    *   **Cache Miss:** If the key is not found in Redis, the `Stimulus` is processed by the Core Engine, a new `Report` is generated, and this report is saved to Redis with a **1-hour TTL**. The report is then returned to the client.
    *   **Cache Hit:** If the key is found in Redis, the stored `Report` is returned directly to the client. The Core Engine is not engaged, and its internal state is not modified.

This mechanism is highly effective for applications where the same emotional stimuli are likely to occur repeatedly.

## Recommended Client-Side Caching

While Sentio Engine handles caching for its own processing, clients that integrate with it are encouraged to implement their own caching layers for tasks that fall outside the scope of the engine.

### 1. Embedding Cache (for RAG Systems)

If your application uses a Retrieval-Augmented Generation (RAG) system, caching embeddings is critical for performance and cost savings.

*   **What to Cache:** The vector embeddings of text chunks or documents.
*   **Cache Key:** A hash of the text content combined with the version of the embedding model used (e.g., `hash(text + "model_v1.2")`).
*   **TTL:** Embeddings are generally stable. A long TTL (weeks or months) or even indefinite caching is appropriate. Invalidate the cache only when the source text or the embedding model changes.

### 2. Prompt Cache (for LLM Calls)

Just as Sentio Engine caches its "prompts" (`Stimulus`), your application should cache the prompts it sends to external LLMs.

*   **What to Cache:** The final generated text response from the LLM.
*   **Cache Key:** A hash of the full prompt sent to the LLM (including the system prompt, user query, and any data from the Sentio Engine `Report`).
*   **TTL:** This depends on the volatility of your data. For dynamic content, a short TTL (10-60 minutes) is recommended. For static content (like FAQs), a longer TTL (hours or days) can be used.

### Example Implementation

For a practical demonstration of how to implement these client-side caching strategies, please refer to the example client located at `examples/oai_client_example.py`. This script shows how to use Redis to build simple yet effective caches for both embeddings and LLM prompts.
