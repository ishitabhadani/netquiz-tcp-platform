"""
NetQuiz Custom Quiz & Teacher Management Engine
Manages teacher-created quizzes, persistent JSON storage, student sessions,
and quiz-specific leaderboards.
"""

import datetime
import json
import logging
import random
import string
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.config import CUSTOM_QUIZZES_FILE_PATH, DATA_DIR

logger = logging.getLogger("NetQuiz.Quiz.CustomManager")


def generate_unique_quiz_id(existing_ids: set, title: str = "", category: str = "") -> str:
    """Generates a memorable and distinct quiz code, e.g. CN2-8F4K2 or QZ-A83F9."""
    # Prefix from category or title
    prefix = "QZ"
    if category:
        words = category.split()
        if len(words) >= 2:
            prefix = f"{words[0][0].upper()}{words[1][0].upper()}2"
        elif len(words) == 1 and len(words[0]) >= 2:
            prefix = words[0][:2].upper()
    elif title:
        words = title.split()
        if len(words) >= 2:
            prefix = f"{words[0][0].upper()}{words[1][0].upper()}"

    for _ in range(50):
        chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        candidate = f"{prefix}-{chars}"
        if candidate not in existing_ids:
            return candidate

    return f"QZ-{uuid.uuid4().hex[:6].upper()}"


