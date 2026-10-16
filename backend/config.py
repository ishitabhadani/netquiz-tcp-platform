"""
Configuration settings for NetQuiz platform.
Keeps host and port parameters organized and easy to modify.
"""

# FastAPI Web API Server (Bridge between React Frontend and Quiz System)
FASTAPI_HOST = "127.0.0.1"
FASTAPI_PORT = 8000

# Python TCP Socket Server (Direct Computer Networks socket layer - Stage 2)
TCP_SERVER_HOST = "127.0.0.1"
TCP_SERVER_PORT = 5000
