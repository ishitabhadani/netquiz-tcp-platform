"""
NetQuiz Server-Side Quiz Manager & Player State Module

Academic Concepts Demonstrated:
1. Server-Side State Machine & Source-of-Truth:
   Quiz evaluation and scoring are performed strictly by the central server.
   Clients transmit candidate answers; the server validates constraints, evaluates
   correctness, maintains player state, and computes scores.
2. Independent Multi-User Concurrency:
   Each connected student has an isolated PlayerQuizState instance keyed by
   connection ID, preventing state collision across concurrent client threads.
3. Thread Safety:
   Shared session registries and leaderboards are guarded with threading.Lock.
"""

import datetime
import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.config import QUESTIONS_FILE_PATH, QUIZ_QUESTION_COUNT

logger = logging.getLogger("NetQuiz.Quiz.Manager")


class PlayerQuizState:
    """
    Encapsulates independent quiz progress and scoring for a single student.
    """
    def __init__(self, connection_id: str, student_name: str, question_ids: List[int]) -> None:
        self.connection_id: str = connection_id
        self.student_name: str = student_name
        self.assigned_question_ids: List[int] = list(question_ids)
        
        self.current_question_index: int = 0
        self.score: int = 0
        self.correct_answers: int = 0
        self.incorrect_answers: int = 0
        
        self.answered_question_ids: List[int] = []
        self.answers_history: List[Dict[str, Any]] = []
        
        self.quiz_started: bool = False
        self.quiz_completed: bool = False
        
        self.start_time: Optional[str] = None
        self.completion_time: Optional[str] = None

    @property
    def total_questions(self) -> int:
        return len(self.assigned_question_ids)

    @property
    def percentage(self) -> float:
        if self.total_questions == 0:
            return 0.0
        return round((self.score / self.total_questions) * 100.0, 1)

    def to_dict(self) -> Dict[str, Any]:
        """Returns a serializable dictionary representation of the player's state."""
        return {
            "connection_id": self.connection_id,
            "student_name": self.student_name,
            "current_question_index": self.current_question_index,
            "total_questions": self.total_questions,
            "score": self.score,
            "correct_answers": self.correct_answers,
            "incorrect_answers": self.incorrect_answers,
            "percentage": self.percentage,
            "quiz_started": self.quiz_started,
            "quiz_completed": self.quiz_completed,
            "start_time": self.start_time,
            "completion_time": self.completion_time
        }


