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

from fastapi import APIRouter, HTTPException, status
from backend.models.schemas import (
    ConnectedClientItem,
    ConnectedClientsResponse,
    HealthResponse,
    LeaderboardEntry,
    LeaderboardResponse,
    QuizInfoResponse,
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
