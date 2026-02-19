"""Manual validation for TC-522 batch upload implementation."""

import sys
import site
from pathlib import Path

# Enable user site-packages
site.main()
sys.path.insert(0, site.getusersitepackages())

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import tempfile
import uuid
from datetime import datetime, timezone
from launch.telemetry_api.routes.database import TelemetryDatabase
from launch.telemetry_api.server import create_app, ServerConfig
from fastapi.testclient import TestClient


def generate_run_data(idx):
    """Generate test run data."""
    return {
        "event_id": str(uuid.uuid4()),
        "run_id": f"test-run-{idx}",
        "agent_name": "test.agent",
        "job_type": "test",
        "start_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "running",
        "product": "test-product",
        "metrics_json": {"test_metric": idx},
        "context_json": {"trace_id": str(uuid.uuid4()), "span_id": str(uuid.uuid4())},
    }


def run_tests():
    """Run manual validation tests."""
    print("=" * 70)
    print("TC-522 Batch Upload Validation")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_telemetry.db"
        db = TelemetryDatabase(db_path)

        config = ServerConfig(db_path=str(db.db_path))
        app = create_app(config)
        client = TestClient(app)

        tests_passed = 0
        tests_failed = 0

        # Test 1: Basic batch upload
        print("\n[Test 1] Basic batch upload (3 runs)...")
        runs = [generate_run_data(i) for i in range(3)]
        response = client.post("/api/v1/runs/batch", json={"runs": runs})

        if response.status_code == 201:
            data = response.json()
            if data["total"] == 3 and data["created"] == 3 and data["failed"] == 0:
                print("  [PASS] PASS: Batch upload successful")
                tests_passed += 1
            else:
                print(f"  [FAIL] FAIL: Unexpected response data: {data}")
                tests_failed += 1
        else:
            print(f"  [FAIL] FAIL: Status code {response.status_code}")
            tests_failed += 1

        # Test 2: Empty batch rejection
        print("\n[Test 2] Empty batch rejection...")
        response = client.post("/api/v1/runs/batch", json={"runs": []})

        if response.status_code in [400, 422]:  # Accept both 400 and 422 (Pydantic validation)
            print("  [PASS] PASS: Empty batch rejected")
            tests_passed += 1
        else:
            print(f"  [FAIL] FAIL: Expected 400/422, got {response.status_code}")
            tests_failed += 1

        # Test 3: Idempotency
        print("\n[Test 3] Idempotency (duplicate event_ids)...")
        runs = [generate_run_data(i) for i in range(2)]
        response1 = client.post("/api/v1/runs/batch", json={"runs": runs})
        response2 = client.post("/api/v1/runs/batch", json={"runs": runs})

        if response1.status_code == 201 and response2.status_code == 201:
            data1 = response1.json()
            data2 = response2.json()
            if data1["created"] == 2 and data2["existing"] == 2:
                print("  [PASS] PASS: Idempotency working correctly")
                tests_passed += 1
            else:
                print(f"  [FAIL] FAIL: Unexpected idempotency behavior")
                print(f"    First: created={data1['created']}")
                print(f"    Second: existing={data2['existing']}")
                tests_failed += 1
        else:
            print(f"  [FAIL] FAIL: Unexpected status codes")
            tests_failed += 1

        # Test 4: Large batch (100 runs)
        print("\n[Test 4] Large batch (100 runs)...")
        runs = [generate_run_data(i) for i in range(100)]
        import time
        start = time.time()
        response = client.post("/api/v1/runs/batch", json={"runs": runs})
        duration = time.time() - start

        if response.status_code == 201:
            data = response.json()
            if data["total"] == 100 and data["created"] == 100:
                print(f"  [PASS] PASS: Large batch processed in {duration:.2f}s")
                tests_passed += 1
            else:
                print(f"  [FAIL] FAIL: Unexpected response data")
                tests_failed += 1
        else:
            print(f"  [FAIL] FAIL: Status code {response.status_code}")
            tests_failed += 1

        # Test 5: Oversized batch rejection (>1000)
        print("\n[Test 5] Oversized batch rejection (>1000 runs)...")
        runs = [generate_run_data(i) for i in range(1001)]
        response = client.post("/api/v1/runs/batch", json={"runs": runs})

        if response.status_code == 400:
            print("  [PASS] PASS: Oversized batch rejected")
            tests_passed += 1
        else:
            print(f"  [FAIL] FAIL: Expected 400, got {response.status_code}")
            tests_failed += 1

        # Test 6: Transactional batch upload
        print("\n[Test 6] Transactional batch upload...")
        runs = [generate_run_data(i) for i in range(3)]
        response = client.post("/api/v1/runs/batch-transactional", json={"runs": runs})

        if response.status_code == 201:
            data = response.json()
            if data["total"] == 3 and data["created"] == 3 and data["failed"] == 0:
                print("  [PASS] PASS: Transactional batch upload successful")
                tests_passed += 1
            else:
                print(f"  [FAIL] FAIL: Unexpected response data")
                tests_failed += 1
        else:
            print(f"  [FAIL] FAIL: Status code {response.status_code}")
            tests_failed += 1

        # Test 7: Parent-child runs
        print("\n[Test 7] Parent-child runs in batch...")
        parent = generate_run_data(0)
        parent["job_type"] = "launch"
        parent["agent_name"] = "launch.orchestrator"

        children = [generate_run_data(i) for i in range(1, 4)]
        for child in children:
            child["parent_run_id"] = parent["run_id"]

        all_runs = [parent] + children
        response = client.post("/api/v1/runs/batch", json={"runs": all_runs})

        if response.status_code == 201:
            data = response.json()
            if data["total"] == 4 and data["created"] == 4:
                # Verify parent-child relationship
                if data["runs"][0]["parent_run_id"] is None and all(
                    r["parent_run_id"] == parent["run_id"] for r in data["runs"][1:]
                ):
                    print("  [PASS] PASS: Parent-child relationships preserved")
                    tests_passed += 1
                else:
                    print("  [FAIL] FAIL: Parent-child relationships not preserved")
                    tests_failed += 1
            else:
                print(f"  [FAIL] FAIL: Unexpected response data")
                tests_failed += 1
        else:
            print(f"  [FAIL] FAIL: Status code {response.status_code}")
            tests_failed += 1

        # Test 8: JSON fields preservation
        print("\n[Test 8] Metrics and context JSON preservation...")
        run = generate_run_data(0)
        run["metrics_json"] = {"tokens": 100, "latency_ms": 1234}
        run["context_json"] = {"trace_id": "test-trace", "model": "gpt-4"}

        response = client.post("/api/v1/runs/batch", json={"runs": [run]})

        if response.status_code == 201:
            data = response.json()
            run_data = data["runs"][0]
            if (
                run_data["metrics_json"]["tokens"] == 100
                and run_data["context_json"]["model"] == "gpt-4"
            ):
                print("  [PASS] PASS: JSON fields preserved correctly")
                tests_passed += 1
            else:
                print("  [FAIL] FAIL: JSON fields not preserved")
                tests_failed += 1
        else:
            print(f"  [FAIL] FAIL: Status code {response.status_code}")
            tests_failed += 1

        # Summary
        print("\n" + "=" * 70)
        print(f"Test Results: {tests_passed} passed, {tests_failed} failed")
        print("=" * 70)

        if tests_failed == 0:
            print("\n[PASS] All tests passed! TC-522 implementation validated successfully.")
            return 0
        else:
            print(f"\n[FAIL] {tests_failed} test(s) failed.")
            return 1


if __name__ == "__main__":
    try:
        sys.exit(run_tests())
    except Exception as e:
        print(f"\n[FAIL] Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
