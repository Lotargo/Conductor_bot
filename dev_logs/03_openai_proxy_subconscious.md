# Report 03: OpenAI Proxy & The "Subconscious"

## Overview
The final piece of the puzzle was enabling Sentio to actively influence the conversation rather than just passively tracking stats. We achieved this by turning Sentio into an OpenAI-compatible Proxy Server with "Subconscious" capabilities.

## Architecture: The Gatekeeper & The Synthesizer

### 1. The Proxy Endpoint
- **URL:** `POST /v1/chat/completions`.
- **Compatibility:** Drop-in replacement for standard OpenAI clients (like OpenWebUI, LangChain).
- **Integrity:** The User's original message is **never modified**.

### 2. The Gatekeeper (Input Analysis)
- **Role:** Intercepts the incoming user message.
- **Action:**
  - Saves the message to `MessageBufferRepository` (Short-term TTL memory).
  - Calls the internal **Subconscious LLM**.

### 3. The Subconscious (Internal Thought Process)
- **Method:** `llm_client.generate_emotional_reaction`.
- **Input:** Current State + Chat History + New User Message.
- **Task:** "Analyze this. How does it make you feel? What instructions should the conscious persona follow?"
- **Output:** JSON containing:
  - `emotions`: Delta updates (e.g., `{"joy": +0.2}`).
  - `instruction`: Guidance (e.g., "The user is sad. Be supportive but not annoying.").

### 4. The Synthesizer (Injection)
- **Action:**
  - Updates the MongoDB emotional state with the delta.
  - Constructs a hidden **System Prompt Injection**:
    > `[SENTIO SYSTEM CONTEXT] User Session: 123. Mood: Empathetic. INSTRUCTION: The user is sad. Be supportive...`
  - Injects this into the message list sent to the Upstream LLM.

### 5. Streaming Response
- The modified request (Original User Msg + Injected System Prompt) is sent to the Upstream Gateway.
- The response is streamed back to the client in real-time (`text/event-stream`).

## Outcomes
- **Empathy:** The AI now "feels" the context before answering.
- **Autonomy:** Sentio drives the persona's mood independently of the main LLM's training.
- **Simplicity:** Client apps need zero code changes, just a URL swap.
