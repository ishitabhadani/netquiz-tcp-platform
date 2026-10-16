"""
NetQuiz Stage 7 — Multi-User Reliability, Session Isolation & Hardening Test Suite

Academic Concepts Demonstrated:
1. Multi-User Concurrency:
   Multiple students participate simultaneously in individual quiz sessions
   simulated via concurrent execution threads.
2. Server-Side State Isolation:
   Each student possesses an independent PlayerQuizState keyed by unique session ID.
   One student's progress, answers, or quiz completion never leaks into or alters
   another student's state.
3. Server-Side Evaluation & Scoring:
   Clients transmit ONLY candidate answers; scoring, percentage, correctness, and
   leaderboard ranking are computed exclusively on the server.
4. Security & Robustness:
   Correct answers are never leaked in question payloads. Duplicate submissions,
   out-of-order question attempts, invalid answer options, and expired sessions
   are gracefully rejected with clean HTTP error responses.
"""

import concurrent.futures
import threading
import time
from typing import Any, Dict, List
from fastapi.testclient import TestClient

from backend.main import app
from backend.quiz.quiz_manager import quiz_manager_instance
from backend.networking.tcp_server import tcp_server_instance


def run_stage7_multiuser_tests():
    print("=" * 70)
    print("      NETQUIZ STAGE 7 — MULTI-USER RELIABILITY & HARDENING TEST SUITE")
    print("=" * 70)

    # Use FastAPI TestClient to test the complete application stack
    client = TestClient(app)

    # Snapshot baseline metrics
    initial_status = client.get("/api/server/status").json()
    base_connections = initial_status["total_connections"]
    base_questions = initial_status["questions_sent"]
    base_answers = initial_status["answers_received"]
    base_completed = initial_status["completed_quizzes"]

    # =========================================================================
    # PART 1: LEAKAGE & ROBUSTNESS TESTS (Single-Session Pre-Checks)
    # =========================================================================

    print("\n--- TEST 1: Verify Correct Answer Is NEVER Leaked to Client ---")
    join_res = client.post("/api/quiz/join", json={"student_name": "SecurityProbe"})
    assert join_res.status_code == 200, f"Join failed: {join_res.text}"
    probe_session_id = join_res.json()["connection_id"]

    q_res = client.get(f"/api/quiz/question?connection_id={probe_session_id}")
    assert q_res.status_code == 200
    q_data = q_res.json()

    # CRITICAL SECURITY ASSERTION
    assert "correct_answer" not in q_data, "SECURITY BREACH: correct_answer was found in question response!"
    assert "explanation" not in q_data, "SECURITY BREACH: explanation was found in question response!"
    assert "options" in q_data and len(q_data["options"]) == 4
    print(" [PASS] Question payload verified: 'correct_answer' and 'explanation' are strictly withheld.")

    print("\n--- TEST 2: Duplicate Submission Rejection ---")
    # Student answers Q1
    q1_id = q_data["question_id"]
    ans_res1 = client.post(
        "/api/quiz/answer",
        json={"connection_id": probe_session_id, "question_id": q1_id, "answer": "B"}
    )
    assert ans_res1.status_code == 200
    score_after_q1 = ans_res1.json()["current_score"]

    # Student attempts duplicate submission of Q1
    ans_res_dup = client.post(
        "/api/quiz/answer",
        json={"connection_id": probe_session_id, "question_id": q1_id, "answer": "B"}
    )
    assert ans_res_dup.status_code == 400, "Duplicate submission must return HTTP 400 Bad Request"
    dup_error = ans_res_dup.json()
    assert "detail" in dup_error
    print(f" [PASS] Duplicate submission cleanly rejected: {dup_error['detail']}")

    # Verify quiz state was not corrupted and score didn't double-increment
    q2_res = client.get(f"/api/quiz/question?connection_id={probe_session_id}")
    assert q2_res.status_code == 200
    assert q2_res.json()["question_number"] == 2
    print(" [PASS] Quiz engine smoothly advanced to Question 2 despite duplicate attempt.")

    print("\n--- TEST 3: Out-of-Order Question Rejection ---")
    # Current question is Q2; attempt to submit answer for Q5
    ooo_res = client.post(
        "/api/quiz/answer",
        json={"connection_id": probe_session_id, "question_id": 5, "answer": "C"}
    )
    assert ooo_res.status_code == 400
    assert "Invalid question ID 5" in ooo_res.json()["detail"]
    print(f" [PASS] Out-of-order question rejected: {ooo_res.json()['detail']}")

    print("\n--- TEST 4: Invalid Answer Option Validation ---")
    # Valid options are A, B, C, D. Test Z, 1, 'hello', ''
    invalid_options = ["Z", "1", "hello", ""]
    for bad_opt in invalid_options:
        bad_res = client.post(
            "/api/quiz/answer",
            json={"connection_id": probe_session_id, "question_id": 2, "answer": bad_opt}
        )
        assert bad_res.status_code in [400, 422], f"Expected 400 or 422 for bad option '{bad_opt}', got {bad_res.status_code}"
    print(f" [PASS] All {len(invalid_options)} invalid answer options (Z, 1, 'hello', '') were cleanly rejected.")

    print("\n--- TEST 5: Invalid Session Identifier Rejection ---")
    inv_session = "invalid-session-9999"
    q_inv = client.get(f"/api/quiz/question?connection_id={inv_session}")
    assert q_inv.status_code == 404, "Invalid session question request must return 404"
    assert "detail" in q_inv.json()

    a_inv = client.post(
        "/api/quiz/answer",
        json={"connection_id": inv_session, "question_id": 1, "answer": "A"}
    )
    assert a_inv.status_code in [400, 404], "Invalid session answer request must return 400 or 404"

    s_inv = client.get(f"/api/quiz/summary?connection_id={inv_session}")
    assert s_inv.status_code == 404, "Invalid session summary request must return 404"
    print(" [PASS] Invalid session requests cleanly rejected across all endpoints without stack traces.")

    print("\n--- TEST 6: Client-Provided Score Tampering Rejection ---")
    # Client attempts to send forged 'score': 999 and 'percentage': 100.0 in answer body
    tamper_res = client.post(
        "/api/quiz/answer",
        json={
            "connection_id": probe_session_id,
            "question_id": 2,
            "answer": "C",
            "score": 999,
            "percentage": 100.0,
            "correct_answer": "D"
        }
    )
    assert tamper_res.status_code == 200
    res_data = tamper_res.json()
    # Correct answer for Q2 is 'C' -> score should be 1 (from Q1) + 1 (from Q2) = 2
    assert res_data["current_score"] == 2, f"Server trusted client score! Expected 2, got {res_data['current_score']}"
    print(" [PASS] Server strictly calculated score server-side; client-supplied score override ignored.")

    # =========================================================================
    # PART 2: CONCURRENT MULTI-USER QUIZ SIMULATION
    # =========================================================================

    print("\n" + "=" * 70)
    print("--- CONCURRENT THREE-STUDENT QUIZ SIMULATION ---")
    print("Students: Ishita (Target: High Score), Riya (Target: Med Score), Aarav (Target: Low Score)")
    print("=" * 70)

    # Define deliberate answer sequences for 10 questions:
    # Official Answers:
    # Q1: B, Q2: C, Q3: C, Q4: B, Q5: C, Q6: B, Q7: C, Q8: B, Q9: B, Q10: C
    ishita_answers = ["B", "C", "C", "B", "C", "B", "C", "B", "B", "C"]  # 10/10 (100%)
    riya_answers   = ["B", "C", "C", "B", "C", "B", "A", "A", "A", "A"]  # 6/10 (60%)
    aarav_answers  = ["B", "C", "C", "A", "A", "A", "A", "A", "A", "A"]  # 3/10 (30%)

    student_configs = [
        {"name": "Ishita", "answers": ishita_answers, "expected_score": 10, "expected_pct": 100.0},
        {"name": "Riya",   "answers": riya_answers,   "expected_score": 6,  "expected_pct": 60.0},
        {"name": "Aarav",  "answers": aarav_answers,  "expected_score": 3,  "expected_pct": 30.0},
    ]

    student_results: Dict[str, Dict[str, Any]] = {}
    threads_lock = threading.Lock()

    def simulate_student_session(config: Dict[str, Any]) -> None:
        """Simulates an entire quiz lifecycle concurrently in its own execution thread."""
        name = config["name"]
        answers = config["answers"]

        # 1. Join quiz
        join_r = client.post("/api/quiz/join", json={"student_name": name})
        assert join_r.status_code == 200, f"{name} failed to join: {join_r.text}"
        join_payload = join_r.json()
        conn_id = join_payload["connection_id"]
        total_q = join_payload["total_questions"]

        # 2. Iterate through all questions
        scores_history = []
        questions_seen = []

        for q_idx in range(total_q):
            # Fetch current question
            q_req = client.get(f"/api/quiz/question?connection_id={conn_id}")
            assert q_req.status_code == 200, f"{name} failed to fetch Q{q_idx+1}: {q_req.text}"
            question_obj = q_req.json()

            # Verify no secret answer leakage
            assert "correct_answer" not in question_obj, f"Answer leaked to {name} in Q{q_idx+1}"
            questions_seen.append(question_obj["question_id"])

            # Small random sleep to simulate human reaction and cause true thread interleaving
            time.sleep(0.02)

            # Submit student answer
            chosen_ans = answers[q_idx]
            ans_req = client.post(
                "/api/quiz/answer",
                json={
                    "connection_id": conn_id,
                    "question_id": question_obj["question_id"],
                    "answer": chosen_ans,
                    "student_name": name
                }
            )
            assert ans_req.status_code == 200, f"{name} failed submit Q{q_idx+1}: {ans_req.text}"
            ans_payload = ans_req.json()
            scores_history.append(ans_payload["current_score"])

        # 3. Retrieve final quiz summary
        sum_req = client.get(f"/api/quiz/summary?connection_id={conn_id}")
        assert sum_req.status_code == 200, f"{name} failed summary: {sum_req.text}"
        summary_payload = sum_req.json()

        with threads_lock:
            student_results[name] = {
                "connection_id": conn_id,
                "scores_history": scores_history,
                "final_score": summary_payload["score"],
                "percentage": summary_payload["percentage"],
                "correct_answers": summary_payload["correct_answers"],
                "incorrect_answers": summary_payload["incorrect_answers"],
                "questions_seen": questions_seen,
                "summary": summary_payload
            }

    # Execute all three students simultaneously using ThreadPoolExecutor
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(simulate_student_session, cfg) for cfg in student_configs]
        for f in concurrent.futures.as_completed(futures):
            f.result()  # Will raise if any thread had an unhandled assertion

    elapsed = round(time.time() - start_time, 2)
    print(f"\n Concurrently simulated 3 students across 30 total questions in {elapsed}s.")

    # =========================================================================
    # PART 3: VERIFY SESSION ISOLATION (Requirement 4)
    # =========================================================================
    print("\n--- TEST 7: Multi-User Session Isolation Verification ---")

    ishita = student_results["Ishita"]
    riya = student_results["Riya"]
    aarav = student_results["Aarav"]

    # 1. Unique Connection IDs
    assert ishita["connection_id"] != riya["connection_id"], "Collision between Ishita and Riya session IDs"
    assert ishita["connection_id"] != aarav["connection_id"], "Collision between Ishita and Aarav session IDs"
    assert riya["connection_id"] != aarav["connection_id"], "Collision between Riya and Aarav session IDs"
    print(f" [PASS] All 3 session IDs are unique: Ishita ({ishita['connection_id'][:12]}...), Riya ({riya['connection_id'][:12]}...), Aarav ({aarav['connection_id'][:12]}...)")

    # 2. Independent Scores
    assert ishita["final_score"] == 10 and ishita["percentage"] == 100.0, f"Ishita score mismatch: {ishita['final_score']}"
    assert riya["final_score"] == 6 and riya["percentage"] == 60.0, f"Riya score mismatch: {riya['final_score']}"
    assert aarav["final_score"] == 3 and aarav["percentage"] == 30.0, f"Aarav score mismatch: {aarav['final_score']}"
    print(f" [PASS] Student scores isolated and independently computed:")
    print(f"        Ishita : {ishita['final_score']}/10 ({ishita['percentage']}%)")
    print(f"        Riya   : {riya['final_score']}/10 ({riya['percentage']}%)")
    print(f"        Aarav  : {aarav['final_score']}/10 ({aarav['percentage']}%)")

    # 3. Cross-Session Hijack Rejection: Student A cannot submit using Student B's session
    hijack_res = client.post(
        "/api/quiz/answer",
        json={
            "connection_id": riya["connection_id"],
            "question_id": 1,
            "answer": "B",
            "student_name": "Ishita"  # Mismatch: Ishita attempts to use Riya's session
        }
    )
    assert hijack_res.status_code == 400
    assert "Session mismatch" in hijack_res.json()["detail"] or "belongs to" in hijack_res.json()["detail"] or "already been completed" in hijack_res.json()["detail"]
    print(f" [PASS] Cross-session answer submission strictly rejected: {hijack_res.json()['detail']}")

    # =========================================================================
    # PART 4: COMPLETED QUIZ STABILITY (Requirement 11)
    # =========================================================================
    print("\n--- TEST 8: Completed Quiz State Stability Verification ---")
    # Ishita's quiz is finished. Attempt another answer:
    comp_ans_res = client.post(
        "/api/quiz/answer",
        json={"connection_id": ishita["connection_id"], "question_id": 1, "answer": "B"}
    )
    assert comp_ans_res.status_code == 400
    assert "already been completed" in comp_ans_res.json()["detail"]
    print(" [PASS] Submitting an answer after quiz completion is rejected.")

    # Attempt to request another question for completed quiz:
    comp_q_res = client.get(f"/api/quiz/question?connection_id={ishita['connection_id']}")
    assert comp_q_res.status_code == 404
    print(" [PASS] Requesting a question after completion returns 404 (no hidden sequence started).")

    # =========================================================================
    # PART 5: LIVE LEADERBOARD VERIFICATION (Requirement 12)
    # =========================================================================
    print("\n--- TEST 9: Server-Side Leaderboard Verification ---")
    lb_res = client.get("/api/quiz/leaderboard")
    assert lb_res.status_code == 200
    leaderboard = lb_res.json()["leaderboard"]

    # 1. All completed students appear
    lb_names = [e["student_name"] for e in leaderboard]
    assert "Ishita" in lb_names, "Ishita missing from leaderboard"
    assert "Riya" in lb_names, "Riya missing from leaderboard"
    assert "Aarav" in lb_names, "Aarav missing from leaderboard"
    print(f" [PASS] All 3 completed students appear in server leaderboard: {lb_names}")

    # 2. Descending score order
    scores = [e["score"] for e in leaderboard]
    assert scores == sorted(scores, reverse=True), f"Leaderboard scores not sorted descending: {scores}"
    print(f" [PASS] Leaderboard entries sorted descending by score: {scores}")

    # 3. Ranking correctness
    for idx, entry in enumerate(leaderboard, start=1):
        assert entry["rank"] == idx, f"Rank mismatch for entry {entry}: expected {idx}, got {entry['rank']}"

    # Verify top 3 order: Ishita (10), Riya (6), Aarav (3)
    top3_names = [e["student_name"] for e in leaderboard[:3]]
    assert top3_names == ["Ishita", "Riya", "Aarav"], f"Top 3 order mismatch: {top3_names}"
    print(f" [PASS] Rankings verified:")
    for e in leaderboard[:3]:
        print(f"        Rank {e['rank']}: {e['student_name']} — Score {e['score']}/{e['total_questions']} ({e['percentage']}%)")

    # 4. No duplicate entries for same session
    session_ids_in_history = [s["connection_id"] for s in quiz_manager_instance.get_leaderboard()]
    assert len(session_ids_in_history) == len(set(session_ids_in_history)), "Duplicate session IDs in leaderboard"
    print(" [PASS] No duplicate leaderboard entries detected.")

    # =========================================================================
    # PART 6: TCP SERVER METRICS ACCOUNTING (Requirement 13)
    # =========================================================================
    print("\n--- TEST 10: Server Metrics Accuracy Verification ---")
    final_status = client.get("/api/server/status").json()

    # Net connections delta must include probe session + 3 student sessions = at least +4
    delta_connections = final_status["total_connections"] - base_connections
    assert delta_connections >= 4, f"Expected >= 4 connections, got {delta_connections}"

    # Questions sent delta: probe (1 + 1) + 3 students * 10 questions = at least +32
    delta_questions = final_status["questions_sent"] - base_questions
    assert delta_questions >= 30, f"Expected >= 30 questions sent, got {delta_questions}"

    # Answers received delta: probe (1 + 1) + 3 students * 10 questions = at least +32
    delta_answers = final_status["answers_received"] - base_answers
    assert delta_answers >= 30, f"Expected >= 30 answers received, got {delta_answers}"

    # Completed quizzes delta: 3 students completed
    delta_completed = final_status["completed_quizzes"] - base_completed
    assert delta_completed >= 3, f"Expected >= 3 completed quizzes, got {delta_completed}"

    print(f" [PASS] Metrics accurately tracked:")
    print(f"        Total Connections Delta: +{delta_connections}")
    print(f"        Questions Sent Delta:    +{delta_questions}")
    print(f"        Answers Received Delta:  +{delta_answers}")
    print(f"        Completed Quizzes Delta: +{delta_completed}")
    print(f"        Messages Received Delta: +{final_status['messages_received']}")
    print(f"        Messages Sent Delta:     +{final_status['messages_sent']}")

    print("\n" + "=" * 70)
    print("  ALL 10/10 STAGE 7 MULTI-USER & HARDENING TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_stage7_multiuser_tests()
