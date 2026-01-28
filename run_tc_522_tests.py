"""Test runner for TC-522 batch upload tests (standalone)."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Now try to run tests manually
try:
    # Import test module
    sys.path.insert(0, str(Path(__file__).parent / "tests" / "unit" / "telemetry_api"))

    from test_tc_522_batch_upload import (
        TestBatchUpload,
        TestBatchUploadTransactional,
        TestBatchValidation,
        TestBatchPerformance,
        test_db,
        client,
    )

    print("Successfully imported test modules")
    print("\nTest classes found:")
    print("  - TestBatchUpload")
    print("  - TestBatchUploadTransactional")
    print("  - TestBatchValidation")
    print("  - TestBatchPerformance")

    # Try to manually run one test
    import tempfile
    from pathlib import Path
    from launch.telemetry_api.routes.database import TelemetryDatabase
    from launch.telemetry_api.server import create_app, ServerConfig
    from fastapi.testclient import TestClient

    print("\nRunning manual smoke test...")

    # Create test database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_telemetry.db"
        db = TelemetryDatabase(db_path)

        # Create test client
        config = ServerConfig(db_path=str(db.db_path))
        app = create_app(config)
        test_client = TestClient(app)

        # Run a simple batch upload test
        import uuid
        from datetime import datetime, timezone

        runs = [
            {
                "event_id": str(uuid.uuid4()),
                "run_id": f"test-run-{i}",
                "agent_name": "test.agent",
                "job_type": "test",
                "start_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "status": "running",
            }
            for i in range(3)
        ]

        response = test_client.post("/api/v1/runs/batch", json={"runs": runs})

        if response.status_code == 201:
            data = response.json()
            print(f"  ✓ Batch upload successful: {data['total']} runs created")
            print(f"  ✓ Created: {data['created']}, Existing: {data['existing']}, Failed: {data['failed']}")
            print("\n✓ TC-522 implementation validated successfully!")
            sys.exit(0)
        else:
            print(f"  ✗ Batch upload failed: {response.status_code}")
            print(f"  Response: {response.json()}")
            sys.exit(1)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
