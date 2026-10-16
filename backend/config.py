"""
Configuration settings for NetQuiz platform.
Keeps host, port, and quiz parameters organized and easy to modify.
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent

# FastAPI Web API Server (Bridge between React Frontend and Quiz System)
# Binds to 0.0.0.0 in cloud deployments and reads platform-injected $PORT with fallback to 8000
FASTAPI_HOST = os.getenv("FASTAPI_HOST", "0.0.0.0")
FASTAPI_PORT = int(os.getenv("PORT", os.getenv("FASTAPI_PORT", "8000")))

# Python TCP Socket Server (Direct Computer Networks socket layer)
TCP_SERVER_HOST = os.getenv("TCP_SERVER_HOST", "127.0.0.1")
TCP_SERVER_PORT = int(os.getenv("TCP_SERVER_PORT", "5000"))

# Quiz Configuration (Stage 3)
QUIZ_QUESTION_COUNT = 10
QUESTIONS_FILE_PATH = BASE_DIR / "backend" / "quiz" / "questions.json"

# Persistent Custom Quiz Data Storage
DATA_DIR = BASE_DIR / "backend" / "data"
CUSTOM_QUIZZES_FILE_PATH = DATA_DIR / "quizzes.json"

# Teacher Access Credentials
TEACHER_EMAIL = os.getenv("TEACHER_EMAIL", "teacher@netquiz.edu")
TEACHER_PASSWORD = os.getenv("TEACHER_PASSWORD", "teacher123")
TEACHER_SECRET_KEY = os.getenv("TEACHER_SECRET_KEY", "netquiz-teacher-secret-key-2026")
