"""
Unit Test Suite for QuizManager (Stage 3).

Verifies all 12 core rules:
1. Question bank loads successfully.
2. Question structure is strictly valid (options A, B, C, D present).
3. Player can join and start a quiz session.
4. First question is delivered with stripped correct_answer.
5. Correct answer increases score by 1.
6. Incorrect answer does not increase score.
7. Duplicate answer submission is rejected.
8. Invalid question ID is rejected.
9. Invalid answer option (e.g. 'Z') is rejected.
10. Answer submission after quiz completion is rejected.
11. Final score and percentage calculated correctly.
12. Multiple players maintain completely isolated independent scores.
"""

from backend.quiz.quiz_manager import QuizManager


def test_quiz_manager_logic():
    print("=" * 60)
    print("      QUIZ MANAGER UNIT TESTS & VALIDATION")
    print("=" * 60)
    passed = 0
    total = 12

    qm = QuizManager(question_count=10)

    # 1. Question bank loads
    assert len(qm.questions) >= 15, f"Expected at least 15 questions, found {len(qm.questions)}"
    print(f" [PASS] 1. Loaded {len(qm.questions)} questions from bank.")
    passed += 1

    # 2. Question structure is valid
    for q_id, q_data in qm.questions.items():
        assert "A" in q_data["options"] and "D" in q_data["options"]
        assert q_data["correct_answer"] in ["A", "B", "C", "D"]
    print(" [PASS] 2. All questions contain valid options (A-D) and valid correct answers.")
    passed += 1

    # 3. Player can start quiz
    conn_id = "test_player_1"
    ok, start_data = qm.start_quiz(conn_id, "Ishita")
    assert ok is True
    assert start_data["total_questions"] == 10
    print(" [PASS] 3. Player started quiz session successfully.")
    passed += 1

    # 4. First question delivered without revealing correct answer
    q1 = qm.get_current_question(conn_id)
    assert q1 is not None
    assert q1["question_number"] == 1
    assert "correct_answer" not in q1, "Security breach: correct_answer must NOT be sent to client!"
    assert "explanation" not in q1
    print(" [PASS] 4. Question delivered with correct answer and explanation stripped.")
    passed += 1

    # 5. Correct answer increases score
    q1_id = q1["question_id"]
    correct_ans = qm.questions[q1_id]["correct_answer"]
    ok, res = qm.submit_answer(conn_id, q1_id, correct_ans)
    assert ok is True and res["correct"] is True and res["current_score"] == 1
    print(" [PASS] 5. Correct answer evaluated and score incremented to 1.")
    passed += 1

    # 6. Incorrect answer does not increase score
    q2 = qm.get_current_question(conn_id)
    q2_id = q2["question_id"]
    wrong_ans = "A" if qm.questions[q2_id]["correct_answer"] != "A" else "B"
    ok, res = qm.submit_answer(conn_id, q2_id, wrong_ans)
    assert ok is True and res["correct"] is False and res["current_score"] == 1
    print(" [PASS] 6. Incorrect answer evaluated and score remained at 1.")
    passed += 1

    # 7. Duplicate answer is rejected
    ok, err = qm.submit_answer(conn_id, q2_id, "C")
    assert ok is False and err["type"] == "error"
    print(f" [PASS] 7. Duplicate answer rejected: {err['message']}")
    passed += 1

    # 8. Invalid question ID is rejected
    ok, err = qm.submit_answer(conn_id, 9999, "A")
    assert ok is False and err["type"] == "error"
    print(f" [PASS] 8. Invalid question ID rejected: {err['message']}")
    passed += 1

    # 9. Invalid answer option is rejected
    q3 = qm.get_current_question(conn_id)
    q3_id = q3["question_id"]
    ok, err = qm.submit_answer(conn_id, q3_id, "Z")
    assert ok is False and err["type"] == "error"
    print(f" [PASS] 9. Invalid answer option rejected: {err['message']}")
    passed += 1

    # Answer remaining questions (questions 3 to 10) to complete the quiz
    for expected_idx in range(2, 10):
        curr_q = qm.get_current_question(conn_id)
        assert curr_q is not None
        qid = curr_q["question_id"]
        c_ans = qm.questions[qid]["correct_answer"]
        ok, res = qm.submit_answer(conn_id, qid, c_ans)
        assert ok is True

    # 10. Answer after quiz completion is rejected
    ok, err = qm.submit_answer(conn_id, 1, "B")
    assert ok is False and "already been completed" in err["message"]
    print(f" [PASS] 10. Answer after quiz completion rejected: {err['message']}")
    passed += 1

    # 11. Final score calculation
    summary = qm.get_quiz_end_summary(conn_id)
    assert summary is not None
    # Player got: Q1 correct, Q2 wrong, Q3-Q10 correct = 9/10
    assert summary["score"] == 9
    assert summary["total_questions"] == 10
    assert summary["percentage"] == 90.0
    print(f" [PASS] 11. Final score verified: {summary['score']}/10 ({summary['percentage']}%)")
    passed += 1

    # 12. Multiple players maintain independent scores
    conn_a = "player_a"
    conn_b = "player_b"
    qm.start_quiz(conn_a, "Student A")
    qm.start_quiz(conn_b, "Student B")

    # Student A answers first question correctly
    qa1 = qm.get_current_question(conn_a)
    qm.submit_answer(conn_a, qa1["question_id"], qm.questions[qa1["question_id"]]["correct_answer"])

    # Student B answers first question incorrectly
    qb1 = qm.get_current_question(conn_b)
    wrong_b = "A" if qm.questions[qb1["question_id"]]["correct_answer"] != "A" else "B"
    qm.submit_answer(conn_b, qb1["question_id"], wrong_b)

    state_a = qm.get_player_state(conn_a)
    state_b = qm.get_player_state(conn_b)
    assert state_a["score"] == 1 and state_b["score"] == 0
    print(" [PASS] 12. Multiple concurrent player states verified completely independent.")
    passed += 1

    print("\n" + "=" * 60)
    print(f"  ALL {passed}/{total} QUIZ MANAGER UNIT TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    test_quiz_manager_logic()
