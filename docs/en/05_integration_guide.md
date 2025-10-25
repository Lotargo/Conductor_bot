# Integration Guide

This guide provides a practical, conceptual example of how to integrate the Sentio Engine into a typical LLM-based chatbot application.

## Core Concept: The "Emotional Heartbeat"

The Sentio Engine is not meant to be a one-off function call. It's designed to be a persistent service that provides an "emotional heartbeat" for your AI. The general workflow is a continuous loop:

1.  **Analyze** user input to create a `Stimulus`.
2.  **Send** the `Stimulus` to the Sentio Engine.
3.  **Retrieve** the updated `Report` from the Sentio Engine.
4.  **Inject** the `Report` into the LLM's context.
5.  **Generate** an emotionally aware response.

## Example Application Flow

Let's imagine a chatbot backend built with Python.

### 1. The LLM Parser Function

First, you need a function that can translate user text into an emotional stimulus. This is a perfect task for an LLM. You can use a local model or an API like OpenAI/Anthropic with a specific prompt.

```python
def text_to_stimulus(user_text: str) -> Stimulus:
    """
    Uses an LLM to analyze text and determine the emotional content.
    (This is a simplified example).
    """
    # This prompt asks the LLM to act as a sentiment analyzer
    # and return a JSON object.
    prompt = f"""
        Analyze the emotional content of the following text.
        Respond ONLY with a JSON object mapping emotion names to an intensity
        from 0.0 to 1.0.

        Text: "{user_text}"

        Example response: {{"joy": 0.8, "gratitude": 0.6}}
    """

    # --- LLM API Call ---
    # response_json = call_llm_api(prompt)
    # mock_response = {"joy": 0.7, "trust": 0.4} # Mocked response

    stimulus = Stimulus()
    # stimulus.emotions.update(mock_response)

    return stimulus
```

### 2. Main Chat Handler

Your main chat handler will orchestrate the entire process.

```python
# Assume sentio_client is a helper class that handles requests to the Sentio Engine API
# a(see API Reference for an example)

def handle_chat_message(user_message: str):
    """
    Main function to process a user message and generate a response.
    """
    # 1. Analyze user input
    stimulus = text_to_stimulus(user_message)

    # 2. Send the stimulus to Sentio Engine
    sentio_client.send_stimulus(stimulus)

    # 3. Retrieve the updated emotional report
    report = sentio_client.get_report()

    # 4. Inject the report into the LLM's system prompt
    system_prompt = f"""
        You are a helpful and empathetic AI assistant.
        Your current emotional state is as follows:
        - Primary Mood: {report.emotional_state.primary_mood}
        - Active Emotions: {dict(report.emotional_state.emotions)}

        Please tailor your response to reflect this emotional state.
        For example, if you are feeling joyful, be more enthusiastic.
        If you are feeling sad, be more reserved and gentle.
    """

    # 5. Generate the final response
    # final_response = call_main_llm(system_prompt, user_message)

    # return final_response
```

### Why This Works

By injecting the emotional state directly into the system prompt, you are giving the LLM crucial context about *how* it should behave. This is far more effective than simply telling it to "be empathetic." You are providing it with a concrete internal state, which will naturally color its language, tone, and even its reasoning.

This simple loop transforms your AI from a stateless information processor into a dynamic entity with a persistent, evolving personality.
