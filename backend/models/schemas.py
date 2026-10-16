"""
Pydantic Schemas for NetQuiz FastAPI Bridge Layer.
Provides typed, validated response models for OpenAPI documentation and client responses.
"""

from typing import Any, Dict, List, Optional
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


# ────────────────────────────────────────────────────────────────────────────
# Teacher Authentication & Management Schemas
# ────────────────────────────────────────────────────────────────────────────

class TeacherLoginRequest(BaseModel):
    email: str = Field(..., example="teacher@netquiz.edu")
    password: str = Field(..., min_length=1, example="teacher123")


class TeacherLoginResponse(BaseModel):
    success: bool
    token: str
    teacher: Dict[str, Any]
    message: str


class TeacherStatsResponse(BaseModel):
    total_quizzes: int
    active_quizzes: int
    total_participants: int
    total_questions: int


class QuestionItem(BaseModel):
    id: str = Field(..., example="q_001")
    question: str = Field(..., min_length=1)
    type: str = Field(default="mcq", example="mcq")  # mcq or true_false
    options: Dict[str, str] = Field(default_factory=dict)
    correct_answer: str = Field(..., example="C")
    explanation: Optional[str] = ""
    points: int = Field(default=1, ge=1)
    time_limit: int = Field(default=30, ge=5)  # in seconds


class QuestionItemStudent(BaseModel):
    """Client-safe question payload delivered to students (correct answer stripped)."""
    id: str
    question: str
    type: str
    options: Dict[str, str]
    points: int
    time_limit: int
    question_number: int
    total_questions: int


class QuizCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120, example="Computer Networks Unit 2 Test")
    description: Optional[str] = Field(default="", max_length=1000)
    category: Optional[str] = Field(default="Computer Networks", max_length=100)
    type: Optional[str] = Field(default="Unit Test", max_length=50)
    time_limit_minutes: Optional[int] = Field(default=None, ge=1)
    questions: List[QuestionItem] = Field(default_factory=list)


class QuizUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    time_limit_minutes: Optional[int] = None
    questions: Optional[List[QuestionItem]] = None


class QuizSummaryCard(BaseModel):
    quiz_id: str
    title: str
    description: str
    category: str
    type: str
    status: str  # draft, published, active, ended
    total_questions: int
    participants_count: int
    completed_count: int
    created_at: str


class QuizDetailTeacherResponse(BaseModel):
    quiz_id: str
    title: str
    description: str
    category: str
    type: str
    time_limit_minutes: Optional[int] = None
    status: str
    created_at: str
    updated_at: str
    created_by: str
    questions: List[QuestionItem]
    total_questions: int
    participants_count: int
    completed_count: int


class PublicQuizDetailResponse(BaseModel):
    quiz_id: str
    title: str
    description: str
    category: str
    type: str
    status: str
    total_questions: int
    time_limit_minutes: Optional[int] = None
    created_at: str


class CustomQuizJoinRequest(BaseModel):
    student_name: str = Field(..., min_length=1, max_length=50, example="Ishita")


class CustomQuizJoinResponse(BaseModel):
    success: bool
    connection_id: str
    student_name: str
    quiz_id: str
    quiz_title: str
    total_questions: int
    time_limit_minutes: Optional[int] = None
    message: str


class CustomSubmitAnswerRequest(BaseModel):
    connection_id: str = Field(..., description="Unique student session ID")
    question_id: str = Field(..., description="Target question ID being answered")
    answer: str = Field(..., min_length=1, max_length=10, example="A")
    student_name: Optional[str] = Field(None, description="Optional student name verification")


class CustomAnswerResultResponse(BaseModel):
    correct: bool
    submitted_answer: str
    correct_answer: str
    explanation: str
    current_score: int
    points_scored: int
    total_points: int
    question_number: int
    total_questions: int
    quiz_completed: bool


class CustomQuizSummaryResponse(BaseModel):
    student_name: str
    quiz_id: str
    quiz_title: str
    score: int
    total_questions: int
    points_scored: int
    total_points: int
    percentage: float
    time_taken: str
    completion_time: Optional[str] = None


class QuizLeaderboardItem(BaseModel):
    rank: int
    student_name: str
    score: int
    total_questions: int
    points_scored: int
    total_points: int
    percentage: float
    time_taken: str
    submission_status: str
    submitted_at: Optional[str] = None


class CustomQuizLeaderboardResponse(BaseModel):
    quiz_id: str
    quiz_title: str
    status: str
    total_participants: int
    completed_count: int
    leaderboard: List[QuizLeaderboardItem]


class ParticipantItem(BaseModel):
    participant_id: str
    student_name: str
    joined_at: str
    status: str
    score: int
    total_questions: int
    percentage: float
    time_taken: str
    current_question: int


class QuizParticipantsResponse(BaseModel):
    quiz_id: str
    quiz_title: str
    total_participants: int
    completed_count: int
    participants: List[ParticipantItem]

