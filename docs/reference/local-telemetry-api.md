# Local Telemetry API Client Guide

**Purpose:** This guide shows you how to integrate with Local Telemetry to track agent runs, job executions, and automated tasks through HTTP endpoints.

**Version:** 3.0.0
**Last Updated:** 2026-02-07
**Base URL:** http://localhost:8765 (default, configurable via `TELEMETRY_API_URL`)

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Understanding the Event Lifecycle](#understanding-the-event-lifecycle)
3. [How to Fill Fields](#how-to-fill-fields)
4. [Best Practices](#best-practices)
5. [Common Integration Patterns](#common-integration-patterns)
6. [Endpoint Reference](#endpoint-reference)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Your First Telemetry Event

Here's the minimal code to track a run:

```python
import requests
import uuid
from datetime import datetime, timezone

api_url = "http://localhost:8765"
event_id = str(uuid.uuid4())

# 1. Start the run
requests.post(f"{api_url}/api/v1/runs", json={
    "event_id": event_id,
    "run_id": "my-first-run-001",
    "agent_name": "my-agent",
    "job_type": "data-processing",
    "start_time": datetime.now(timezone.utc).isoformat()
})

# 2. Do your work
result = do_work()

# 3. Mark complete
requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
    "status": "success",
    "end_time": datetime.now(timezone.utc).isoformat()
})
```

### Prerequisites

- **Service running:** Container `local-telemetry-api` on port 8765
- **Authentication:** Disabled by default (no auth headers needed)
- **Rate limiting:** Disabled by default
- **Content-Type:** Always use `application/json`

### Interactive Documentation

- **Swagger UI:** http://localhost:8765/docs
- **ReDoc:** http://localhost:8765/redoc
- **OpenAPI Spec:** http://localhost:8765/openapi.json

---

## Understanding the Event Lifecycle

Every telemetry event follows a **three-phase lifecycle**: **Start → Work → Complete**. Understanding this lifecycle is critical to using Local Telemetry effectively.

### Phase 1: Start (`POST /api/v1/runs`)

**When:** At the beginning of your job, before doing any work.
**Purpose:** Create the run record with initial metadata.
**Status:** Set to `"running"` (default) or omit the field entirely.

```python
event_id = str(uuid.uuid4())  # Generate ONCE per run

requests.post(f"{api_url}/api/v1/runs", json={
    "event_id": event_id,
    "run_id": f"run-{datetime.now(timezone.utc).isoformat()}",
    "agent_name": "data-processor",
    "job_type": "etl-pipeline",
    "start_time": datetime.now(timezone.utc).isoformat(),
    "status": "running",  # Optional, defaults to "running"

    # Optional context
    "environment": "production",
    "git_repo": "https://github.com/myorg/myrepo",
    "git_branch": "main"
})
```

**Key Requirements:**
- **`event_id`**: Unique identifier (UUID recommended) - used for idempotency
- **`run_id`**: Application-level identifier for your run
- **`agent_name`**: Name of the agent/service executing the work
- **`job_type`**: Type of job being performed
- **`start_time`**: When the run started (ISO8601 with timezone)

### Phase 2: Work (Your Application Logic)

**When:** Between start and completion.
**Purpose:** Execute your actual work.
**Telemetry:** No telemetry calls needed during work (unless updating progress).

```python
try:
    # Do your work
    items = fetch_data()
    results = process_items(items)

except Exception as e:
    # Capture errors for Phase 3
    error_summary = str(e)
    error_details = traceback.format_exc()
```

**Optional Progress Updates:** Use `PATCH /api/v1/runs/{event_id}` to update progress during long-running jobs:

```python
# Update progress mid-run
requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
    "items_succeeded": 50,
    "items_failed": 2
})
```

### Phase 3: Complete (`PATCH /api/v1/runs/{event_id}`)

**When:** After work completes (success or failure).
**Purpose:** Record final status, duration, counts, and errors.
**Status:** Update to final status: `success`, `failure`, `partial`, `timeout`, or `cancelled`.

**Success:**
```python
requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
    "status": "success",
    "end_time": datetime.now(timezone.utc).isoformat(),
    "duration_ms": 5000,
    "items_succeeded": 100,
    "output_summary": "Processed 100 items successfully"
})
```

**Failure:**
```python
requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
    "status": "failure",
    "end_time": datetime.now(timezone.utc).isoformat(),
    "error_summary": "Database connection failed",
    "error_details": traceback.format_exc()
})
```

**Partial Success:**
```python
requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
    "status": "partial",
    "end_time": datetime.now(timezone.utc).isoformat(),
    "items_succeeded": 85,
    "items_failed": 15,
    "error_summary": "15 items failed validation"
})
```

### Lifecycle Summary

| Phase | Endpoint | HTTP Method | Required Fields | Purpose |
|-------|----------|-------------|-----------------|---------|
| **Start** | `/api/v1/runs` | POST | `event_id`, `run_id`, `agent_name`, `job_type`, `start_time` | Initialize run |
| **Work** | *(your code)* | — | — | Execute task |
| **Complete** | `/api/v1/runs/{event_id}` | PATCH | `status`, `end_time` | Finalize run |

---

## How to Fill Fields

### Required Fields (Phase 1: Start)

#### `event_id`
- **Type:** String (UUID recommended)
- **Purpose:** Unique identifier for idempotency (prevents duplicate entries)
- **How to fill:** Generate once per run using `uuid.uuid4()`
- **Example:** `"550e8400-e29b-41d4-a716-446655440000"`
- **⚠️ Critical:** Never reuse `event_id` across different runs

```python
event_id = str(uuid.uuid4())  # Generate ONCE
```

#### `run_id`
- **Type:** String
- **Purpose:** Application-level identifier for your run (human-readable)
- **How to fill:** Use a format that includes timestamp and context
- **Example:** `"2026-01-12T10:30:00Z-my-agent-abc123"`
- **Pattern:** `{timestamp}-{agent_name}-{unique_suffix}`

```python
run_id = f"{datetime.now(timezone.utc).isoformat()}-{agent_name}-{uuid.uuid4().hex[:8]}"
```

#### `agent_name`
- **Type:** String
- **Purpose:** Name of the agent/service executing the work
- **How to fill:** Use dot notation for namespacing
- **Examples:**
  - `"seo_intelligence.insight_engine"`
  - `"data_pipeline.etl_worker"`
  - `"claude_agent.code_generator"`

```python
agent_name = "my_product.my_agent"
```

#### `job_type`
- **Type:** String
- **Purpose:** Category of work being performed
- **How to fill:** Use descriptive, consistent values
- **Examples:**
  - `"insight_generation"`
  - `"data_processing"`
  - `"model_training"`
  - `"feature_implementation"`

```python
job_type = "data_processing"
```

#### `start_time`
- **Type:** String (ISO8601 with timezone)
- **Purpose:** When the run started
- **How to fill:** Always include timezone (use UTC)
- **✅ Correct:** `"2026-01-12T10:30:00Z"` or `"2026-01-12T10:30:00+00:00"`
- **❌ Wrong:** `"2026-01-12 10:30:00"` (no timezone → validation error)

```python
start_time = datetime.now(timezone.utc).isoformat()
```

### Status Field

#### Valid Statuses (Canonical Values)

| Status | When to Use | Typical Use Case |
|--------|-------------|------------------|
| `running` | Job in progress (default) | Initial state |
| `success` | Job completed successfully | All work completed without errors |
| `failure` | Job failed completely | Unhandled exception, critical error |
| `partial` | Job completed with some failures | Some items succeeded, some failed |
| `timeout` | Job exceeded time limit | External timeout, deadline exceeded |
| `cancelled` | Job was cancelled | User cancellation, shutdown signal |

#### Status Aliases (POST only)

These aliases are **accepted on POST** and automatically normalized:
- `failed` → `failure`
- `completed` → `success`
- `succeeded` → `success`

**⚠️ Important:** PATCH endpoint does **NOT** accept aliases. Use only canonical values on PATCH.

```python
# ✅ OK on POST: alias normalized
requests.post(..., json={"status": "failed"})  # Becomes "failure"

# ✅ OK on PATCH: canonical value
requests.patch(..., json={"status": "failure"})

# ❌ ERROR on PATCH: alias rejected (422)
requests.patch(..., json={"status": "failed"})
```

### Item Counters

Track the number of items processed during your run:

| Field | Purpose | When to Set | Must Be |
|-------|---------|-------------|---------|
| `items_discovered` | Total items found/available | Phase 1 (POST) | ≥ 0 |
| `items_succeeded` | Items processed successfully | Phase 3 (PATCH) | ≥ 0 |
| `items_failed` | Items that failed | Phase 3 (PATCH) | ≥ 0 |
| `items_skipped` | Items skipped/ignored | Phase 3 (PATCH) | ≥ 0 |

**Example:**
```python
# Phase 1: Start
requests.post(..., json={
    "items_discovered": 100  # Found 100 items to process
})

# Phase 3: Complete
requests.patch(..., json={
    "items_succeeded": 85,   # 85 processed successfully
    "items_failed": 10,      # 10 failed
    "items_skipped": 5       # 5 skipped
})
```

### Duration Tracking

Track how long your run took:

```python
import time

start = time.time()

# Do work
do_work()

duration_ms = int((time.time() - start) * 1000)

requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
    "duration_ms": duration_ms  # In milliseconds
})
```

### Error Fields

Capture errors when jobs fail:

| Field | Purpose | Max Length |
|-------|---------|------------|
| `error_summary` | Short error message | Use for UI display |
| `error_details` | Full traceback/stack trace | Use for debugging |

**Example:**
```python
import traceback

try:
    do_work()
except Exception as e:
    requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
        "status": "failure",
        "error_summary": str(e),             # "Database connection failed"
        "error_details": traceback.format_exc()  # Full stack trace
    })
```

### Contextual Fields

Add context about what's being processed:

| Field | Purpose | Example |
|-------|---------|---------|
| `product` | Product identifier | `"seo-intelligence"` |
| `product_family` | Product grouping | `"content"`, `"analytics"` |
| `platform` | Platform/channel | `"web"`, `"mobile"`, `"api"` |
| `website` | Root domain | `"example.com"` |
| `subdomain` | Site subdomain | `"blog"`, `"docs"` |
| `website_section` | Section of site | `"blog"`, `"products"` |
| `item_name` | Specific item | `"how-to-optimize-seo"` |

**Example:**
```python
requests.post(f"{api_url}/api/v1/runs", json={
    "event_id": event_id,
    "run_id": "run-001",
    "agent_name": "content_analyzer",
    "job_type": "seo_analysis",
    "start_time": datetime.now(timezone.utc).isoformat(),

    # Context
    "product": "seo-intelligence",
    "platform": "web",
    "website": "example.com",
    "website_section": "blog",
    "item_name": "how-to-optimize-seo"
})
```

### Git Tracking

#### Option 1: Include Git Metadata on Start

If you know the commit hash at the start of the run:

```python
requests.post(f"{api_url}/api/v1/runs", json={
    "event_id": event_id,
    "run_id": "run-001",
    "agent_name": "my-agent",
    "job_type": "deployment",
    "start_time": datetime.now(timezone.utc).isoformat(),

    # Git metadata (persisted)
    "git_repo": "https://github.com/myorg/myrepo",
    "git_branch": "main",
    "git_commit_hash": "abc1234567890",
    "git_run_tag": "v1.2.3"
})
```

**⚠️ Important:** These git fields are **accepted but NOT persisted** on POST:
- `git_commit_source`
- `git_commit_author`
- `git_commit_timestamp`

To set these fields, use Option 2 below.

#### Option 2: Associate Commit After Creation

If the commit is created during the run (e.g., LLM code generation):

```python
# Phase 1: Start run
event_id = str(uuid.uuid4())
requests.post(f"{api_url}/api/v1/runs", json={
    "event_id": event_id,
    "run_id": "run-001",
    "agent_name": "code-generator",
    "job_type": "feature-implementation",
    "start_time": datetime.now(timezone.utc).isoformat()
})

# Phase 2: Work and create commit
result = generate_code()
commit_sha = create_git_commit()

# Phase 2b: Associate commit
requests.post(f"{api_url}/api/v1/runs/{event_id}/associate-commit", json={
    "commit_hash": commit_sha,
    "commit_source": "llm",  # "manual", "llm", or "ci"
    "commit_author": "Claude Code <noreply@anthropic.com>",
    "commit_timestamp": datetime.now(timezone.utc).isoformat()
})

# Phase 3: Complete
requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
    "status": "success",
    "end_time": datetime.now(timezone.utc).isoformat()
})
```

**`commit_source` Values:**
- `manual` — Human-created commit
- `llm` — LLM-generated commit (Claude Code, Cursor, Copilot, etc.)
- `ci` — CI/CD pipeline commit

### Custom Metadata (JSON Fields)

Use `metrics_json` and `context_json` for custom structured data:

```python
requests.post(f"{api_url}/api/v1/runs", json={
    "event_id": event_id,
    "run_id": "run-001",
    "agent_name": "llm-agent",
    "job_type": "code-generation",
    "start_time": datetime.now(timezone.utc).isoformat(),

    # Custom metrics
    "metrics_json": {
        "input_tokens": 1500,
        "output_tokens": 3000,
        "api_cost_usd": 0.05
    },

    # Custom context
    "context_json": {
        "model": "claude-sonnet-4.5",
        "temperature": 0.7,
        "features_enabled": ["code_review", "testing"]
    }
})
```

**Storage:** These fields are stored as JSON strings in the database and parsed back to objects when retrieved.

---

## Best Practices

### 1. Always Generate Unique `event_id` Values

**✅ Correct:**
```python
event_id = str(uuid.uuid4())  # Generate once per run

# Use same event_id for all operations on this run
requests.post(f"{api_url}/api/v1/runs", json={"event_id": event_id, ...})
requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={...})
```

**❌ Wrong:**
```python
# Don't generate new event_id for updates
requests.patch(f"{api_url}/api/v1/runs/{str(uuid.uuid4())}", ...)
```

### 2. Use Idempotency for Safe Retries

The `event_id` field enables idempotent POST requests. If you retry with the same `event_id`, you'll get HTTP 201 with `"status": "duplicate"` (not an error).

```python
event_id = str(uuid.uuid4())

for attempt in range(3):
    try:
        response = requests.post(f"{api_url}/api/v1/runs", json={
            "event_id": event_id,  # Same ID for all retries
            "run_id": "run-001",
            "agent_name": "my-agent",
            "job_type": "processing",
            "start_time": datetime.now(timezone.utc).isoformat()
        })

        result = response.json()
        if result["status"] == "created":
            print("New run created")
        elif result["status"] == "duplicate":
            print("Run already exists (safe retry)")
        break

    except requests.exceptions.RequestException as e:
        if attempt == 2:
            print(f"Failed after 3 attempts: {e}")
        time.sleep(2 ** attempt)
```

### 3. Always Include Timezone in Timestamps

**✅ Correct:**
```python
# Explicit UTC timezone
start_time = datetime.now(timezone.utc).isoformat()
# Result: "2026-01-12T10:30:00.123456+00:00"
```

**❌ Wrong:**
```python
# No timezone → validation error
start_time = datetime.now().isoformat()
# Result: "2026-01-12T10:30:00.123456" (REJECTED)
```

### 4. Use PATCH for Updates (Not POST)

**✅ Correct:**
```python
# Start run
requests.post(f"{api_url}/api/v1/runs", json={...})

# Update run
requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
    "status": "success",
    "end_time": "..."
})
```

**❌ Wrong:**
```python
# Don't create a new run instead of updating
requests.post(f"{api_url}/api/v1/runs", json={
    "event_id": event_id,  # Duplicate event_id
    "status": "success"
})
```

### 5. Track Duration in Milliseconds

```python
import time

start = time.time()
do_work()
duration_ms = int((time.time() - start) * 1000)

requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
    "duration_ms": duration_ms
})
```

### 6. Use Canonical Statuses on PATCH

**✅ Correct:**
```python
requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
    "status": "failure"  # Canonical value
})
```

**❌ Wrong:**
```python
requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
    "status": "failed"  # Alias NOT accepted on PATCH (422 error)
})
```

### 7. Don't Crash Your Agent If Telemetry Fails

Telemetry is observability, not critical path. Handle failures gracefully:

```python
def safe_telemetry_post(api_url, data):
    try:
        response = requests.post(f"{api_url}/api/v1/runs", json=data, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        # Log but don't crash
        print(f"Telemetry failed (non-fatal): {e}")
        return None

# Usage
safe_telemetry_post(api_url, run_data)
do_critical_work()  # Continues even if telemetry fails
```

### 8. Use Batch Upload for High Volume

If you're creating many events at once, use the batch endpoint:

```python
events = [
    {
        "event_id": str(uuid.uuid4()),
        "run_id": f"run-{i}",
        "agent_name": "bulk-processor",
        "job_type": "batch-job",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "status": "success"
    }
    for i in range(100)
]

response = requests.post(f"{api_url}/api/v1/runs/batch", json=events)
result = response.json()
print(f"Inserted: {result['inserted']}, Duplicates: {result['duplicates']}")
```

---

## Common Integration Patterns

### Pattern 1: Context Manager for Auto-Tracking

```python
from contextlib import contextmanager
import requests
import uuid
from datetime import datetime, timezone
import time

@contextmanager
def telemetry_run(agent_name, job_type, api_url="http://localhost:8765", **kwargs):
    """
    Context manager that automatically tracks run lifecycle.

    Usage:
        with telemetry_run("my-agent", "processing") as event_id:
            do_work()
    """
    event_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)
    start_ts = time.time()

    # Phase 1: Start run
    try:
        requests.post(f"{api_url}/api/v1/runs", json={
            "event_id": event_id,
            "run_id": f"{start_time.isoformat()}-{agent_name}-{uuid.uuid4().hex[:8]}",
            "agent_name": agent_name,
            "job_type": job_type,
            "status": "running",
            "start_time": start_time.isoformat(),
            **kwargs  # Additional fields
        }, timeout=5)
    except Exception as e:
        print(f"Telemetry start failed: {e}")

    # Phase 2: Yield to user code
    try:
        yield event_id

        # Phase 3: Mark success
        duration_ms = int((time.time() - start_ts) * 1000)
        try:
            requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
                "status": "success",
                "end_time": datetime.now(timezone.utc).isoformat(),
                "duration_ms": duration_ms
            }, timeout=5)
        except Exception as e:
            print(f"Telemetry completion failed: {e}")

    except Exception as e:
        # Phase 3: Mark failure
        duration_ms = int((time.time() - start_ts) * 1000)
        try:
            requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
                "status": "failure",
                "end_time": datetime.now(timezone.utc).isoformat(),
                "duration_ms": duration_ms,
                "error_summary": str(e),
                "error_details": traceback.format_exc()
            }, timeout=5)
        except Exception as te:
            print(f"Telemetry error reporting failed: {te}")
        raise  # Re-raise original exception

# Usage
with telemetry_run("my-agent", "processing", environment="prod") as event_id:
    result = do_work()

    # Optional: update progress mid-run
    requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
        "items_succeeded": result.count
    })
```

### Pattern 2: Decorator for Function Tracking

```python
import functools
import requests
import uuid
from datetime import datetime, timezone
import time
import traceback

def track_telemetry(agent_name, job_type, api_url="http://localhost:8765"):
    """
    Decorator to automatically track function execution.

    Usage:
        @track_telemetry("my-agent", "processing")
        def process_data():
            return do_work()
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            event_id = str(uuid.uuid4())
            start_time = datetime.now(timezone.utc)
            start_ts = time.time()

            # Start run
            try:
                requests.post(f"{api_url}/api/v1/runs", json={
                    "event_id": event_id,
                    "run_id": f"{start_time.isoformat()}-{agent_name}-{uuid.uuid4().hex[:8]}",
                    "agent_name": agent_name,
                    "job_type": job_type,
                    "status": "running",
                    "start_time": start_time.isoformat()
                }, timeout=5)
            except Exception as e:
                print(f"Telemetry failed: {e}")

            # Execute function
            try:
                result = func(*args, **kwargs)

                # Mark success
                duration_ms = int((time.time() - start_ts) * 1000)
                try:
                    requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
                        "status": "success",
                        "end_time": datetime.now(timezone.utc).isoformat(),
                        "duration_ms": duration_ms
                    }, timeout=5)
                except:
                    pass

                return result

            except Exception as e:
                # Mark failure
                duration_ms = int((time.time() - start_ts) * 1000)
                try:
                    requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
                        "status": "failure",
                        "end_time": datetime.now(timezone.utc).isoformat(),
                        "duration_ms": duration_ms,
                        "error_summary": str(e),
                        "error_details": traceback.format_exc()
                    }, timeout=5)
                except:
                    pass
                raise

        return wrapper
    return decorator

# Usage
@track_telemetry("data-processor", "etl")
def process_data():
    return do_work()
```

### Pattern 3: Buffered Telemetry Writer

For high-volume scenarios, buffer events and flush in batches:

```python
import queue
import threading
import requests
import time

class BufferedTelemetry:
    """
    Buffered telemetry client that batches events for efficiency.

    Usage:
        telemetry = BufferedTelemetry("http://localhost:8765")
        telemetry.add({...run data...})
        telemetry.flush()  # Optional manual flush
    """
    def __init__(self, api_url, flush_size=50, flush_interval=30):
        self.api_url = api_url
        self.buffer = queue.Queue()
        self.flush_size = flush_size
        self.flush_interval = flush_interval
        self.running = True

        # Start background flush worker
        self.worker = threading.Thread(target=self._flush_worker, daemon=True)
        self.worker.start()

    def add(self, run_data):
        """Add event to buffer. Flushes automatically when buffer is full."""
        self.buffer.put(run_data)

        if self.buffer.qsize() >= self.flush_size:
            self._flush()

    def flush(self):
        """Manually flush all buffered events."""
        self._flush()

    def _flush(self):
        """Internal flush implementation."""
        events = []

        # Drain buffer
        while not self.buffer.empty() and len(events) < self.flush_size:
            try:
                events.append(self.buffer.get_nowait())
            except queue.Empty:
                break

        if not events:
            return

        # Upload batch
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/runs/batch",
                json=events,
                timeout=10
            )
            response.raise_for_status()
            print(f"Flushed {len(events)} events")
        except Exception as e:
            print(f"Batch upload failed: {e}")
            # Re-queue failed events
            for event in events:
                self.buffer.put(event)

    def _flush_worker(self):
        """Background worker that flushes periodically."""
        while self.running:
            time.sleep(self.flush_interval)
            self._flush()

    def shutdown(self):
        """Shutdown worker and flush remaining events."""
        self.running = False
        self.worker.join(timeout=5)
        self._flush()

# Usage
telemetry = BufferedTelemetry("http://localhost:8765")

for i in range(100):
    telemetry.add({
        "event_id": str(uuid.uuid4()),
        "run_id": f"run-{i}",
        "agent_name": "bulk-agent",
        "job_type": "processing",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "status": "success"
    })

telemetry.shutdown()  # Flush on exit
```

### Pattern 4: Progress Tracking for Long-Running Jobs

```python
import requests
import uuid
from datetime import datetime, timezone
import time

def process_with_progress(items, api_url="http://localhost:8765"):
    event_id = str(uuid.uuid4())

    # Phase 1: Start
    requests.post(f"{api_url}/api/v1/runs", json={
        "event_id": event_id,
        "run_id": f"run-{event_id[:8]}",
        "agent_name": "batch-processor",
        "job_type": "data-processing",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "items_discovered": len(items)
    })

    succeeded = 0
    failed = 0

    # Phase 2: Process with progress updates
    for i, item in enumerate(items):
        try:
            process_item(item)
            succeeded += 1
        except Exception:
            failed += 1

        # Update progress every 10 items
        if (i + 1) % 10 == 0:
            requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
                "items_succeeded": succeeded,
                "items_failed": failed
            })

    # Phase 3: Complete
    requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
        "status": "success" if failed == 0 else "partial",
        "end_time": datetime.now(timezone.utc).isoformat(),
        "items_succeeded": succeeded,
        "items_failed": failed
    })
```

---

## Endpoint Reference

### Core Endpoints

#### POST `/api/v1/runs` — Create Run

**Purpose:** Start a new telemetry run (idempotent).
**Auth:** Required if enabled
**Rate Limit:** Enforced if enabled

**Required Fields:**
- `event_id` (string)
- `run_id` (string)
- `agent_name` (string)
- `job_type` (string)
- `start_time` (string, ISO8601 with timezone)

**Response (HTTP 201):**
```json
{
  "status": "created",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "run_id": "run-001"
}
```

**Response on Duplicate (HTTP 201):**
```json
{
  "status": "duplicate",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Event already exists (idempotent)"
}
```

**Example:**
```bash
curl -X POST http://localhost:8765/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "run_id": "run-001",
    "agent_name": "my-agent",
    "job_type": "processing",
    "start_time": "2026-01-12T10:30:00Z"
  }'
```

---

#### PATCH `/api/v1/runs/{event_id}` — Update Run

**Purpose:** Update an existing run's status and metrics.
**Auth:** Required if enabled
**Rate Limit:** Enforced if enabled

**Common Fields to Update:**
- `status` (string) — Canonical values only: `running`, `success`, `failure`, `partial`, `timeout`, `cancelled`
- `end_time` (string, ISO8601)
- `duration_ms` (integer, ≥ 0)
- `items_succeeded` (integer, ≥ 0)
- `items_failed` (integer, ≥ 0)
- `items_skipped` (integer, ≥ 0)
- `error_summary` (string)
- `error_details` (string)
- `output_summary` (string)
- `metrics_json` (object)
- `context_json` (object)

**Response (HTTP 200):**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "updated": true,
  "fields_updated": ["status", "end_time", "duration_ms"]
}
```

**Example:**
```bash
curl -X PATCH http://localhost:8765/api/v1/runs/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "success",
    "end_time": "2026-01-12T10:35:00Z",
    "duration_ms": 300000,
    "items_succeeded": 100
  }'
```

---

#### POST `/api/v1/runs/{event_id}/associate-commit` — Link Git Commit

**Purpose:** Associate a git commit with a run (typically for LLM-generated code).
**Auth:** Required if enabled
**Rate Limit:** Enforced if enabled

**Required Fields:**
- `commit_hash` (string, 7-40 characters)
- `commit_source` (string) — `manual`, `llm`, or `ci`

**Optional Fields:**
- `commit_author` (string)
- `commit_timestamp` (string, ISO8601)

**Response (HTTP 200):**
```json
{
  "status": "success",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "run_id": "run-001",
  "commit_hash": "abc1234567890"
}
```

**Example:**
```bash
curl -X POST http://localhost:8765/api/v1/runs/550e8400-e29b-41d4-a716-446655440000/associate-commit \
  -H "Content-Type: application/json" \
  -d '{
    "commit_hash": "abc1234567890",
    "commit_source": "llm",
    "commit_author": "Claude Code <noreply@anthropic.com>",
    "commit_timestamp": "2026-01-12T10:35:00Z"
  }'
```

---

#### POST `/api/v1/runs/batch` — Create Multiple Runs

**Purpose:** Create multiple runs in a single request.
**Auth:** Required if enabled
**Rate Limit:** Enforced if enabled

**Request Body:** Array of run objects (no wrapper)

**Response (HTTP 200):**
```json
{
  "inserted": 98,
  "duplicates": 2,
  "errors": [],
  "total": 100
}
```

**Example:**
```bash
curl -X POST http://localhost:8765/api/v1/runs/batch \
  -H "Content-Type: application/json" \
  -d '[
    {
      "event_id": "11111111-1111-1111-1111-111111111111",
      "run_id": "run-1",
      "agent_name": "agent-a",
      "job_type": "job-a",
      "start_time": "2026-01-12T10:30:00Z"
    },
    {
      "event_id": "22222222-2222-2222-2222-222222222222",
      "run_id": "run-2",
      "agent_name": "agent-b",
      "job_type": "job-b",
      "start_time": "2026-01-12T10:31:00Z"
    }
  ]'
```

---

### Query Endpoints

#### GET `/api/v1/runs` — Query Runs

**Purpose:** Retrieve runs with filters and pagination.
**Auth:** Not required
**Rate Limit:** Enforced if enabled

**Query Parameters:**
- `agent_name` (string) — Exact match
- `job_type` (string) — Exact match
- `status` (string) — Accepts canonical values and aliases
- `created_before` (string, ISO8601) — Exclusive `<`
- `created_after` (string, ISO8601) — Exclusive `>`
- `start_time_from` (string, ISO8601) — Inclusive `>=`
- `start_time_to` (string, ISO8601) — Inclusive `<=`
- `limit` (integer, 1-1000, default 100)
- `offset` (integer, ≥ 0, default 0)

**Response:** Array of run objects, ordered by `created_at DESC`

**Example:**
```bash
curl "http://localhost:8765/api/v1/runs?agent_name=my-agent&status=success&limit=50"
```

---

#### GET `/api/v1/runs/{event_id}` — Get Single Run

**Purpose:** Retrieve a specific run by `event_id`.
**Auth:** Not required
**Rate Limit:** Enforced if enabled

**Response:** Single run object (not an array)

**Example:**
```bash
curl http://localhost:8765/api/v1/runs/550e8400-e29b-41d4-a716-446655440000
```

---

### Utility Endpoints

#### GET `/health` — Health Check

**Purpose:** Check if the service is running.
**Auth:** Not required
**Rate Limit:** Not enforced

**Response (HTTP 200):**
```json
{
  "status": "ok",
  "version": "3.0.0",
  "db_path": "/data/telemetry.sqlite",
  "journal_mode": "DELETE",
  "synchronous": "FULL"
}
```

**Example:**
```bash
curl http://localhost:8765/health
```

---

#### GET `/metrics` — System Metrics

**Purpose:** Get system-wide statistics.
**Auth:** Not required
**Rate Limit:** Not enforced

**Response (HTTP 200):**
```json
{
  "total_runs": 12345,
  "agents": {
    "my-agent": 8400,
    "other-agent": 3945
  },
  "recent_24h": 120,
  "performance": {
    "db_path": "/data/telemetry.sqlite",
    "journal_mode": "DELETE"
  }
}
```

**Example:**
```bash
curl http://localhost:8765/metrics
```

---

#### GET `/api/v1/metadata` — Get Distinct Values

**Purpose:** Get all distinct agent names and job types.
**Auth:** Not required
**Rate Limit:** Enforced if enabled

**Response (HTTP 200):**
```json
{
  "agent_names": ["agent1", "agent2"],
  "job_types": ["job1", "job2"],
  "counts": {
    "agent_names": 2,
    "job_types": 2
  },
  "cache_hit": true
}
```

**Note:** Results are cached for 5 minutes.

**Example:**
```bash
curl http://localhost:8765/api/v1/metadata
```

---

## Troubleshooting

### Error: 422 "field required"

**Problem:** Missing required fields in POST request.

**Solution:** Ensure these fields are present:
- `event_id`
- `run_id`
- `agent_name`
- `job_type`
- `start_time`

**Example:**
```python
# ✅ Correct
requests.post(..., json={
    "event_id": "...",
    "run_id": "...",
    "agent_name": "...",
    "job_type": "...",
    "start_time": "2026-01-12T10:30:00Z"
})
```

---

### Error: 422 "Status must be one of..."

**Problem:** Invalid status value on PATCH endpoint.

**Solution:** Use only canonical values on PATCH:
- `running`
- `success`
- `failure`
- `partial`
- `timeout`
- `cancelled`

**❌ Wrong:**
```python
requests.patch(..., json={"status": "failed"})  # Alias not allowed
```

**✅ Correct:**
```python
requests.patch(..., json={"status": "failure"})  # Canonical value
```

**Note:** Aliases are accepted on POST but **NOT on PATCH**.

---

### Error: 422 "ensure this value has at least 1 characters"

**Problem:** Timestamp missing timezone.

**Solution:** Always include timezone in ISO8601 timestamps:

**❌ Wrong:**
```python
"start_time": "2026-01-12 10:30:00"  # No timezone
```

**✅ Correct:**
```python
"start_time": "2026-01-12T10:30:00Z"  # UTC
"start_time": "2026-01-12T10:30:00+00:00"  # UTC with offset
```

---

### Error: 404 Not Found

**Problem:** `event_id` doesn't exist in database.

**Solution:**
1. Verify the run was created with POST first
2. Check for typos in `event_id`
3. Use GET `/api/v1/runs` to verify the run exists

**Debug:**
```bash
# Verify run exists
curl http://localhost:8765/api/v1/runs/YOUR-EVENT-ID
```

---

### Error: 429 Too Many Requests

**Problem:** Exceeded rate limit.

**Solution:**
- Wait 60 seconds (see `Retry-After` header)
- Reduce request frequency
- Use batch endpoint for multiple events
- Disable rate limiting in development (`TELEMETRY_RATE_LIMIT_ENABLED=false`)

**Batch Alternative:**
```python
# Instead of 100 individual POST requests
events = [...]
requests.post(f"{api_url}/api/v1/runs/batch", json=events)
```

---

### Error: 500 "database is locked"

**Problem:** Multiple processes writing to SQLite database.

**Solution:**
- Ensure only ONE API worker is running (`TELEMETRY_API_WORKERS=1`)
- Check for other processes accessing database directly
- Wait and retry (usually transient)

---

### Issue: Duplicate `event_id` returns 201 (not an error)

**Problem:** This is NOT an error — it's idempotent behavior.

**Explanation:** Both new and duplicate runs return HTTP 201. Check the response body:
- `"status": "created"` → New run inserted
- `"status": "duplicate"` → Run already exists (safe retry)

**Example:**
```python
response = requests.post(..., json={"event_id": event_id, ...})
result = response.json()

if result["status"] == "created":
    print("New run created")
elif result["status"] == "duplicate":
    print("Run already exists (idempotent retry)")
```

---

### Issue: `git_commit_source` not saved after POST

**Problem:** `git_commit_source`, `git_commit_author`, `git_commit_timestamp` not persisted on POST.

**Explanation:** These fields are **accepted** in the POST body but **NOT persisted** during initial creation.

**Solution:** Use one of these methods to set commit metadata:

**Option 1: PATCH**
```python
requests.patch(f"{api_url}/api/v1/runs/{event_id}", json={
    "git_commit_source": "llm",
    "git_commit_author": "Claude <noreply@anthropic.com>",
    "git_commit_timestamp": "2026-01-12T10:30:00Z"
})
```

**Option 2: associate-commit**
```python
requests.post(f"{api_url}/api/v1/runs/{event_id}/associate-commit", json={
    "commit_hash": "abc123",
    "commit_source": "llm",
    "commit_author": "Claude <noreply@anthropic.com>",
    "commit_timestamp": "2026-01-12T10:30:00Z"
})
```

---

### Issue: `commit_url` or `repo_url` returns null

**Problem:** Missing git metadata or unsupported platform.

**Solution:**
- Ensure `git_repo` and `git_commit_hash` are set
- Supported platforms: GitHub.com, GitLab.com, Bitbucket.org only
- Self-hosted instances return `null` (expected behavior)

**Verify:**
```bash
curl http://localhost:8765/api/v1/runs/YOUR-EVENT-ID/commit-url
```

---

## See Also

- **Interactive API Docs:** http://localhost:8765/docs
