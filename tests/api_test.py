"""
API endpoint tests for IndexTTS2.

Usage:
    # Start the server first:
    uv run webui.py --enable_api --port 7861 --fp16

    # Then run tests:
    PYTHONPATH="$PYTHONPATH:." uv run tests/api_test.py

    # Or test against custom URL:
    API_BASE_URL=http://localhost:8000 PYTHONPATH="$PYTHONPATH:." uv run tests/api_test.py
"""

import os
import sys
import time
import json
import tempfile
import urllib.request
import urllib.error
from pathlib import Path

# Configuration
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:7861")
PROMPT_AUDIO = "tests/sample_prompt.wav"
TEST_TEXT = "你好，这是一个测试。"

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def log_success(msg: str):
    print(f"{GREEN}✓ {msg}{RESET}")


def log_error(msg: str):
    print(f"{RED}✗ {msg}{RESET}")


def log_info(msg: str):
    print(f"{YELLOW}→ {msg}{RESET}")


def api_get(endpoint: str, params: dict = None) -> tuple[int, dict | bytes]:
    """Make GET request to API."""
    url = f"{BASE_URL}{endpoint}"
    if params:
        query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        url = f"{url}?{query}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=120) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return resp.status, json.loads(resp.read().decode())
            else:
                return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode()) if e.headers.get("Content-Type", "").startswith("application/json") else {}


def api_post(endpoint: str, data: dict) -> tuple[int, dict | bytes]:
    """Make POST request to API."""
    url = f"{BASE_URL}{endpoint}"
    body = json.dumps(data).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=120) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return resp.status, json.loads(resp.read().decode())
            else:
                return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode()) if e.headers.get("Content-Type", "").startswith("application/json") else {}


def test_health_check():
    """Test health check endpoint."""
    log_info("Testing health check endpoint...")
    status, data = api_get("/api/v1/health")

    if status == 200 and data.get("status") == "healthy":
        log_success(f"Health check passed: {data}")
        return True
    else:
        log_error(f"Health check failed: status={status}, data={data}")
        return False


def test_sync_tts_get():
    """Test synchronous TTS via GET request."""
    log_info("Testing synchronous TTS (GET)...")

    params = {
        "text": TEST_TEXT,
        "prompt_audio": PROMPT_AUDIO,
    }
    status, data = api_get("/api/v1/tts/tasks", params)

    if status == 200 and isinstance(data, bytes) and len(data) > 1000:
        log_success(f"Sync TTS (GET) passed: received {len(data)} bytes of audio")
        return True
    else:
        log_error(f"Sync TTS (GET) failed: status={status}, data_type={type(data)}")
        return False


def test_sync_tts_post():
    """Test synchronous TTS via POST request."""
    log_info("Testing synchronous TTS (POST)...")

    payload = {
        "text": TEST_TEXT,
        "prompt_audio": PROMPT_AUDIO,
        "sync": True,
    }
    status, data = api_post("/api/v1/tts/tasks", payload)

    if status == 200 and isinstance(data, bytes) and len(data) > 1000:
        log_success(f"Sync TTS (POST) passed: received {len(data)} bytes of audio")
        return True
    else:
        log_error(f"Sync TTS (POST) failed: status={status}, data_type={type(data)}")
        return False


def test_async_tts():
    """Test asynchronous TTS workflow."""
    log_info("Testing asynchronous TTS...")

    # Create task
    payload = {
        "text": TEST_TEXT,
        "prompt_audio": PROMPT_AUDIO,
        "sync": False,
    }
    status, data = api_post("/api/v1/tts/tasks", payload)

    if status != 200 or "task_id" not in data:
        log_error(f"Async task creation failed: status={status}, data={data}")
        return False

    task_id = data["task_id"]
    log_info(f"Task created: {task_id}")

    # Poll for completion
    max_wait = 120  # seconds
    poll_interval = 2  # seconds
    elapsed = 0

    while elapsed < max_wait:
        status, task_data = api_get(f"/api/v1/tts/tasks/{task_id}")

        if status != 200:
            log_error(f"Task status check failed: status={status}")
            return False

        task_status = task_data.get("status")
        log_info(f"Task status: {task_status}")

        if task_status == "completed":
            break
        elif task_status == "failed":
            log_error(f"Task failed: {task_data.get('message')}")
            return False

        time.sleep(poll_interval)
        elapsed += poll_interval

    if elapsed >= max_wait:
        log_error("Task timed out")
        return False

    # Download result
    status, audio_data = api_get(f"/api/v1/tts/tasks/{task_id}/result")

    if status == 200 and isinstance(audio_data, bytes) and len(audio_data) > 1000:
        log_success(f"Async TTS passed: received {len(audio_data)} bytes of audio")
        return True
    else:
        log_error(f"Result download failed: status={status}")
        return False


def test_invalid_prompt_audio():
    """Test error handling for invalid prompt audio."""
    log_info("Testing invalid prompt audio error handling...")

    params = {
        "text": TEST_TEXT,
        "prompt_audio": "nonexistent.wav",
    }
    status, data = api_get("/api/v1/tts/tasks", params)

    if status == 400:
        log_success(f"Error handling passed: {data.get('detail', 'error returned')}")
        return True
    else:
        log_error(f"Error handling failed: expected 400, got {status}")
        return False


def test_task_not_found():
    """Test error handling for non-existent task."""
    log_info("Testing task not found error handling...")

    status, data = api_get("/api/v1/tts/tasks/nonexistent-task-id")

    if status == 404:
        log_success("Task not found error handling passed")
        return True
    else:
        log_error(f"Error handling failed: expected 404, got {status}")
        return False


def main():
    """Run all tests."""
    print(f"\n{'='*60}")
    print(f"IndexTTS2 API Tests")
    print(f"Base URL: {BASE_URL}")
    print(f"{'='*60}\n")

    # Check if prompt audio exists
    if not os.path.exists(PROMPT_AUDIO):
        log_error(f"Prompt audio not found: {PROMPT_AUDIO}")
        log_info("Please ensure you're running from the project root directory")
        sys.exit(1)

    tests = [
        ("Health Check", test_health_check),
        ("Sync TTS (GET)", test_sync_tts_get),
        ("Sync TTS (POST)", test_sync_tts_post),
        ("Async TTS", test_async_tts),
        ("Invalid Prompt Audio", test_invalid_prompt_audio),
        ("Task Not Found", test_task_not_found),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n--- {name} ---")
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            log_error(f"Test exception: {e}")
            results.append((name, False))

    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")

    passed = sum(1 for _, r in results if r)
    failed = sum(1 for _, r in results if not r)

    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {status}: {name}")

    print(f"\nTotal: {passed} passed, {failed} failed")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    import urllib.parse
    main()
