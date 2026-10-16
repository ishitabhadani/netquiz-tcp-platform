"""
FastAPI Route Handlers for NetQuiz Application Layer.

Academic Concept:
FastAPI serves as an HTTP REST bridge between the React frontend and the
underlying Python TCP Server / QuizManager.
It queries and exposes:
1. TCP Server Network Status (port 5000, connections, packet counts)
2. Connected Clients Registry (isolated client states)
3. Quiz Configuration & Question Bank Metrics
4. Real-Time Leaderboard evaluated strictly server-side
"""

import uuid
from fastapi import APIRouter, HTTPException, status
from backend.models.schemas import (
    AnswerResultResponse,
    ConnectedClientItem,
    ConnectedClientsResponse,
    HealthResponse,
    JoinQuizRequest,
    JoinQuizResponse,
    LeaderboardEntry,
    LeaderboardResponse,
    QuizInfoResponse,
    QuestionResponse,
    QuizSummaryResponse,
    SubmitAnswerRequest,
    TCPServerStatusResponse,
)
from backend.networking.tcp_server import tcp_server_instance
from backend.quiz.quiz_manager import quiz_manager_instance

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Backend Health Check",
    description="Returns service availability and version information for the FastAPI application layer."
)
def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="NetQuiz Backend",
        version="1.0"
    )


@router.get(
    "/server/status",
    response_model=TCPServerStatusResponse,
    summary="TCP Socket Server Metrics & Status",
    description="Exposes live status and networking metrics directly from the Python TCP socket layer (port 5000)."
)
def get_tcp_server_status() -> TCPServerStatusResponse:
    try:
        raw_status = tcp_server_instance.get_status()
        return TCPServerStatusResponse(
            running=raw_status["is_running"],
            host=raw_status["host"],
            port=raw_status["port"],
            protocol=raw_status["protocol"],
            address_family="IPv4",
            socket_type=raw_status["socket_type"],
            active_clients=raw_status["active_clients"],
            total_connections=raw_status["total_connections"],
            messages_sent=raw_status["messages_sent"],
            messages_received=raw_status["messages_received"],
            questions_sent=raw_status.get("questions_sent", 0),
            answers_received=raw_status.get("answers_received", 0),
            completed_quizzes=raw_status.get("completed_quizzes", 0)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query TCP server status: {str(e)}"
        )


@router.get(
    "/server/clients",
    response_model=ConnectedClientsResponse,
    summary="List Connected TCP Clients",
    description="Returns the active client registry from the TCP server, including IP, ephemeral port, student name, and quiz status."
)
def get_connected_clients() -> ConnectedClientsResponse:
    try:
        raw_status = tcp_server_instance.get_status()
        client_list = []
        for c in raw_status.get("clients", []):
            client_list.append(
                ConnectedClientItem(
                    connection_id=c["connection_id"],
                    student_name=c["student_name"],
                    address=f"{c['ip']}:{c['port']}",
                    status=c["status"],
                    connected_at=c.get("connected_at"),
                    score=c.get("score"),
                    current_question=c.get("current_question"),
                    total_questions=c.get("total_questions"),
                    quiz_completed=c.get("quiz_completed"),
                    percentage=c.get("percentage")
                )
            )
        return ConnectedClientsResponse(
            count=len(client_list),
            clients=client_list
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query connected clients: {str(e)}"
        )


@router.get(
    "/quiz/info",
    response_model=QuizInfoResponse,
    summary="Quiz Configuration & Metadata",
    description="Returns total questions available in the question bank, questions configured per quiz, and topic details."
)
def get_quiz_info() -> QuizInfoResponse:
    try:
        return QuizInfoResponse(
            total_questions_available=len(quiz_manager_instance.questions),
            questions_per_quiz=quiz_manager_instance.question_count,
            topic="Computer Networks",
            question_type="Multiple Choice"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve quiz metadata: {str(e)}"
        )


@router.get(
    "/quiz/leaderboard",
    response_model=LeaderboardResponse,
    summary="Live Server Leaderboard",
    description="Returns completed student quiz results ranked by score (descending) as evaluated by the QuizManager."
)
def get_quiz_leaderboard() -> LeaderboardResponse:
    try:
        raw_leaderboard = quiz_manager_instance.get_leaderboard()
        entries = []
        for item in raw_leaderboard:
            entries.append(
                LeaderboardEntry(
                    rank=item.get("rank", 1),
                    student_name=item["student_name"],
                    score=item["score"],
                    total_questions=item["total_questions"],
                    percentage=item["percentage"],
                    completion_time=item.get("completion_time")
                )
            )
        return LeaderboardResponse(leaderboard=entries)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve leaderboard: {str(e)}"
        )