class CustomQuizManager:
    """
    Thread-safe manager for teacher-created quizzes, isolated sessions,
    and quiz-specific leaderboards with persistent JSON storage.
    """

    def __init__(self, storage_path: Path = CUSTOM_QUIZZES_FILE_PATH) -> None:
        self.storage_path = Path(storage_path)
        self.lock = threading.RLock()
        
        # In-memory index of quizzes: { quiz_id -> quiz_dict }
        self.quizzes: Dict[str, Dict[str, Any]] = {}
        
        # In-memory index of active/completed custom student sessions:
        # { connection_id -> { quiz_id, student_name, current_question_index, score, ... } }
        self.sessions: Dict[str, Dict[str, Any]] = {}

        self._initialize_storage()

    def _initialize_storage(self) -> None:
        """Ensures storage directory and quizzes file exist, seeding initial data if empty."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            if not self.storage_path.exists():
                self._seed_initial_quizzes()
            else:
                self._load_from_disk()
        except Exception as e:
            logger.error(f"[CUSTOM_QUIZ] Storage initialization error: {e}")
            self._seed_initial_quizzes()

    def _seed_initial_quizzes(self) -> None:
        """Seeds initial default teacher quiz so the dashboard is immediately populated."""
        sample_quiz_id = "CN2-8F4K2"
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        sample_quiz = {
            "quiz_id": sample_quiz_id,
            "title": "Computer Networks Unit 2 Test",
            "description": "Comprehensive test on Transport Layer protocols, TCP connection management, reliable byte-stream framing, and congestion control algorithms.",
            "category": "Computer Networks",
            "type": "Unit Test",
            "time_limit_minutes": 15,
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "created_by": "teacher@netquiz.edu",
            "questions": [
                {
                    "id": "q_001",
                    "question": "Which protocol guarantees reliable, connection-oriented and ordered byte-stream delivery at the Transport Layer?",
                    "type": "mcq",
                    "options": {
                        "A": "UDP",
                        "B": "TCP",
                        "C": "ICMP",
                        "D": "IP"
                    },
                    "correct_answer": "B",
                    "explanation": "TCP provides full-duplex, connection-oriented, sequenced, and reliable byte-stream transmission using ACKs and sequence numbers.",
                    "points": 1,
                    "time_limit": 30
                },
                {
                    "id": "q_002",
                    "question": "True or False: UDP performs a three-way handshake (SYN, SYN-ACK, ACK) before transmitting payload packets.",
                    "type": "true_false",
                    "options": {
                        "A": "True",
                        "B": "False"
                    },
                    "correct_answer": "B",
                    "explanation": "False. UDP is connectionless and sends datagrams without initiating a three-way handshake.",
                    "points": 1,
                    "time_limit": 20
                },
                {
                    "id": "q_003",
                    "question": "What is the standard socket option used in TCP servers to reuse local port addresses without waiting for the TIME_WAIT state to expire?",
                    "type": "mcq",
                    "options": {
                        "A": "SO_KEEPALIVE",
                        "B": "SO_BROADCAST",
                        "C": "SO_REUSEADDR",
                        "D": "TCP_NODELAY"
                    },
                    "correct_answer": "C",
                    "explanation": "SO_REUSEADDR permits a server socket to bind immediately to a local address/port still in TIME_WAIT state.",
                    "points": 1,
                    "time_limit": 30
                },
                {
                    "id": "q_004",
                    "question": "In TCP congestion control, which algorithm halves the congestion window (cwnd) or resets ssthresh upon experiencing packet loss?",
                    "type": "mcq",
                    "options": {
                        "A": "Slow Start",
                        "B": "Congestion Avoidance / Fast Recovery",
                        "C": "Bellman-Ford",
                        "D": "Dijkstra Link State"
                    },
                    "correct_answer": "B",
                    "explanation": "Fast Recovery / AIMD handles packet loss by setting ssthresh to cwnd/2 and maintaining higher pipeline utilization.",
                    "points": 1,
                    "time_limit": 30
                },
                {
                    "id": "q_005",
                    "question": "What framing technique is used by the NetQuiz TCP socket server to delimit structured messages across a continuous byte stream?",
                    "type": "mcq",
                    "options": {
                        "A": "Fixed 128-byte padding",
                        "B": "Bit stuffing flag 01111110",
                        "C": "Newline-delimited JSON Lines ('\\n')",
                        "D": "HTTP chunked transfer headers"
                    },
                    "correct_answer": "C",
                    "explanation": "NetQuiz uses newline-delimited JSON framing so client and server can reliably detect message boundaries over TCP byte streams.",
                    "points": 1,
                    "time_limit": 30
                }
            ],
            "participants": [
                {
                    "participant_id": f"cst-{sample_quiz_id}-demo1",
                    "student_name": "Aarav",
                    "joined_at": now,
                    "status": "completed",
                    "score": 5,
                    "total_questions": 5,
                    "points_scored": 5,
                    "total_points": 5,
                    "percentage": 100.0,
                    "time_taken": "02:45",
                    "time_taken_seconds": 165,
                    "current_question": 5,
                    "submitted_at": now
                },
                {
                    "participant_id": f"cst-{sample_quiz_id}-demo2",
                    "student_name": "Ishita",
                    "joined_at": now,
                    "status": "completed",
                    "score": 4,
                    "total_questions": 5,
                    "points_scored": 4,
                    "total_points": 5,
                    "percentage": 80.0,
                    "time_taken": "03:12",
                    "time_taken_seconds": 192,
                    "current_question": 5,
                    "submitted_at": now
                }
            ],
            "leaderboard": [
                {
                    "rank": 1,
                    "student_name": "Aarav",
                    "score": 5,
                    "total_questions": 5,
                    "points_scored": 5,
                    "total_points": 5,
                    "percentage": 100.0,
                    "time_taken": "02:45",
                    "submission_status": "Completed",
                    "submitted_at": now
                },
                {
                    "rank": 2,
                    "student_name": "Ishita",
                    "score": 4,
                    "total_questions": 5,
                    "points_scored": 4,
                    "total_points": 5,
                    "percentage": 80.0,
                    "time_taken": "03:12",
                    "submission_status": "Completed",
                    "submitted_at": now
                }
            ]
        }

        with self.lock:
            self.quizzes = {sample_quiz_id: sample_quiz}
            # Rehydrate sessions index
            for p in sample_quiz["participants"]:
                cid = p["participant_id"]
                self.sessions[cid] = {
                    "quiz_id": sample_quiz_id,
                    "connection_id": cid,
                    "student_name": p["student_name"],
                    "current_question_index": p["current_question"],
                    "score": p["score"],
                    "points_scored": p["points_scored"],
                    "total_points": p["total_points"],
                    "quiz_started": True,
                    "quiz_completed": (p["status"] == "completed"),
                    "start_time": p["joined_at"],
                    "completion_time": p.get("submitted_at"),
                    "time_taken": p["time_taken"],
                    "time_taken_seconds": p["time_taken_seconds"],
                    "answers_history": []
                }
            self._save_to_disk()

    def _load_from_disk(self) -> None:
        """Loads quizzes from disk JSON file."""
        with open(self.storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                self.quizzes = data
            elif isinstance(data, list):
                self.quizzes = {q["quiz_id"]: q for q in data if "quiz_id" in q}
            else:
                self.quizzes = {}

        # Re-index sessions
        self.sessions.clear()
        for q_id, q in self.quizzes.items():
            for p in q.get("participants", []):
                cid = p.get("participant_id")
                if cid:
                    self.sessions[cid] = {
                        "quiz_id": q_id,
                        "connection_id": cid,
                        "student_name": p["student_name"],
                        "current_question_index": p.get("current_question", 0),
                        "score": p.get("score", 0),
                        "points_scored": p.get("points_scored", 0),
                        "total_points": p.get("total_points", len(q.get("questions", []))),
                        "quiz_started": True,
                        "quiz_completed": (p.get("status") == "completed"),
                        "start_time": p.get("joined_at"),
                        "completion_time": p.get("submitted_at"),
                        "time_taken": p.get("time_taken", "00:00"),
                        "time_taken_seconds": p.get("time_taken_seconds", 0),
                        "answers_history": p.get("answers_history", [])
                    }

    def _save_to_disk(self) -> None:
        """Atomic disk persistence."""
        tmp_path = self.storage_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.quizzes, f, indent=2, ensure_ascii=False)
        tmp_path.replace(self.storage_path)

    # ────────────────────────────────────────────────────────────────────────────
    # Teacher Quiz CRUD & Lifecycle
    # ────────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, int]:
        """Calculates dashboard summary metrics."""
        with self.lock:
            total_quizzes = len(self.quizzes)
            active_quizzes = sum(1 for q in self.quizzes.values() if q.get("status") in ["active", "published"])
            total_participants = sum(len(q.get("participants", [])) for q in self.quizzes.values())
            total_questions = sum(len(q.get("questions", [])) for q in self.quizzes.values())
            return {
                "total_quizzes": total_quizzes,
                "active_quizzes": active_quizzes,
                "total_participants": total_participants,
                "total_questions": total_questions
            }

    def get_all_quizzes(self) -> List[Dict[str, Any]]:
        """Returns summary list of all teacher quizzes, sorted newest first."""
        with self.lock:
            result = []
            for q in self.quizzes.values():
                result.append({
                    "quiz_id": q["quiz_id"],
                    "title": q["title"],
                    "description": q.get("description", ""),
                    "category": q.get("category", "Computer Networks"),
                    "type": q.get("type", "Unit Test"),
                    "status": q.get("status", "draft"),
                    "total_questions": len(q.get("questions", [])),
                    "participants_count": len(q.get("participants", [])),
                    "completed_count": len(q.get("leaderboard", [])),
                    "created_at": q.get("created_at", "")
                })
            # Sort newest first
            return sorted(result, key=lambda x: x["created_at"], reverse=True)

    def get_quiz(self, quiz_id: str, for_student: bool = False) -> Optional[Dict[str, Any]]:
        """
        Retrieves a quiz by ID.
        If for_student is True, correct answers and sensitive metadata are NEVER returned!
        """
        with self.lock:
            q = self.quizzes.get(quiz_id)
            if not q:
                return None

            if for_student:
                return {
                    "quiz_id": q["quiz_id"],
                    "title": q["title"],
                    "description": q.get("description", ""),
                    "category": q.get("category", "Computer Networks"),
                    "type": q.get("type", "Unit Test"),
                    "status": q.get("status", "draft"),
                    "total_questions": len(q.get("questions", [])),
                    "time_limit_minutes": q.get("time_limit_minutes"),
                    "created_at": q.get("created_at", "")
                }

            # Return full quiz for teacher
            return {
                "quiz_id": q["quiz_id"],
                "title": q["title"],
                "description": q.get("description", ""),
                "category": q.get("category", "Computer Networks"),
                "type": q.get("type", "Unit Test"),
                "time_limit_minutes": q.get("time_limit_minutes"),
                "status": q.get("status", "draft"),
                "created_at": q.get("created_at", ""),
                "updated_at": q.get("updated_at", ""),
                "created_by": q.get("created_by", "teacher@netquiz.edu"),
                "questions": q.get("questions", []),
                "total_questions": len(q.get("questions", [])),
                "participants_count": len(q.get("participants", [])),
                "completed_count": len(q.get("leaderboard", []))
            }

    def create_quiz(self, data: Dict[str, Any], created_by: str = "teacher@netquiz.edu") -> Dict[str, Any]:
        """Creates a new quiz with a unique ID and persists it."""
        with self.lock:
            existing_ids = set(self.quizzes.keys())
            title = data.get("title", "").strip() or "Untitled Quiz"
            category = data.get("category", "").strip() or "Computer Networks"
            quiz_id = generate_unique_quiz_id(existing_ids, title, category)

            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            raw_questions = data.get("questions", [])
            cleaned_questions = []

            for idx, raw_q in enumerate(raw_questions, start=1):
                qid = raw_q.get("id") or f"q_{idx:03d}"
                cleaned_questions.append({
                    "id": qid,
                    "question": raw_q.get("question", "").strip(),
                    "type": raw_q.get("type", "mcq"),
                    "options": raw_q.get("options", {}),
                    "correct_answer": str(raw_q.get("correct_answer", "A")).strip().upper(),
                    "explanation": raw_q.get("explanation", "").strip(),
                    "points": int(raw_q.get("points", 1)),
                    "time_limit": int(raw_q.get("time_limit", 30))
                })

            quiz_obj = {
                "quiz_id": quiz_id,
                "title": title,
                "description": data.get("description", "").strip(),
                "category": category,
                "type": data.get("type", "Unit Test").strip(),
                "time_limit_minutes": data.get("time_limit_minutes"),
                "status": "draft",
                "created_at": now,
                "updated_at": now,
                "created_by": created_by,
                "questions": cleaned_questions,
                "participants": [],
                "leaderboard": []
            }

            self.quizzes[quiz_id] = quiz_obj
            self._save_to_disk()
            logger.info(f"[CUSTOM_QUIZ] Created quiz '{title}' [{quiz_id}] with {len(cleaned_questions)} questions")
            return self.get_quiz(quiz_id)

    def update_quiz(self, quiz_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates metadata and questions of an existing quiz."""
        with self.lock:
            q = self.quizzes.get(quiz_id)
            if not q:
                return None

            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            q["updated_at"] = now

            if "title" in updates and updates["title"] is not None:
                q["title"] = updates["title"].strip()
            if "description" in updates and updates["description"] is not None:
                q["description"] = updates["description"].strip()
            if "category" in updates and updates["category"] is not None:
                q["category"] = updates["category"].strip()
            if "type" in updates and updates["type"] is not None:
                q["type"] = updates["type"].strip()
            if "time_limit_minutes" in updates:
                q["time_limit_minutes"] = updates["time_limit_minutes"]

            if "questions" in updates and updates["questions"] is not None:
                cleaned_questions = []
                for idx, raw_q in enumerate(updates["questions"], start=1):
                    qid = raw_q.get("id") or f"q_{idx:03d}"
                    cleaned_questions.append({
                        "id": qid,
                        "question": raw_q.get("question", "").strip(),
                        "type": raw_q.get("type", "mcq"),
                        "options": raw_q.get("options", {}),
                        "correct_answer": str(raw_q.get("correct_answer", "A")).strip().upper(),
                        "explanation": raw_q.get("explanation", "").strip(),
                        "points": int(raw_q.get("points", 1)),
                        "time_limit": int(raw_q.get("time_limit", 30))
                    })
                q["questions"] = cleaned_questions

            self._save_to_disk()
            return self.get_quiz(quiz_id)

    def delete_quiz(self, quiz_id: str) -> bool:
        """Deletes a quiz and cleans up its sessions."""
        with self.lock:
            if quiz_id not in self.quizzes:
                return False

            del self.quizzes[quiz_id]
            # Remove associated sessions
            to_del = [cid for cid, s in self.sessions.items() if s.get("quiz_id") == quiz_id]
            for cid in to_del:
                del self.sessions[cid]

            self._save_to_disk()
            return True

    def publish_quiz(self, quiz_id: str) -> Tuple[bool, str]:
        """Validates and publishes a quiz, transitioning it from draft to published."""
        with self.lock:
            q = self.quizzes.get(quiz_id)
            if not q:
                return False, f"Quiz {quiz_id} not found."

            questions = q.get("questions", [])
            if len(questions) == 0:
                return False, "Cannot publish a quiz with no questions. Please add at least one question."

            for idx, q_item in enumerate(questions, start=1):
                if not q_item.get("question", "").strip():
                    return False, f"Question {idx} has empty question text."
                if not q_item.get("correct_answer"):
                    return False, f"Question {idx} does not have a correct answer selected."
                options = q_item.get("options", {})
                if q_item.get("type") == "mcq" and len(options) < 2:
                    return False, f"Multiple choice question {idx} must have at least 2 options."

            q["status"] = "published"
            q["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_to_disk()
            return True, "Quiz published successfully! Share the generated link with students."

    def start_quiz(self, quiz_id: str) -> Tuple[bool, str]:
        """Activates a quiz for live student participation."""
        with self.lock:
            q = self.quizzes.get(quiz_id)
            if not q:
                return False, f"Quiz {quiz_id} not found."
            if len(q.get("questions", [])) == 0:
                return False, "Cannot start a quiz without questions."

            q["status"] = "active"
            q["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_to_disk()
            return True, "Quiz is now ACTIVE. Students can join and participate live."

    def end_quiz(self, quiz_id: str) -> Tuple[bool, str]:
        """Ends a quiz. Disallows new student attempts; preserves existing scores/leaderboard."""
        with self.lock:
            q = self.quizzes.get(quiz_id)
            if not q:
                return False, f"Quiz {quiz_id} not found."

            q["status"] = "ended"
            q["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_to_disk()
            return True, "Quiz has been ended. No further submissions will be accepted."

    # ────────────────────────────────────────────────────────────────────────────
    # Student Participation & Server-Side Scoring
    # ────────────────────────────────────────────────────────────────────────────

    def join_student(self, quiz_id: str, student_name: str) -> Tuple[bool, Dict[str, Any]]:
        """Allows a student to join a specific quiz attempt."""
        clean_name = student_name.strip()
        if not clean_name:
            return False, {"error": "Student name cannot be empty."}

        with self.lock:
            q = self.quizzes.get(quiz_id)
            if not q:
                return False, {"error": f"Quiz '{quiz_id}' was not found. Please verify your quiz link."}

            status = q.get("status", "draft")
            if status == "draft":
                return False, {"error": "This quiz is still a draft and has not been published by the teacher."}
            if status == "ended":
                return False, {"error": "This quiz has ended and is no longer accepting new submissions."}

            questions = q.get("questions", [])
            if len(questions) == 0:
                return False, {"error": "This quiz has no questions available."}

            connection_id = f"cst-{quiz_id}-{uuid.uuid4().hex[:8]}"
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            total_points = sum(q_item.get("points", 1) for q_item in questions)

            session = {
                "quiz_id": quiz_id,
                "connection_id": connection_id,
                "student_name": clean_name,
                "current_question_index": 0,
                "score": 0,
                "points_scored": 0,
                "total_points": total_points,
                "quiz_started": True,
                "quiz_completed": False,
                "start_time": now,
                "start_timestamp": datetime.datetime.now().timestamp(),
                "completion_time": None,
                "time_taken": "00:00",
                "time_taken_seconds": 0,
                "answers_history": []
            }

            self.sessions[connection_id] = session

            # Record in quiz participant list
            participant_record = {
                "participant_id": connection_id,
                "student_name": clean_name,
                "joined_at": now,
                "status": "in_progress",
                "score": 0,
                "total_questions": len(questions),
                "points_scored": 0,
                "total_points": total_points,
                "percentage": 0.0,
                "time_taken": "00:00",
                "time_taken_seconds": 0,
                "current_question": 1
            }
            q.setdefault("participants", []).append(participant_record)
            self._save_to_disk()

            logger.info(f"[CUSTOM_QUIZ] Student '{clean_name}' joined quiz '{q['title']}' [{quiz_id}]")

            return True, {
                "success": True,
                "connection_id": connection_id,
                "student_name": clean_name,
                "quiz_id": quiz_id,
                "quiz_title": q["title"],
                "total_questions": len(questions),
                "time_limit_minutes": q.get("time_limit_minutes"),
                "message": f"Successfully joined '{q['title']}'. Good luck!"
            }

    def get_student_question(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the student's current question for their isolated session.
        CRITICAL: Never exposes correct_answer or explanation to the client!
        """
        with self.lock:
            session = self.sessions.get(connection_id)
            if not session or session["quiz_completed"]:
                return None

            quiz_id = session["quiz_id"]
            q = self.quizzes.get(quiz_id)
            if not q:
                return None

            questions = q.get("questions", [])
            idx = session["current_question_index"]
            if idx >= len(questions):
                return None

            target_q = questions[idx]
            return {
                "id": target_q["id"],
                "question": target_q["question"],
                "type": target_q.get("type", "mcq"),
                "options": target_q.get("options", {}),
                "points": target_q.get("points", 1),
                "time_limit": target_q.get("time_limit", 30),
                "question_number": idx + 1,
                "total_questions": len(questions)
            }

    def submit_student_answer(
        self,
        connection_id: str,
        question_id: str,
        answer: str,
        student_name: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Evaluates a student's answer strictly on the server against the custom quiz questions.
        Updates student's progress and recomputes the quiz-specific leaderboard upon completion.
        """
        with self.lock:
            session = self.sessions.get(connection_id)
            if not session:
                return False, {"error": "Invalid or expired quiz session. Please join again."}

            if student_name and session["student_name"].strip().lower() != student_name.strip().lower():
                return False, {"error": f"Session mismatch: Belongs to '{session['student_name']}'."}

            if session["quiz_completed"]:
                return False, {"error": "Quiz has already been completed."}

            quiz_id = session["quiz_id"]
            q = self.quizzes.get(quiz_id)
            if not q:
                return False, {"error": "Quiz not found."}

            questions = q.get("questions", [])
            idx = session["current_question_index"]
            if idx >= len(questions):
                return False, {"error": "No more questions pending."}

            target_q = questions[idx]
            if target_q["id"] != question_id:
                return False, {
                    "error": f"Invalid question sequence. Expected question ID '{target_q['id']}'."
                }

            # Evaluate answer
            clean_answer = str(answer).strip().upper()
            correct_ans = str(target_q["correct_answer"]).strip().upper()
            is_correct = (clean_answer == correct_ans)
            q_points = target_q.get("points", 1)

            if is_correct:
                session["score"] += 1
                session["points_scored"] += q_points

            answered_number = idx + 1
            session["current_question_index"] += 1

            session["answers_history"].append({
                "question_id": question_id,
                "submitted_answer": clean_answer,
                "correct_answer": correct_ans,
                "is_correct": is_correct,
                "points_earned": q_points if is_correct else 0
            })

            is_completed = (session["current_question_index"] >= len(questions))
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if is_completed:
                session["quiz_completed"] = True
                session["completion_time"] = now
                elapsed_sec = int(datetime.datetime.now().timestamp() - session.get("start_timestamp", 0))
                if elapsed_sec < 0:
                    elapsed_sec = 0
                session["time_taken_seconds"] = elapsed_sec
                mins = elapsed_sec // 60
                secs = elapsed_sec % 60
                session["time_taken"] = f"{mins:02d}:{secs:02d}"

                # Update participant status in quiz
                for p in q.get("participants", []):
                    if p["participant_id"] == connection_id:
                        p["status"] = "completed"
                        p["score"] = session["score"]
                        p["points_scored"] = session["points_scored"]
                        p["percentage"] = round((session["score"] / len(questions)) * 100.0, 1)
                        p["time_taken"] = session["time_taken"]
                        p["time_taken_seconds"] = elapsed_sec
                        p["current_question"] = len(questions)
                        p["submitted_at"] = now
                        break

                # Update quiz-specific leaderboard
                self._update_quiz_leaderboard(quiz_id, session)

            self._save_to_disk()

            return True, {
                "correct": is_correct,
                "submitted_answer": clean_answer,
                "correct_answer": correct_ans,
                "explanation": target_q.get("explanation", ""),
                "current_score": session["score"],
                "points_scored": session["points_scored"],
                "total_points": session["total_points"],
                "question_number": answered_number,
                "total_questions": len(questions),
                "quiz_completed": is_completed
            }

    def _update_quiz_leaderboard(self, quiz_id: str, session: Dict[str, Any]) -> None:
        """Helper to re-rank the quiz-specific leaderboard."""
        q = self.quizzes.get(quiz_id)
        if not q:
            return

        leaderboard = q.setdefault("leaderboard", [])
        total_questions = len(q.get("questions", []))
        pct = round((session["score"] / total_questions) * 100.0, 1) if total_questions > 0 else 0.0

        # Replace or append entry
        entry = {
            "participant_id": session["connection_id"],
            "student_name": session["student_name"],
            "score": session["score"],
            "total_questions": total_questions,
            "points_scored": session["points_scored"],
            "total_points": session["total_points"],
            "percentage": pct,
            "time_taken": session.get("time_taken", "00:00"),
            "time_taken_seconds": session.get("time_taken_seconds", 0),
            "submission_status": "Completed",
            "submitted_at": session.get("completion_time")
        }

        # Filter out old entry if re-submitted
        filtered = [item for item in leaderboard if item.get("participant_id") != session["connection_id"]]
        filtered.append(entry)

        # Sort: highest points/score first, then fastest time
        filtered.sort(
            key=lambda x: (
                x.get("points_scored", 0),
                x.get("score", 0),
                -x.get("time_taken_seconds", 999999)
            ),
            reverse=True
        )

        for rank, item in enumerate(filtered, start=1):
            item["rank"] = rank

        q["leaderboard"] = filtered

    def get_student_summary(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Returns final score summary for an individual student."""
        with self.lock:
            session = self.sessions.get(connection_id)
            if not session or not session.get("quiz_completed"):
                return None

            quiz_id = session["quiz_id"]
            q = self.quizzes.get(quiz_id)
            title = q["title"] if q else "Custom Quiz"
            total_questions = len(q.get("questions", [])) if q else len(session.get("answers_history", []))
            pct = round((session["score"] / total_questions) * 100.0, 1) if total_questions > 0 else 0.0

            return {
                "student_name": session["student_name"],
                "quiz_id": quiz_id,
                "quiz_title": title,
                "score": session["score"],
                "total_questions": total_questions,
                "points_scored": session["points_scored"],
                "total_points": session["total_points"],
                "percentage": pct,
                "time_taken": session.get("time_taken", "00:00"),
                "completion_time": session.get("completion_time")
            }

    def get_quiz_leaderboard(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        """Returns the isolated leaderboard strictly for the requested quiz ID."""
        with self.lock:
            q = self.quizzes.get(quiz_id)
            if not q:
                return None

            return {
                "quiz_id": quiz_id,
                "quiz_title": q["title"],
                "status": q.get("status", "draft"),
                "total_participants": len(q.get("participants", [])),
                "completed_count": len(q.get("leaderboard", [])),
                "leaderboard": q.get("leaderboard", [])
            }

    def get_quiz_participants(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        """Returns live participant progress for teacher monitoring."""
        with self.lock:
            q = self.quizzes.get(quiz_id)
            if not q:
                return None

            return {
                "quiz_id": quiz_id,
                "quiz_title": q["title"],
                "total_participants": len(q.get("participants", [])),
                "completed_count": len(q.get("leaderboard", [])),
                "participants": q.get("participants", [])
            }


# Module singleton instance
custom_quiz_manager_instance = CustomQuizManager()
