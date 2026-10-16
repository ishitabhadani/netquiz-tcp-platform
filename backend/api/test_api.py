"""
Automated Test Suite for FastAPI Application / Bridge Layer (Stage 4).

Verifies all Stage 4 requirements:
1. GET /api/health endpoint
2. GET /api/server/status endpoint (TCP socket metrics)
3. GET /api/server/clients endpoint (Connected clients registry)
4. GET /api/quiz/info endpoint (Question bank metadata)
5. GET /api/quiz/leaderboard endpoint (Server-evaluated rankings)
6. CORS headers configuration
7. OpenAPI /docs schema generation
8. Application lifespan (Startup & graceful shutdown of TCP Server)
"""

from fastapi.testclient import TestClient
from backend.main import app
from backend.networking.tcp_server import tcp_server_instance
from backend.quiz.quiz_manager import quiz_manager_instance


def test_fastapi_endpoints():
    print("=" * 60)
    print("      FASTAPI APPLICATION & BRIDGE LAYER TESTS")
    print("=" * 60)
    passed = 0
    total = 8

    # Using TestClient within lifespan context
    with TestClient(app) as client:
        # TEST 1: Health Endpoint
        print("\n--- TEST 1: GET /api/health ---")
        res = client.get("/api/health")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["status"] == "ok"
        assert data["service"] == "NetQuiz Backend"
        assert data["version"] == "1.0"
        print(f" [PASS] Health check verified: {data}")
        passed += 1

        # TEST 2: TCP Server Status Endpoint
        print("\n--- TEST 2: GET /api/server/status ---")
        res = client.get("/api/server/status")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["port"] == 5000
        assert data["protocol"] == "TCP"
        assert data["address_family"] == "IPv4"
        assert data["socket_type"] == "SOCK_STREAM"
        assert "active_clients" in data
        assert "questions_sent" in data
        assert "completed_quizzes" in data
        print(f" [PASS] TCP Server Status verified: Port {data['port']}, Protocol {data['protocol']}, Running: {data['running']}")
        passed += 1

        # TEST 3: Connected Clients Endpoint
        print("\n--- TEST 3: GET /api/server/clients ---")
        res = client.get("/api/server/clients")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert "count" in data
        assert isinstance(data["clients"], list)
        print(f" [PASS] Connected clients endpoint verified: count = {data['count']}")
        passed += 1

        # TEST 4: Quiz Info Endpoint
        print("\n--- TEST 4: GET /api/quiz/info ---")
        res = client.get("/api/quiz/info")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["total_questions_available"] >= 15
        assert data["questions_per_quiz"] == 10
        assert data["topic"] == "Computer Networks"
        print(f" [PASS] Quiz info verified: {data['questions_per_quiz']} questions from bank of {data['total_questions_available']}")
        passed += 1

        # TEST 5: Leaderboard Endpoint
        print("\n--- TEST 5: GET /api/quiz/leaderboard ---")
        res = client.get("/api/quiz/leaderboard")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert "leaderboard" in data
        assert isinstance(data["leaderboard"], list)
        print(f" [PASS] Leaderboard endpoint verified: {len(data['leaderboard'])} entries present.")
        passed += 1

        # TEST 6: CORS Headers Configuration
        print("\n--- TEST 6: CORS Configuration Verification ---")
        origin = "http://localhost:5173"
        res = client.options(
            "/api/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET"
            }
        )
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == origin
        print(f" [PASS] CORS headers verified: Origin '{origin}' allowed.")
        passed += 1

        # TEST 7: OpenAPI /docs Schema
        print("\n--- TEST 7: OpenAPI /docs Generation ---")
        docs_res = client.get("/docs")
        assert docs_res.status_code == 200
        openapi_res = client.get("/openapi.json")
        assert openapi_res.status_code == 200
        schema = openapi_res.json()
        expected_paths = [
            "/api/health",
            "/api/server/status",
            "/api/server/clients",
            "/api/quiz/info",
            "/api/quiz/leaderboard"
        ]
        for path in expected_paths:
            assert path in schema["paths"], f"Expected path {path} in OpenAPI documentation"
        print(" [PASS] Interactive OpenAPI docs (/docs) and schema generated with all endpoints.")
        passed += 1

        # TEST 8: Server Startup Lifecycle
        print("\n--- TEST 8: Lifespan Startup Verification ---")
        assert tcp_server_instance.is_running is True
        print(" [PASS] Lifespan successfully initialized TCP server in background thread.")
        passed += 1

    # After TestClient context exits, verify shutdown
    print("\n--- Verifying Lifespan Shutdown ---")
    assert tcp_server_instance.is_running is False
    print(" [PASS] Lifespan successfully stopped TCP server and released port 5000.")

    print("\n" + "=" * 60)
    print(f"  ALL {passed}/{total} FASTAPI APPLICATION LAYER TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    test_fastapi_endpoints()