class QuizManager:
    """
    Server-side Quiz Manager that loads questions, tracks multi-user sessions,
    and validates answers strictly on the server.
    """
    def __init__(
        self,
        questions_path: Path = QUESTIONS_FILE_PATH,
        question_count: int = QUIZ_QUESTION_COUNT
    ) -> None:
        self.questions_path: Path = Path(questions_path)
        self.question_count: int = question_count
        
        self.questions: Dict[int, Dict[str, Any]] = {}
        self.ordered_question_ids: List[int] = []
        
        # Player state storage (Key: connection_id -> PlayerQuizState)
        self.sessions: Dict[str, PlayerQuizState] = {}
        # Historical record of completed quizzes for leaderboard persistence
        self.completed_history: List[Dict[str, Any]] = []
        
        self.lock: threading.Lock = threading.Lock()
        self.load_questions()

    def load_questions(self) -> None:
        """
        Loads and validates question bank from JSON file.
        """
        if not self.questions_path.exists():
            raise FileNotFoundError(f"Questions file not found at: {self.questions_path}")

        with open(self.questions_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list) or len(data) == 0:
            raise ValueError("Questions file must contain a non-empty JSON list of questions.")

        with self.lock:
            self.questions.clear()
            self.ordered_question_ids.clear()
            
            for item in data:
                q_id = item.get("id")
                question_text = item.get("question")
                options = item.get("options", {})
                correct_answer = item.get("correct_answer")
                explanation = item.get("explanation", "")

                # Strict validation of question structure
                if not (q_id and question_text and isinstance(options, dict) and correct_answer):
                    raise ValueError(f"Malformed question object in {self.questions_path}: {item}")
                
                if not all(opt in options for opt in ["A", "B", "C", "D"]):
                    raise ValueError(f"Question {q_id} does not have required options A, B, C, D")

                self.questions[q_id] = {
                    "id": q_id,
                    "question": question_text,
                    "options": options,
                    "correct_answer": str(correct_answer).strip().upper(),
                    "explanation": explanation
                }
                self.ordered_question_ids.append(q_id)

        logger.info(f"[QUIZ] Loaded {len(self.questions)} questions from {self.questions_path.name}")

    def start_quiz(self, connection_id: str, student_name: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Initializes a quiz session for a student.
        """
        with self.lock:
            # Deterministic selection: first N configured questions from question bank
            assigned_ids = self.ordered_question_ids[: self.question_count]
            if len(assigned_ids) == 0:
                return False, {"error": "Question bank is empty."}

            state = PlayerQuizState(
                connection_id=connection_id,
                student_name=student_name,
                question_ids=assigned_ids
            )
            state.quiz_started = True
            state.start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.sessions[connection_id] = state

            logger.info(f"[QUIZ] '{student_name}' started quiz session ({len(assigned_ids)} questions) [ID: {connection_id}]")
            
            return True, {
                "type": "quiz_start",
                "student_name": student_name,
                "total_questions": state.total_questions,
                "connection_id": connection_id
            }

    def get_current_question(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the current pending question for the student.
        IMPORTANT: Strips out 'correct_answer' and 'explanation' before delivery!
        """
        with self.lock:
            state = self.sessions.get(connection_id)
            if not state or not state.quiz_started or state.quiz_completed:
                return None

            if state.current_question_index >= state.total_questions:
                return None

            q_id = state.assigned_question_ids[state.current_question_index]
            q_data = self.questions.get(q_id)
            if not q_data:
                return None

            # Safe client payload (correct answer is NOT revealed)
            return {
                "type": "question",
                "question_number": state.current_question_index + 1,
                "total_questions": state.total_questions,
                "question_id": q_data["id"],
                "question": q_data["question"],
                "options": q_data["options"]
            }

    def submit_answer(
        self,
        connection_id: str,
        question_id: int,
        answer: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validates and evaluates an answer submitted by a client.
        Computes score server-side and checks if the quiz is finished.
        """
        with self.lock:
            state = self.sessions.get(connection_id)
            if not state:
                return False, {"type": "error", "message": "No active quiz session found. Please join and start quiz."}

            if not state.quiz_started:
                return False, {"type": "error", "message": "Quiz has not been started yet."}

            if state.quiz_completed:
                return False, {"type": "error", "message": "Quiz has already been completed."}

            # Verify question ordering: question_id must match player's current question
            expected_qid = state.assigned_question_ids[state.current_question_index]
            if question_id != expected_qid:
                return False, {
                    "type": "error",
                    "message": f"Invalid question ID {question_id}. Expected answer for question ID {expected_qid} (Question {state.current_question_index + 1})."
                }

            # Check duplicate submissions
            if question_id in state.answered_question_ids:
                return False, {"type": "error", "message": f"Question {question_id} has already been answered."}

            # Validate answer option
            cleaned_answer = str(answer).strip().upper()
            if cleaned_answer not in ["A", "B", "C", "D"]:
                return False, {
                    "type": "error",
                    "message": f"Invalid answer option '{answer}'. Must be one of 'A', 'B', 'C', or 'D'."
                }

            # Server-side correct answer lookup
            q_data = self.questions[question_id]
            correct_ans = q_data["correct_answer"]
            is_correct = (cleaned_answer == correct_ans)

            # Update student's independent score
            if is_correct:
                state.score += 1
                state.correct_answers += 1
                logger.info(f"[QUIZ] {state.student_name} submitted answer {cleaned_answer} -> CORRECT (Score: {state.score})")
            else:
                state.incorrect_answers += 1
                logger.info(f"[QUIZ] {state.student_name} submitted answer {cleaned_answer} -> INCORRECT (Correct: {correct_ans})")

            state.answered_question_ids.append(question_id)
            state.answers_history.append({
                "question_id": question_id,
                "submitted_answer": cleaned_answer,
                "correct_answer": correct_ans,
                "is_correct": is_correct,
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            })

            answered_number = state.current_question_index + 1
            state.current_question_index += 1

            # Check if all questions have been answered
            quiz_just_completed = (state.current_question_index >= state.total_questions)
            if quiz_just_completed:
                state.quiz_completed = True
                state.completion_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # Record to completed history for leaderboard
                self.completed_history.append(state.to_dict())
                logger.info(
                    f"[QUIZ] {state.student_name} COMPLETED quiz with final score: "
                    f"{state.score}/{state.total_questions} ({state.percentage}%)"
                )

            # Response for the submitted answer
            result_payload = {
                "type": "answer_result",
                "correct": is_correct,
                "submitted_answer": cleaned_answer,
                "correct_answer": correct_ans,
                "explanation": q_data.get("explanation", ""),
                "current_score": state.score,
                "question_number": answered_number,
                "total_questions": state.total_questions,
                "quiz_completed": state.quiz_completed
            }

            return True, result_payload

    def get_quiz_end_summary(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the final quiz summary payload for a completed quiz session.
        """
        with self.lock:
            state = self.sessions.get(connection_id)
            if not state or not state.quiz_completed:
                return None

            return {
                "type": "quiz_end",
                "student_name": state.student_name,
                "score": state.score,
                "total_questions": state.total_questions,
                "correct_answers": state.correct_answers,
                "incorrect_answers": state.incorrect_answers,
                "percentage": state.percentage,
                "completion_time": state.completion_time
            }

    def get_player_state(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Thread-safe getter for an individual player's state dictionary."""
        with self.lock:
            state = self.sessions.get(connection_id)
            return state.to_dict() if state else None

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Returns snapshot of all active/completed sessions."""
        with self.lock:
            return [s.to_dict() for s in self.sessions.values()]

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """
        Generates leaderboard sorted by highest score, then by completion time.
        """
        with self.lock:
            all_records = list(self.completed_history)
            # Add currently active sessions that are completed but not yet in history
            for s in self.sessions.values():
                if s.quiz_completed and not any(r["connection_id"] == s.connection_id for r in all_records):
                    all_records.append(s.to_dict())

            sorted_leaderboard = sorted(
                all_records,
                key=lambda x: (x["score"], -x.get("percentage", 0)),
                reverse=True
            )
            
            # Assign ranks
            for rank, entry in enumerate(sorted_leaderboard, start=1):
                entry["rank"] = rank
                
            return sorted_leaderboard


# Module singleton instance for application-wide sharing
quiz_manager_instance = QuizManager()
