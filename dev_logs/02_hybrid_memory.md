# Report 02: Hybrid Memory System

## Overview
While the "Stateless" architecture solved scalability, it introduced a challenge: how to track long-term psychological states (like "Depression" or "Trust") if we only load the *current* snapshot into memory? The solution was the **Hybrid Memory** architecture.

## Mechanics

### 1. Fast Memory (Snapshot)
- **Storage:** `emotional_states` collection.
- **Purpose:** Used for immediate reactions, stimulus processing, and decay calculations.
- **Access:** Loaded on every request.

### 2. Deep Memory (History Log)
- **Storage:** `emotional_history` collection.
- **Purpose:** An append-only log of every emotional event.
- **Implementation:** `HistoryRepository.log_event` is called asynchronously after every state update.

### 3. Analytics (Complex State Evaluator)
- **Problem:** "Depression" isn't a momentary spike; it's a sustained state of sadness.
- **Solution:** We implemented aggregation queries in `HistoryRepository`.
  - Example Query: "Calculate the average intensity of 'sadness' for Session X over the last 14 days."
- **Integration:**
  - Before generating a report, the API calls `_check_and_update_complex_states`.
  - This function runs the aggregations against Mongo.
  - If conditions are met (e.g., avg > 0.5), the tag "depression" is injected into the Report.

## Outcomes
- **Depth:** The AI can now "remember" how it felt last week without keeping that data in RAM.
- **Performance:** Fast memory ensures low latency for chat, while history queries run efficiently via database indices.