# ────────────────────────────────────────────────────────────────────────────
# Stage 6: Quiz Participation Endpoints
# These allow the React frontend to participate in the server-side quiz.
# Architecture: React → FastAPI → QuizManager (in-memory, backed by TCP server state)
# ────────────────────────────────────────────────────────────────────────────

@router.post(
    "/quiz/join",
    response_model=JoinQuizResponse,
    summary="Join Quiz Session",
    description=(
        "Creates an isolated server-side quiz session for the student. "
        "Returns a unique connection_id that must be passed with all subsequent quiz API calls."
    )
)
def join_quiz(body: JoinQuizRequest) -> JoinQuizResponse:
    try:
        # Generate a unique session identifier for this browser-side participant.
        # (TCP clients get connection IDs from socket file descriptors; browser clients get UUIDs)
        connection_id = f"web-{uuid.uuid4().hex[:12]}"
        success, result = quiz_manager_instance.start_quiz(
            connection_id=connection_id,
            student_name=body.student_name.strip()
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to start quiz session.")
            )
        # Track this as a web client in TCP server metrics
        tcp_server_instance.increment_metric("total_connections")
        return JoinQuizResponse(
            success=True,
            connection_id=connection_id,
            student_name=body.student_name.strip(),
            total_questions=result["total_questions"],
            message=f"Quiz session started for {body.student_name.strip()}. Good luck!"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to join quiz: {str(e)}"
        )


@router.get(
    "/quiz/question",
    response_model=QuestionResponse,
    summary="Get Current Quiz Question",
    description=(
        "Retrieves the current unanswered question for a quiz session. "
        "The correct answer is NEVER included in the response (server-side secret). "
        "Pass the connection_id returned by /quiz/join."
    )
)
def get_current_question(connection_id: str) -> QuestionResponse:
    try:
        question = quiz_manager_instance.get_current_question(connection_id)
        if question is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active question found. Session may not exist, quiz may be complete, or connection_id is invalid."
            )
        # Track questions sent metric
        tcp_server_instance.increment_metric("questions_sent")
        return QuestionResponse(
            question_number=question["question_number"],
            total_questions=question["total_questions"],
            question_id=question["question_id"],
            question=question["question"],
            options=question["options"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch question: {str(e)}"
        )


@router.post(
    "/quiz/answer",
    response_model=AnswerResultResponse,
    summary="Submit Quiz Answer",
    description=(
        "Submits a candidate answer to the server for evaluation. "
        "The server validates correctness, updates the student’s score, and returns the result. "
        "This is the core server-side evaluation step."
    )
)
def submit_answer(body: SubmitAnswerRequest) -> AnswerResultResponse:
    try:
        success, result = quiz_manager_instance.submit_answer(
            connection_id=body.connection_id,
            question_id=body.question_id,
            answer=body.answer.upper()
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to submit answer.")
            )
        # Track answers received metric
        tcp_server_instance.increment_metric("answers_received")
        if result.get("quiz_completed"):
            tcp_server_instance.increment_metric("completed_quizzes")
        return AnswerResultResponse(
            correct=result["correct"],
            submitted_answer=result["submitted_answer"],
            correct_answer=result["correct_answer"],
            explanation=result.get("explanation", ""),
            current_score=result["current_score"],
            question_number=result["question_number"],
            total_questions=result["total_questions"],
            quiz_completed=result["quiz_completed"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit answer: {str(e)}"
        )


@router.get(
    "/quiz/summary",
    response_model=QuizSummaryResponse,
    summary="Get Quiz Final Summary",
    description="Returns the final score summary for a completed quiz session."
)
def get_quiz_summary(connection_id: str) -> QuizSummaryResponse:
    try:
        summary = quiz_manager_instance.get_quiz_end_summary(connection_id)
        if summary is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz summary not available. Session not found or quiz not yet completed."
            )
        return QuizSummaryResponse(
            student_name=summary["student_name"],
            score=summary["score"],
            total_questions=summary["total_questions"],
            correct_answers=summary["correct_answers"],
            incorrect_answers=summary["incorrect_answers"],
            percentage=summary["percentage"],
            completion_time=summary.get("completion_time")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve quiz summary: {str(e)}"
        )
