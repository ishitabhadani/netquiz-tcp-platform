"""
Teacher and Custom Quiz REST API Route Handlers.
Implements:
1. Teacher Authentication (login, session validation)
2. Quiz Management CRUD (create, update, delete, publish, start, end)
3. Quiz-Specific Student Participation (join, get question, submit answer, summary)
4. Quiz-Specific Leaderboards and Live Participation Monitoring
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.api.teacher_auth import authenticate_teacher, require_teacher
from backend.models.schemas import (
    CustomAnswerResultResponse,
    CustomQuizJoinRequest,
    CustomQuizJoinResponse,
    CustomQuizLeaderboardResponse,
    CustomQuizSummaryResponse,
    CustomSubmitAnswerRequest,
    PublicQuizDetailResponse,
    QuestionItemStudent,
    QuizCreateRequest,
    QuizDetailTeacherResponse,
    QuizParticipantsResponse,
    QuizSummaryCard,
    QuizUpdateRequest,
    TeacherLoginRequest,
    TeacherLoginResponse,
    TeacherStatsResponse,
)
from backend.networking.tcp_server import tcp_server_instance
from backend.quiz.custom_quiz_manager import custom_quiz_manager_instance

router = APIRouter()


# ────────────────────────────────────────────────────────────────────────────
# 1. Teacher Authentication Endpoints
# ────────────────────────────────────────────────────────────────────────────

@router.post(
    "/teacher/login",
    response_model=TeacherLoginResponse,
    summary="Teacher Login",
    description="Authenticates the teacher with email and password, issuing a bearer session token."
)
def teacher_login(body: TeacherLoginRequest) -> TeacherLoginResponse:
    auth_result = authenticate_teacher(body.email, body.password)
    if not auth_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid teacher email or password. Default demo credentials: teacher@netquiz.edu / teacher123"
        )
    return TeacherLoginResponse(
        success=True,
        token=auth_result["token"],
        access_token=auth_result["token"],
        teacher=auth_result["teacher"],
        message="Teacher authenticated successfully."
    )


@router.get(
    "/teacher/me",
    summary="Verify Teacher Session",
    description="Validates current teacher session token and returns profile."
)
def get_teacher_profile(teacher: Dict[str, Any] = Depends(require_teacher)) -> Dict[str, Any]:
    return {
        "authenticated": True,
        "teacher": {
            "email": teacher["email"],
            "name": teacher["name"],
            "role": teacher["role"]
        }
    }


@router.get(
    "/teacher/stats",
    response_model=TeacherStatsResponse,
    summary="Teacher Dashboard Summary Statistics",
    description="Returns aggregate counts: total quizzes, active quizzes, total participants, total questions."
)
def get_teacher_stats(_teacher: Dict[str, Any] = Depends(require_teacher)) -> TeacherStatsResponse:
    stats = custom_quiz_manager_instance.get_stats()
    return TeacherStatsResponse(**stats)


# ────────────────────────────────────────────────────────────────────────────
# 2. Teacher Quiz CRUD & Lifecycle Endpoints
# ────────────────────────────────────────────────────────────────────────────

@router.get(
    "/teacher/quizzes",
    response_model=List[QuizSummaryCard],
    summary="List All Teacher Quizzes",
    description="Returns all custom quizzes created by the teacher, sorted by newest first."
)
def list_teacher_quizzes(_teacher: Dict[str, Any] = Depends(require_teacher)) -> List[QuizSummaryCard]:
    raw_list = custom_quiz_manager_instance.get_all_quizzes()
    return [QuizSummaryCard(**item) for item in raw_list]


@router.post(
    "/teacher/quizzes",
    response_model=QuizDetailTeacherResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Quiz",
    description="Creates a new custom quiz with questions, generating a unique Quiz ID."
)
def create_quiz(
    body: QuizCreateRequest,
    teacher: Dict[str, Any] = Depends(require_teacher)
) -> QuizDetailTeacherResponse:
    try:
        data = body.model_dump()
        quiz = custom_quiz_manager_instance.create_quiz(data, created_by=teacher["email"])
        return QuizDetailTeacherResponse(**quiz)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create quiz: {str(e)}"
        )


@router.get(
    "/teacher/quizzes/{quiz_id}",
    response_model=QuizDetailTeacherResponse,
    summary="Get Full Quiz Details (Teacher)",
    description="Returns complete quiz details including question correct answers and configuration."
)
def get_quiz_teacher(
    quiz_id: str,
    _teacher: Dict[str, Any] = Depends(require_teacher)
) -> QuizDetailTeacherResponse:
    quiz = custom_quiz_manager_instance.get_quiz(quiz_id, for_student=False)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz '{quiz_id}' not found."
        )
    return QuizDetailTeacherResponse(**quiz)


@router.put(
    "/teacher/quizzes/{quiz_id}",
    response_model=QuizDetailTeacherResponse,
    summary="Update Quiz",
    description="Updates quiz metadata and questions."
)
def update_quiz(
    quiz_id: str,
    body: QuizUpdateRequest,
    _teacher: Dict[str, Any] = Depends(require_teacher)
) -> QuizDetailTeacherResponse:
    updates = body.model_dump(exclude_unset=True)
    updated = custom_quiz_manager_instance.update_quiz(quiz_id, updates)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz '{quiz_id}' not found."
        )
    return QuizDetailTeacherResponse(**updated)


@router.delete(
    "/teacher/quizzes/{quiz_id}",
    summary="Delete Quiz",
    description="Removes a quiz and cleans up its session records."
)
def delete_quiz(
    quiz_id: str,
    _teacher: Dict[str, Any] = Depends(require_teacher)
) -> Dict[str, Any]:
    success = custom_quiz_manager_instance.delete_quiz(quiz_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz '{quiz_id}' not found."
        )
    return {"success": True, "message": f"Quiz '{quiz_id}' was deleted successfully."}


@router.post(
    "/teacher/quizzes/{quiz_id}/publish",
    summary="Publish Quiz",
    description="Transitions a quiz from Draft to Published, generating the shareable link."
)
def publish_quiz(
    quiz_id: str,
    _teacher: Dict[str, Any] = Depends(require_teacher)
) -> Dict[str, Any]:
    success, msg = custom_quiz_manager_instance.publish_quiz(quiz_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"success": True, "message": msg, "status": "published"}


@router.post(
    "/teacher/quizzes/{quiz_id}/start",
    summary="Start / Activate Quiz",
    description="Transitions a quiz to Active status so students can participate live."
)
def start_quiz(
    quiz_id: str,
    _teacher: Dict[str, Any] = Depends(require_teacher)
) -> Dict[str, Any]:
    success, msg = custom_quiz_manager_instance.start_quiz(quiz_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"success": True, "message": msg, "status": "active"}


@router.post(
    "/teacher/quizzes/{quiz_id}/end",
    summary="End Quiz",
    description="Ends the quiz. Closes new attempts while keeping submissions and leaderboards intact."
)
def end_quiz(
    quiz_id: str,
    _teacher: Dict[str, Any] = Depends(require_teacher)
) -> Dict[str, Any]:
    success, msg = custom_quiz_manager_instance.end_quiz(quiz_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"success": True, "message": msg, "status": "ended"}


@router.get(
    "/teacher/quizzes/{quiz_id}/leaderboard",
    response_model=CustomQuizLeaderboardResponse,
    summary="Teacher Quiz Leaderboard",
    description="Returns the full server-evaluated leaderboard strictly for the specified quiz."
)
def get_teacher_quiz_leaderboard(
    quiz_id: str,
    _teacher: Dict[str, Any] = Depends(require_teacher)
) -> CustomQuizLeaderboardResponse:
    data = custom_quiz_manager_instance.get_quiz_leaderboard(quiz_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Quiz '{quiz_id}' not found.")
    return CustomQuizLeaderboardResponse(**data)


@router.get(
    "/teacher/quizzes/{quiz_id}/participants",
    response_model=QuizParticipantsResponse,
    summary="Live Participant Tracking",
    description="Returns real-time progress for all students connected to this quiz."
)
def get_quiz_participants(
    quiz_id: str,
    _teacher: Dict[str, Any] = Depends(require_teacher)
) -> QuizParticipantsResponse:
    data = custom_quiz_manager_instance.get_quiz_participants(quiz_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Quiz '{quiz_id}' not found.")
    return QuizParticipantsResponse(**data)


# ────────────────────────────────────────────────────────────────────────────
# 3. Student-Facing Custom Quiz Endpoints
# ────────────────────────────────────────────────────────────────────────────

@router.get(
    "/quizzes/{quiz_id}",
    response_model=PublicQuizDetailResponse,
    summary="Get Public Quiz Information",
    description="Returns public quiz title, description, and status. NEVER returns questions or correct answers!"
)
def get_public_quiz(quiz_id: str) -> PublicQuizDetailResponse:
    quiz = custom_quiz_manager_instance.get_quiz(quiz_id, for_student=True)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz '{quiz_id}' not found. Please check your quiz link."
        )
    return PublicQuizDetailResponse(**quiz)


@router.post(
    "/quizzes/{quiz_id}/join",
    response_model=CustomQuizJoinResponse,
    summary="Student Joins Specific Quiz",
    description="Registers a student session for a specific quiz ID."
)
def student_join_quiz(quiz_id: str, body: CustomQuizJoinRequest) -> CustomQuizJoinResponse:
    success, res = custom_quiz_manager_instance.join_student(quiz_id, body.student_name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res.get("error", "Unable to join quiz.")
        )
    # Track metrics in TCP server
    tcp_server_instance.increment_metric("total_connections")
    tcp_server_instance.increment_metric("messages_received")
    tcp_server_instance.increment_metric("messages_sent")
    return CustomQuizJoinResponse(**res)


@router.get(
    "/quizzes/{quiz_id}/question",
    response_model=QuestionItemStudent,
    summary="Get Student Current Question",
    description="Retrieves the current unanswered question for this quiz attempt. Correct answers are stripped!"
)
def get_student_quiz_question(
    quiz_id: str,
    connection_id: str = Query(..., description="Student connection ID returned by join")
) -> QuestionItemStudent:
    q_data = custom_quiz_manager_instance.get_student_question(connection_id)
    if not q_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active question available for this session. Quiz may be completed."
        )
    tcp_server_instance.increment_metric("questions_sent")
    tcp_server_instance.increment_metric("messages_received")
    tcp_server_instance.increment_metric("messages_sent")
    return QuestionItemStudent(**q_data)


@router.post(
    "/quizzes/{quiz_id}/answer",
    response_model=CustomAnswerResultResponse,
    summary="Submit Student Answer",
    description="Submits an answer evaluated strictly server-side against this quiz's question bank."
)
def submit_student_quiz_answer(
    quiz_id: str,
    body: CustomSubmitAnswerRequest
) -> CustomAnswerResultResponse:
    success, res = custom_quiz_manager_instance.submit_student_answer(
        connection_id=body.connection_id,
        question_id=body.question_id,
        answer=body.answer,
        student_name=body.student_name
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res.get("error", "Failed to submit answer.")
        )
    tcp_server_instance.increment_metric("answers_received")
    tcp_server_instance.increment_metric("messages_received")
    tcp_server_instance.increment_metric("messages_sent")
    if res.get("quiz_completed"):
        tcp_server_instance.increment_metric("completed_quizzes")

    return CustomAnswerResultResponse(**res)


@router.post(
    "/quizzes/{quiz_id}/submit",
    response_model=CustomAnswerResultResponse,
    summary="Submit Student Answer (Alias)",
    description="Alias for /quizzes/{quiz_id}/answer."
)
def submit_student_quiz_answer_alias(
    quiz_id: str,
    body: CustomSubmitAnswerRequest
) -> CustomAnswerResultResponse:
    return submit_student_quiz_answer(quiz_id, body)


@router.get(
    "/quizzes/{quiz_id}/summary",
    response_model=CustomQuizSummaryResponse,
    summary="Student Quiz Summary",
    description="Returns final score summary for a completed quiz attempt."
)
def get_student_quiz_summary(
    quiz_id: str,
    connection_id: str = Query(...)
) -> CustomQuizSummaryResponse:
    summary = custom_quiz_manager_instance.get_student_summary(connection_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz summary not available. Quiz may not be finished."
        )
    tcp_server_instance.increment_metric("messages_received")
    tcp_server_instance.increment_metric("messages_sent")
    return CustomQuizSummaryResponse(**summary)


@router.get(
    "/quizzes/{quiz_id}/leaderboard",
    response_model=CustomQuizLeaderboardResponse,
    summary="Public Quiz Leaderboard",
    description="Returns the public leaderboard strictly for this quiz ID."
)
def get_public_quiz_leaderboard(quiz_id: str) -> CustomQuizLeaderboardResponse:
    data = custom_quiz_manager_instance.get_quiz_leaderboard(quiz_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Quiz '{quiz_id}' not found.")
    return CustomQuizLeaderboardResponse(**data)
