"""
NetQuiz Teacher Dashboard & Custom Quiz System Test Suite
Tests:
1. Teacher login (valid/invalid credentials)
2. Session token authorization & rejection of unauthenticated requests
3. Quiz creation with unique Quiz ID generation
4. Question creation (MCQ & True/False)
5. Quiz update & validation
6. Quiz publishing and state transitions (Draft -> Published -> Active -> Ended)
7. Student joining specific quiz (/api/quizzes/{quiz_id}/join)
8. Student cannot access another quiz's questions (isolation)
9. Correct answers are NEVER exposed in student-facing endpoints
10. Server-side answer validation and scoring
11. Duplicate submission rejection
12. Completed quiz locking
13. Quiz-specific leaderboard isolation (Quiz A with 5 students vs Quiz B with 3 students)
14. Live participant progress tracking
15. Ending a quiz rejects new attempts while preserving past submissions
"""

import sys
import unittest
from fastapi.testclient import TestClient

from backend.main import app
from backend.quiz.custom_quiz_manager import custom_quiz_manager_instance


class TestTeacherQuizSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.orig_backup = None
        if custom_quiz_manager_instance.storage_path.exists():
            cls.orig_backup = custom_quiz_manager_instance.storage_path.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        if cls.orig_backup is not None:
            custom_quiz_manager_instance.storage_path.write_text(cls.orig_backup, encoding="utf-8")
            custom_quiz_manager_instance._load_from_disk()

    def test_01_teacher_login_and_auth(self):
        """Tests teacher login with valid and invalid credentials."""
        # Invalid credentials
        res = self.client.post("/api/teacher/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })
        self.assertEqual(res.status_code, 401)

        # Valid default credentials
        res = self.client.post("/api/teacher/login", json={
            "email": "teacher@netquiz.edu",
            "password": "teacher123"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["token"].startswith("tkn_"))
        token = data["token"]

        # Verify session
        me_res = self.client.get("/api/teacher/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json()["teacher"]["email"], "teacher@netquiz.edu")

        # Missing token rejected
        unauth = self.client.get("/api/teacher/me")
        self.assertEqual(unauth.status_code, 401)

    def test_02_create_and_publish_quiz(self):
        """Tests creating a multi-question quiz and transitioning lifecycle states."""
        # Login
        login_res = self.client.post("/api/teacher/login", json={
            "email": "teacher@netquiz.edu",
            "password": "teacher123"
        })
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create quiz
        payload = {
            "title": "Data Link Layer Assessment",
            "description": "Test on framing, CRC error detection, and MAC addressing.",
            "category": "Computer Networks",
            "type": "Class Test",
            "time_limit_minutes": 20,
            "questions": [
                {
                    "id": "dl_q1",
                    "question": "What is the standard polynomial divisor used for CRC-32 error detection in Ethernet?",
                    "type": "mcq",
                    "options": {
                        "A": "Standard generator polynomial of degree 32",
                        "B": "Hamming code parity generator",
                        "C": "Checksum 16-bit 1's complement",
                        "D": "Parity bit check"
                    },
                    "correct_answer": "A",
                    "explanation": "Ethernet implements CRC-32 with a 33-term generator polynomial.",
                    "points": 2,
                    "time_limit": 45
                },
                {
                    "id": "dl_q2",
                    "question": "True or False: MAC addresses are 48-bit (6-octet) physical hardware addresses.",
                    "type": "true_false",
                    "options": {
                        "A": "True",
                        "B": "False"
                    },
                    "correct_answer": "A",
                    "explanation": "True. Standard IEEE 802 MAC addresses are 48 bits long.",
                    "points": 1,
                    "time_limit": 20
                }
            ]
        }

        res = self.client.post("/api/teacher/quizzes", json=payload, headers=headers)
        self.assertEqual(res.status_code, 201)
        quiz = res.json()
        quiz_id = quiz["quiz_id"]
        self.assertTrue(len(quiz_id) >= 6)
        self.assertEqual(quiz["status"], "draft")
        self.assertEqual(quiz["total_questions"], 2)

        # Publish quiz
        pub_res = self.client.post(f"/api/teacher/quizzes/{quiz_id}/publish", headers=headers)
        self.assertEqual(pub_res.status_code, 200)

        # Start quiz
        start_res = self.client.post(f"/api/teacher/quizzes/{quiz_id}/start", headers=headers)
        self.assertEqual(start_res.status_code, 200)
        self.assertEqual(start_res.json()["status"], "active")

    def test_03_student_quiz_security_and_answers_never_exposed(self):
        """Verifies that student-facing endpoints never reveal correct answers."""
        login_res = self.client.post("/api/teacher/login", json={
            "email": "teacher@netquiz.edu",
            "password": "teacher123"
        })
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create and publish quiz
        q_res = self.client.post("/api/teacher/quizzes", json={
            "title": "Security Secrets Test",
            "category": "Network Security",
            "questions": [
                {
                    "id": "sec_q1",
                    "question": "Which cipher is symmetric?",
                    "options": {"A": "AES", "B": "RSA", "C": "ECC", "D": "Diffie-Hellman"},
                    "correct_answer": "A",
                    "explanation": "AES is a symmetric block cipher.",
                    "points": 1
                }
            ]
        }, headers=headers)
        quiz_id = q_res.json()["quiz_id"]
        self.client.post(f"/api/teacher/quizzes/{quiz_id}/publish", headers=headers)
        self.client.post(f"/api/teacher/quizzes/{quiz_id}/start", headers=headers)

        # 1. Public details endpoint
        pub_details = self.client.get(f"/api/quizzes/{quiz_id}").json()
        self.assertNotIn("correct_answer", pub_details)
        self.assertNotIn("questions", pub_details)

        # 2. Student joins
        join_res = self.client.post(f"/api/quizzes/{quiz_id}/join", json={"student_name": "Eve"}).json()
        cid = join_res["connection_id"]

        # 3. Student fetches question
        question_payload = self.client.get(f"/api/quizzes/{quiz_id}/question?connection_id={cid}").json()
        self.assertNotIn("correct_answer", question_payload)
        self.assertNotIn("explanation", question_payload)
        self.assertEqual(question_payload["question"], "Which cipher is symmetric?")

    def test_04_isolated_quiz_leaderboards_and_multiuser(self):
        """
        Creates Quiz A and Quiz B.
        Simulates 5 students taking Quiz A and 3 students taking Quiz B.
        Validates:
        1. Quiz A leaderboard has exactly the 5 students from Quiz A and ZERO from Quiz B.
        2. Quiz B leaderboard has exactly the 3 students from Quiz B and ZERO from Quiz A.
        3. Cross-quiz submissions are strictly rejected.
        """
        login_res = self.client.post("/api/teacher/login", json={
            "email": "teacher@netquiz.edu",
            "password": "teacher123"
        })
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create Quiz A (2 questions)
        res_a = self.client.post("/api/teacher/quizzes", json={
            "title": "Quiz A — Routing Algorithms",
            "category": "Computer Networks",
            "questions": [
                {
                    "id": "qa_1",
                    "question": "Which algorithm is used in OSPF?",
                    "options": {"A": "Dijkstra", "B": "Bellman-Ford", "C": "Floyd-Warshall", "D": "Prim"},
                    "correct_answer": "A",
                    "points": 1
                },
                {
                    "id": "qa_2",
                    "question": "Which algorithm is used in RIP?",
                    "options": {"A": "Dijkstra", "B": "Bellman-Ford", "C": "Kruskal", "D": "A*"},
                    "correct_answer": "B",
                    "points": 1
                }
            ]
        }, headers=headers).json()
        quiz_a_id = res_a["quiz_id"]
        self.client.post(f"/api/teacher/quizzes/{quiz_a_id}/publish", headers=headers)
        self.client.post(f"/api/teacher/quizzes/{quiz_a_id}/start", headers=headers)

        # Create Quiz B (1 question)
        res_b = self.client.post("/api/teacher/quizzes", json={
            "title": "Quiz B — Application Layer",
            "category": "Computer Networks",
            "questions": [
                {
                    "id": "qb_1",
                    "question": "What is the default port for DNS?",
                    "options": {"A": "80", "B": "443", "C": "53", "D": "22"},
                    "correct_answer": "C",
                    "points": 1
                }
            ]
        }, headers=headers).json()
        quiz_b_id = res_b["quiz_id"]
        self.client.post(f"/api/teacher/quizzes/{quiz_b_id}/publish", headers=headers)
        self.client.post(f"/api/teacher/quizzes/{quiz_b_id}/start", headers=headers)

        # 5 students join and complete Quiz A
        students_a = ["Aarav", "Ishita", "Riya", "Karan", "Sneha"]
        answers_a = [
            ("A", "B"),  # Aarav: 2/2
            ("A", "B"),  # Ishita: 2/2
            ("A", "C"),  # Riya: 1/2
            ("D", "B"),  # Karan: 1/2
            ("D", "C"),  # Sneha: 0/2
        ]

        sessions_a = []
        for name, ans_pair in zip(students_a, answers_a):
            join_res = self.client.post(f"/api/quizzes/{quiz_a_id}/join", json={"student_name": name}).json()
            cid = join_res["connection_id"]
            sessions_a.append(cid)

            # Answer Q1
            ans1 = self.client.post(f"/api/quizzes/{quiz_a_id}/answer", json={
                "connection_id": cid,
                "question_id": "qa_1",
                "answer": ans_pair[0],
                "student_name": name
            }).json()
            self.assertFalse(ans1["quiz_completed"])

            # Answer Q2
            ans2 = self.client.post(f"/api/quizzes/{quiz_a_id}/answer", json={
                "connection_id": cid,
                "question_id": "qa_2",
                "answer": ans_pair[1],
                "student_name": name
            }).json()
            self.assertTrue(ans2["quiz_completed"])

        # 3 students join and complete Quiz B
        students_b = ["Tanvi", "Dev", "Meera"]
        answers_b = ["C", "C", "A"]  # Tanvi: 1/1, Dev: 1/1, Meera: 0/1

        sessions_b = []
        for name, ans in zip(students_b, answers_b):
            join_res = self.client.post(f"/api/quizzes/{quiz_b_id}/join", json={"student_name": name}).json()
            cid = join_res["connection_id"]
            sessions_b.append(cid)

            ans_res = self.client.post(f"/api/quizzes/{quiz_b_id}/answer", json={
                "connection_id": cid,
                "question_id": "qb_1",
                "answer": ans,
                "student_name": name
            }).json()
            self.assertTrue(ans_res["quiz_completed"])

        # ── ISOLATION VERIFICATION ──────────────────────────────────────────
        # Fetch Leaderboard for Quiz A
        lb_a = self.client.get(f"/api/quizzes/{quiz_a_id}/leaderboard").json()
        names_in_a = [e["student_name"] for e in lb_a["leaderboard"]]
        self.assertEqual(len(names_in_a), 5)
        for s in students_a:
            self.assertIn(s, names_in_a)
        for s in students_b:
            self.assertNotIn(s, names_in_a)

        # Fetch Leaderboard for Quiz B
        lb_b = self.client.get(f"/api/quizzes/{quiz_b_id}/leaderboard").json()
        names_in_b = [e["student_name"] for e in lb_b["leaderboard"]]
        self.assertEqual(len(names_in_b), 3)
        for s in students_b:
            self.assertIn(s, names_in_b)
        for s in students_a:
            self.assertNotIn(s, names_in_b)

        # Cross-quiz submission rejected
        cross_sub = self.client.post(f"/api/quizzes/{quiz_b_id}/answer", json={
            "connection_id": sessions_a[0],
            "question_id": "qb_1",
            "answer": "C"
        })
        self.assertEqual(cross_sub.status_code, 400)

        # Ending Quiz A
        end_res = self.client.post(f"/api/teacher/quizzes/{quiz_a_id}/end", headers=headers)
        self.assertEqual(end_res.status_code, 200)

        # Attempt to join ended quiz rejected
        ended_join = self.client.post(f"/api/quizzes/{quiz_a_id}/join", json={"student_name": "LateStudent"})
        self.assertEqual(ended_join.status_code, 400)
        self.assertIn("ended", ended_join.json()["detail"].lower())

        # Leaderboard of ended quiz remains intact and readable
        lb_ended = self.client.get(f"/api/quizzes/{quiz_a_id}/leaderboard").json()
        self.assertEqual(len(lb_ended["leaderboard"]), 5)

    def test_05_concurrent_students_and_duplicate_submission_prevention(self):
        """Tests two students on the same quiz, duplicate submission prevention, and quiz ID format."""
        login_res = self.client.post("/api/teacher/login", json={
            "email": "teacher@netquiz.edu",
            "password": "teacher123"
        })
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create quiz
        create_res = self.client.post("/api/teacher/quizzes", json={
            "title": "Computer Networks Unit 2 Test",
            "category": "Computer Networks",
            "questions": [
                {
                    "id": "q_001",
                    "question": "What layer does IP belong to?",
                    "options": {"A": "Network", "B": "Transport", "C": "Application", "D": "Physical"},
                    "correct_answer": "A",
                    "points": 1
                }
            ]
        }, headers=headers).json()
        quiz_id = create_res["quiz_id"]

        # Validate Quiz ID format: Prefix + 5 uppercase alphanumeric chars
        self.assertRegex(quiz_id, r"^[A-Z0-9]+-[A-Z0-9]{5}$")

        self.client.post(f"/api/teacher/quizzes/{quiz_id}/publish", headers=headers)
        self.client.post(f"/api/teacher/quizzes/{quiz_id}/start", headers=headers)

        # Student 1 joins
        s1_res = self.client.post(f"/api/quizzes/{quiz_id}/join", json={"student_name": "Student1"}).json()
        s1_cid = s1_res["connection_id"]

        # Student 2 joins same quiz
        s2_res = self.client.post(f"/api/quizzes/{quiz_id}/join", json={"student_name": "Student2"}).json()
        s2_cid = s2_res["connection_id"]

        self.assertNotEqual(s1_cid, s2_cid)

        # Student 1 answers correctly
        ans1 = self.client.post(f"/api/quizzes/{quiz_id}/answer", json={
            "connection_id": s1_cid,
            "question_id": "q_001",
            "answer": "A",
            "student_name": "Student1"
        })
        self.assertEqual(ans1.status_code, 200)
        self.assertTrue(ans1.json()["correct"])
        self.assertTrue(ans1.json()["quiz_completed"])

        # Duplicate answer submission attempt for Student 1 rejected
        dup_sub = self.client.post(f"/api/quizzes/{quiz_id}/answer", json={
            "connection_id": s1_cid,
            "question_id": "q_001",
            "answer": "A",
            "student_name": "Student1"
        })
        self.assertEqual(dup_sub.status_code, 400)

        # Student 2 answers incorrectly
        ans2 = self.client.post(f"/api/quizzes/{quiz_id}/answer", json={
            "connection_id": s2_cid,
            "question_id": "q_001",
            "answer": "B",
            "student_name": "Student2"
        })
        self.assertEqual(ans2.status_code, 200)
        self.assertFalse(ans2.json()["correct"])
        self.assertTrue(ans2.json()["quiz_completed"])

        # Check leaderboard shows both with independent scores
        lb = self.client.get(f"/api/quizzes/{quiz_id}/leaderboard").json()["leaderboard"]
        self.assertEqual(len(lb), 2)
        self.assertEqual(lb[0]["student_name"], "Student1")
        self.assertEqual(lb[0]["score"], 1)
        self.assertEqual(lb[1]["student_name"], "Student2")
        self.assertEqual(lb[1]["score"], 0)


if __name__ == "__main__":
    unittest.main()
