"""
Pydantic Schemas for NetQuiz FastAPI Bridge Layer.
Provides typed, validated response models for OpenAPI documentation and client responses.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., example="ok")
    service: str = Field(..., example="NetQuiz Backend")
    version: str = Field(..., example="1.0")


class TCPServerStatusResponse(BaseModel):
    running: bool = Field(..., description="Whether the TCP socket server is actively running")
    host: str = Field(..., example="127.0.0.1")
    port: int = Field(..., example=5000)
    protocol: str = Field(..., example="TCP")
    address_family: str = Field(..., example="IPv4")
    socket_type: str = Field(..., example="SOCK_STREAM")
    active_clients: int = Field(..., description="Current count of connected TCP clients")
    total_connections: int = Field(..., description="Cumulative total TCP connections accepted")
    messages_sent: int = Field(..., description="Total framed JSON messages sent over TCP")
    messages_received: int = Field(..., description="Total framed JSON messages received over TCP")
    questions_sent: int = Field(..., description="Total quiz questions transmitted to clients")
    answers_received: int = Field(..., description="Total candidate answers submitted by clients")
    completed_quizzes: int = Field(..., description="Total completed student quiz sessions")


class ConnectedClientItem(BaseModel):
    connection_id: str = Field(..., example="abc12345")
    student_name: str = Field(..., example="Ishita")
    address: str = Field(..., example="127.0.0.1:50123")
    status: str = Field(..., example="connected")
    connected_at: Optional[str] = None
    score: Optional[int] = None
    current_question: Optional[int] = None
    total_questions: Optional[int] = None
    quiz_completed: Optional[bool] = None
    percentage: Optional[float] = None


class ConnectedClientsResponse(BaseModel):
    count: int = Field(..., description="Number of currently connected TCP clients")
    clients: List[ConnectedClientItem] = Field(..., description="List of active client details")


class LeaderboardEntry(BaseModel):
    rank: int = Field(..., example=1)
    student_name: str = Field(..., example="Riya")
    score: int = Field(..., example=10)
    total_questions: int = Field(..., example=10)
    percentage: float = Field(..., example=100.0)
    completion_time: Optional[str] = None


class LeaderboardResponse(BaseModel):
    leaderboard: List[LeaderboardEntry] = Field(..., description="Leaderboard ranked by highest score")


class QuizInfoResponse(BaseModel):
    total_questions_available: int = Field(..., example=15)
    questions_per_quiz: int = Field(..., example=10)
    topic: str = Field(..., example="Computer Networks")
    question_type: str = Field(..., example="Multiple Choice")


# ────────────────────────────────────────────────────────────────────────────
# Quiz Participation Schemas (Stage 6)
# ────────────────────────────────────────────────────────────────────────────

class JoinQuizRequest(BaseModel):
    student_name: str = Field(..., min_length=1, max_length=50, example="Ishita")


class JoinQuizResponse(BaseModel):
    success: bool
    connection_id: str = Field(..., description="Unique session ID for this quiz attempt")
    student_name: str
    total_questions: int
    message: str


class QuestionOptions(BaseModel):
    A: str
    B: str
    C: str
    D: str


class QuestionResponse(BaseModel):
    question_number: int
    total_questions: int
    question_id: int
    question: str
    options: QuestionOptions


class SubmitAnswerRequest(BaseModel):
    connection_id: str = Field(..., description="Session ID returned by join endpoint")
    question_id: int
    answer: str = Field(..., pattern="^[A-Da-d]$", example="A")
    student_name: Optional[str] = Field(None, description="Optional student name for session ownership validation")


class AnswerResultResponse(BaseModel):
    correct: bool
    submitted_answer: str
    correct_answer: str
    explanation: str
    current_score: int
    question_number: int
    total_questions: int
    quiz_completed: bool


class QuizSummaryResponse(BaseModel):
    student_name: str
    score: int
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    percentage: float
    completion_time: Optional[str] = None
