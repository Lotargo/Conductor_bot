# Testing Guide

This guide describes the steps to set up the environment and run tests for the Sentio Engine project.

## 1. Environment Setup

### 1.1. Install Poetry

Poetry is used to manage project dependencies.

**Windows (PowerShell):**
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

**macOS / Linux:**
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

You may need to restart your terminal after installation.

### 1.2. Install Project Dependencies

1.  Navigate to the `sentio_engine` directory.
2.  Run the command:
    ```bash
    poetry install
    ```

## 2. Unit Tests

Unit tests check individual application components in isolation. They do not require Docker or Redis to be running.

To run them, execute the following from the `sentio_engine` directory:
```bash
poetry run pytest
```

## 3. Integration Test (with Docker)

This test verifies the interaction between `sentio-engine` and Redis.

### 3.1. Start Services

From the project's root directory, run:
```bash
docker compose up --build -d
```
This command will start both the application and Redis.

### 3.2. Run the Test Script

After the services are running, execute the following from the `sentio_engine` directory:
```bash
poetry run python tests/integration_test.py
```
The script checks that caching is working by comparing the response time of the first (cache miss) and second (cache hit) requests.

### 3.3. Stop Services

After the test is complete, stop the containers:
```bash
docker compose down
```

---

**Previous:** [Caching Strategy](./06_caching_strategy.md)
