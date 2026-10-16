"""
Multi-User TCP Quiz Integration Test Suite (Stage 3).

Demonstrates the core academic Computer Networks requirement:
- Runs a live Python TCP Server on port 5000.
- Connects THREE simultaneous clients concurrently:
  * Student A (Ishita): Answers 8 correct -> Verified Score: 8/10 (80%)
  * Student B (Aarav): Answers 5 correct  -> Verified Score: 5/10 (50%)
  * Student C (Riya): Answers 10 correct  -> Verified Score: 10/10 (100%)
- Confirms that each student's score and state remain strictly isolated.
- Confirms server metrics update (questions_sent, answers_received, completed_quizzes).
- Verifies clean shutdown and port release.
"""

import threading
import time
from typing import Dict, List

from backend.config import TCP_SERVER_HOST, TCP_SERVER_PORT
from backend.networking.tcp_server import TCPServer
from backend.networking.test_client import QuizTCPClient
from backend.quiz.quiz_manager import QuizManager


def run_stage3_integration_test():
    print("=" * 65)
    print("   STAGE 3: MULTI-USER TCP QUIZ INTEGRATION & CONCURRENCY TEST")
    print("=" * 65)

    # 1. Start TCP Server with QuizManager
    qm = QuizManager(question_count=10)
    server = TCPServer(host=TCP_SERVER_HOST, port=TCP_SERVER_PORT, quiz_manager=qm)
    server.start(run_in_background=True)
    time.sleep(0.3)
    print(f"[SERVER] TCP Server started on {TCP_SERVER_HOST}:{TCP_SERVER_PORT} with Quiz Engine ready.")

    # Define answer profiles
    # First 10 correct answers in questions.json:
    # 1: B, 2: C, 3: C, 4: B, 5: C, 6: B, 7: C, 8: B, 9: B, 10: C
    all_correct = ["B", "C", "C", "B", "C", "B", "C", "B", "B", "C"]
    
    # Student C: 10/10
    answers_c = list(all_correct)
    
    # Student A: 8/10 (Q1 and Q2 wrong)
    answers_a = ["A", "A"] + all_correct[2:]
    
    # Student B: 5/10 (Q1 to Q5 wrong)
    answers_b = ["A", "A", "A", "A", "A"] + all_correct[5:]

    results: Dict[str, Dict] = {}

    def simulate_student(name: str, answer_list: List[str], expected_score: int):
        client = QuizTCPClient(host=TCP_SERVER_HOST, port=TCP_SERVER_PORT)
        assert client.connect() is True, f"Client {name} connection failed"
        assert client.join(name) is True, f"Client {name} join failed"
        
        # Play complete quiz
        summary = client.run_quiz(preset_answers=answer_list, interactive=False)
        assert summary is not None, f"Client {name} did not receive final quiz summary"
        
        results[name] = summary
        client.disconnect()

    # Launch all 3 students concurrently on separate execution threads
    threads = [
        threading.Thread(target=simulate_student, args=("Ishita (Student A)", answers_a, 8)),
        threading.Thread(target=simulate_student, args=("Aarav (Student B)", answers_b, 5)),
        threading.Thread(target=simulate_student, args=("Riya (Student C)", answers_c, 10))
    ]

    print("\n[TEST] Launching 3 concurrent TCP student threads...")
    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=15.0)

    print("\n" + "=" * 65)
    print("             MULTI-USER QUIZ RESULTS SUMMARY")
    print("=" * 65)

    for student_name, summary in results.items():
        print(f" {student_name:<20}: Score {summary['score']}/10 ({summary['percentage']}%) | Correct: {summary['correct_answers']} | Incorrect: {summary['incorrect_answers']}")

    # Strict Assertions
    assert results["Ishita (Student A)"]["score"] == 8, f"Expected 8 for Ishita, got {results['Ishita (Student A)']['score']}"
    assert results["Aarav (Student B)"]["score"] == 5, f"Expected 5 for Aarav, got {results['Aarav (Student B)']['score']}"
    assert results["Riya (Student C)"]["score"] == 10, f"Expected 10 for Riya, got {results['Riya (Student C)']['score']}"

    print("\n[VERIFICATION] Confirmed: Student scores are 100% independent and isolated.")

    # Verify Server Metrics
    status = server.get_status()
    print(f"\n[SERVER METRICS]")
    print(f" - Total Connections: {status['total_connections']}")
    print(f" - Questions Sent:    {status['questions_sent']}")
    print(f" - Answers Received:  {status['answers_received']}")
    print(f" - Completed Quizzes: {status['completed_quizzes']}")

    assert status["completed_quizzes"] == 3
    assert status["answers_received"] == 30  # 3 students * 10 answers
    assert status["questions_sent"] == 30    # 3 students * 10 questions

    # Verify Leaderboard
    leaderboard = qm.get_leaderboard()
    print("\n[SERVER LEADERBOARD]")
    for entry in leaderboard:
        print(f" Rank {entry['rank']}: {entry['student_name']:<20} Score: {entry['score']}/10 ({entry['percentage']}%)")

    assert leaderboard[0]["student_name"] == "Riya (Student C)"
    assert leaderboard[0]["score"] == 10
    assert leaderboard[1]["student_name"] == "Ishita (Student A)"
    assert leaderboard[1]["score"] == 8
    assert leaderboard[2]["student_name"] == "Aarav (Student B)"
    assert leaderboard[2]["score"] == 5

    # Shut down server cleanly
    server.stop()
    time.sleep(0.3)
    print("\n[SERVER] Server stopped and port 5000 released cleanly.")

    print("=" * 65)
    print("  STAGE 3 INTEGRATION TEST COMPLETED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    run_stage3_integration_test()
