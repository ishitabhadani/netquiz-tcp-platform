"""
Comprehensive Stage 2 Test Suite for NetQuiz TCP Socket Server.

Executes and verifies all 8 mandatory tests specified in the project requirements:
TEST 1: Start TCP server and verify it listens on 127.0.0.1:5000.
TEST 2: Connect one client and verify join_ack.
TEST 3: Connect three clients simultaneously and verify active_clients == 3.
TEST 4: Send ping and verify pong response.
TEST 5: Disconnect one client and verify other clients stay connected.
TEST 6: Send malformed JSON and verify server handles it without crashing.
TEST 7: Restart server and verify SO_REUSEADDR allows immediate rebind.
TEST 8: Verify concurrent clients maintain independent connection IDs and states.
"""

import socket
import sys
import time
from typing import List

from backend.config import TCP_SERVER_HOST, TCP_SERVER_PORT
from backend.networking.tcp_server import TCPServer
from backend.networking.test_client import QuizTCPClient


def run_all_tests():
    print("=" * 60)
    print("      NETQUIZ STAGE 2 — TCP SOCKET SERVER TEST SUITE")
    print("=" * 60)
    passed_count = 0
    total_tests = 8

    # TEST 1: Start TCP Server
    print("\n--- TEST 1: Start TCP Server on 127.0.0.1:5000 ---")
    server = TCPServer(host=TCP_SERVER_HOST, port=TCP_SERVER_PORT)
    server.start(run_in_background=True)
    time.sleep(0.3)
    
    status = server.get_status()
    assert status["is_running"] is True, "Server should be running"
    assert status["port"] == 5000, "Port should be 5000"
    print(f" [PASS] Server is listening on {status['host']}:{status['port']} via {status['protocol']} ({status['family']})")
    passed_count += 1

    # TEST 2: Single Client Connect & Join
    print("\n--- TEST 2: Connect Single Client (Ishita) ---")
    client1 = QuizTCPClient()
    connected = client1.connect()
    assert connected is True, "Client 1 connection failed"
    joined = client1.join("Ishita")
    assert joined is True, "Client 1 join failed"
    assert client1.connection_id is not None, "Connection ID should not be None"
    print(f" [PASS] Client joined successfully. ID: {client1.connection_id}")
    passed_count += 1

    # TEST 3: Connect 3 Simultaneous Clients
    print("\n--- TEST 3: Connect Three Simultaneous Clients (Ishita, Aarav, Riya) ---")
    client2 = QuizTCPClient()
    assert client2.connect() is True
    assert client2.join("Aarav") is True

    client3 = QuizTCPClient()
    assert client3.connect() is True
    assert client3.join("Riya") is True

    time.sleep(0.3)
    status = server.get_status()
    print(f" Current Server Active Clients: {status['active_clients']}")
    for c in status["clients"]:
        print(f"  - Student: {c['student_name']} (ID: {c['connection_id']}, Addr: {c['ip']}:{c['port']})")
    assert status["active_clients"] == 3, f"Expected 3 active clients, got {status['active_clients']}"
    print(" [PASS] All three clients are connected simultaneously.")
    passed_count += 1

    # TEST 4: Ping / Pong Test
    print("\n--- TEST 4: Ping/Pong Message Test ---")
    ping_ok = client2.ping()
    assert ping_ok is True, "Ping from client2 failed"
    print(" [PASS] Ping sent and Pong received successfully.")
    passed_count += 1

    # TEST 5: Disconnect One Client (Other Clients Remain Connected)
    print("\n--- TEST 5: Disconnect One Client (Aarav) ---")
    client2.disconnect()
    time.sleep(0.3)
    status = server.get_status()
    print(f" Server Active Clients after Aarav disconnected: {status['active_clients']}")
    assert status["active_clients"] == 2, f"Expected 2 active clients, got {status['active_clients']}"
    # Verify remaining clients are Ishita and Riya
    names = [c["student_name"] for c in status["clients"]]
    assert "Ishita" in names and "Riya" in names, f"Remaining clients should be Ishita & Riya, got: {names}"
    # Verify client1 and client3 can still ping
    assert client1.ping() is True, "Client 1 should still be responsive"
    assert client3.ping() is True, "Client 3 should still be responsive"
    print(" [PASS] Disconnected client removed cleanly; other clients remain active and operational.")
    passed_count += 1

    # TEST 6: Malformed JSON Handling (No Crash)
    print("\n--- TEST 6: Malformed JSON Resilience ---")
    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw_sock.connect((TCP_SERVER_HOST, TCP_SERVER_PORT))
    # Send broken JSON line
    raw_sock.sendall(b"{this is not valid json}\n")
    response_bytes = raw_sock.recv(4096)
    raw_sock.close()
    assert b"error" in response_bytes.lower(), "Server should reply with error message for bad JSON"
    time.sleep(0.2)
    # Check server is still running and healthy
    status = server.get_status()
    assert status["is_running"] is True, "Server should NOT crash on invalid JSON"
    print(f" [PASS] Server returned error response and continued running unaffected: {response_bytes.decode('utf-8').strip()}")
    passed_count += 1

    # Clean up test clients from previous tests
    client1.disconnect()
    client3.disconnect()
    time.sleep(0.2)

    # TEST 7: Clean Shutdown & Restart (SO_REUSEADDR Port Binding)
    print("\n--- TEST 7: Server Stop & Port Re-bind Verification ---")
    server.stop()
    time.sleep(0.3)
    
    # Start a brand new server instance on the exact same port
    new_server = TCPServer(host=TCP_SERVER_HOST, port=TCP_SERVER_PORT)
    new_server.start(run_in_background=True)
    time.sleep(0.3)
    new_status = new_server.get_status()
    assert new_status["is_running"] is True, "New server should start cleanly on port 5000"
    print(" [PASS] Server shut down cleanly and new instance rebound to port 5000 immediately without TIME_WAIT errors.")
    passed_count += 1

    # TEST 8: Independent Client State Verification
    print("\n--- TEST 8: Independent Client State Verification ---")
    c_alpha = QuizTCPClient()
    c_beta = QuizTCPClient()
    c_gamma = QuizTCPClient()
    
    assert c_alpha.connect() and c_alpha.join("AlphaStudent")
    assert c_beta.connect() and c_beta.join("BetaStudent")
    assert c_gamma.connect() and c_gamma.join("GammaStudent")

    ids = [c_alpha.connection_id, c_beta.connection_id, c_gamma.connection_id]
    assert len(set(ids)) == 3, f"Each client must have a unique connection ID: {ids}"
    
    status = new_server.get_status()
    assert status["active_clients"] == 3
    print(f" [PASS] 3 concurrent clients established unique IDs: {ids}")
    passed_count += 1

    # Clean up
    c_alpha.disconnect()
    c_beta.disconnect()
    c_gamma.disconnect()
    new_server.stop()

    print("\n" + "=" * 60)
    print(f"  ALL {passed_count}/{total_tests} TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
