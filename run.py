import threading
import uvicorn
import time
import sys
import os

# Ensure the 'conductor' directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from conductor.listener.main import app as fastapi_app
from conductor.orchestrator.main import run_orchestrator
from conductor.decision_engine.main import run_decision_engine
from conductor.executor.main import run_executor

def run_fastapi():
    """Runs the FastAPI listener app using uvicorn."""
    print("MAIN_RUNNER: Starting Listener (FastAPI)...")
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, log_level="info")

def main():
    """
    Runs all Conductor modules concurrently in separate threads.
    """
    print("--- Starting Conductor AI Assistant ---")

    # Define the target functions for each module
    targets = {
        "listener": run_fastapi,
        "orchestrator": run_orchestrator,
        "decision_engine": run_decision_engine,
        "executor": run_executor,
    }

    threads = []

    # Create and start a thread for each module
    for name, target_func in targets.items():
        thread = threading.Thread(target=target_func, name=name, daemon=True)
        threads.append(thread)
        print(f"MAIN_RUNNER: Launching module '{name}' in a new thread.")
        thread.start()
        time.sleep(1) # Stagger starts to make logs more readable

    print("\n--- All modules are running. Press Ctrl+C to stop. ---")
    
    try:
        # Keep the main thread alive to allow daemon threads to run
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n--- Shutting down Conductor AI Assistant ---")
        # Threads are daemons, so they will exit when the main thread exits.
        sys.exit(0)

if __name__ == "__main__":
    main()