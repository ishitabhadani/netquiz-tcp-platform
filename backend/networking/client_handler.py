"""
NetQuiz Client Handler Module

Academic Concept:
Concurrent Client Handling using Multithreading:
When a central TCP server accepts a connection from a client, it spawns a dedicated
execution thread (ClientHandler) for that client.
This ensures:
1. One client waiting or processing does NOT block other clients.
2. Independent client state (student name, socket descriptor, connection info).
3. Graceful handling of individual client disconnections without affecting the server.
"""

import datetime
import logging
import socket
import threading
import uuid
from typing import Any, Dict, Optional, Tuple

from backend.networking.protocol import MessageFramingBuffer, send_json

logger = logging.getLogger("NetQuiz.TCP.ClientHandler")


class ClientHandler(threading.Thread):
    """
    Dedicated thread handling an individual connected TCP client.
    """
    def __init__(
        self,
        client_socket: socket.socket,
        client_address: Tuple[str, int],
        server: Any
    ) -> None:
        super().__init__(daemon=True)
        self.connection_id: str = uuid.uuid4().hex[:8]
        self.client_socket: socket.socket = client_socket
        self.client_address: Tuple[str, int] = client_address
        self.server: Any = server
        
        self.student_name: Optional[str] = None
        self.connected_at: str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.is_active: bool = True
        self._closed: bool = False
        self.framing_buffer = MessageFramingBuffer()
        
        self.name = f"Thread-Client-{self.connection_id}"

    def run(self) -> None:
        """
        Main execution loop for this client's thread.
        Listens for incoming TCP byte streams, extracts framed JSON messages,
        and dispatches responses.
        """
        logger.info(
            f"[CONNECTION] New client thread started for {self.client_address} (ID: {self.connection_id})"
        )
        
        try:
            while self.is_active and self.server.is_running:
                # recv() blocks until data arrives or connection terminates
                # 4096 bytes is a standard socket buffer size
                try:
                    data = self.client_socket.recv(4096)
                except socket.timeout:
                    continue
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                    logger.info(f"[DISCONNECT] Client {self.connection_id} disconnected unexpectedly (Reset).")
                    break
                except OSError:
                    # Occurs if socket is closed during server shutdown
                    break

                # TCP EOF: If recv() returns 0 bytes, client closed the connection (TCP FIN)
                if not data:
                    logger.info(f"[DISCONNECT] Client {self.connection_id} closed connection (EOF).")
                    break

                # Feed bytes into the message framing buffer
                self.framing_buffer.feed(data)
                
                while self.framing_buffer.has_message():
                    item = self.framing_buffer.get_message()
                    if not item:
                        break
                    message, error = item

                    if error:
                        logger.warning(f"[ERROR] Invalid payload from {self.connection_id}: {error}")
                        self.server.record_message_received()
                        self._safe_send({
                            "type": "error",
                            "message": error,
                            "connection_id": self.connection_id
                        })
                        continue

                    if message is not None:
                        self.server.record_message_received()
                        self._process_message(message)
                        if not self.is_active:
                            break

                if not self.is_active:
                    break

        except Exception as e:
            logger.error(f"[ERROR] Unexpected exception in client {self.connection_id}: {e}", exc_info=True)
        finally:
            self.close()

    def _process_message(self, message: Dict[str, Any]) -> None:
        """
        Processes framed JSON messages according to the NetQuiz protocol.
        """
        msg_type = message.get("type", "").lower()
        
        if msg_type == "join":
            name = str(message.get("student_name", "Anonymous")).strip()
            self.student_name = name if name else "Anonymous"
            logger.info(f"[CLIENT] Student joined: '{self.student_name}' (ID: {self.connection_id})")
            
            # Send join acknowledgement
            self._safe_send({
                "type": "join_ack",
                "success": True,
                "message": "Connected to NetQuiz TCP Server",
                "connection_id": self.connection_id,
                "student_name": self.student_name
            })

        elif msg_type in ["start_quiz", "quiz_start"]:
            logger.info(f"[QUIZ] {self.student_name} requested quiz start.")
            ok, start_data = self.server.quiz_manager.start_quiz(
                self.connection_id,
                self.student_name or "Anonymous"
            )
            if not ok:
                self._safe_send({
                    "type": "error",
                    "message": start_data.get("error", "Unable to start quiz.")
                })
                return

            # 1. Send quiz_start confirmation
            self._safe_send(start_data)

            # 2. Immediately send the first question
            first_question = self.server.quiz_manager.get_current_question(self.connection_id)
            if first_question:
                self.server.record_question_sent()
                logger.info(f"[QUIZ] Sending question 1 to {self.student_name}")
                self._safe_send(first_question)

        elif msg_type == "answer":
            raw_qid = message.get("question_id")
            raw_ans = message.get("answer")

            if raw_qid is None or raw_ans is None:
                self._safe_send({
                    "type": "error",
                    "message": "Missing 'question_id' or 'answer' in answer submission."
                })
                return

            try:
                question_id = int(raw_qid)
            except (ValueError, TypeError):
                self._safe_send({
                    "type": "error",
                    "message": f"Invalid question_id format: {raw_qid}"
                })
                return

            self.server.record_answer_received()
            logger.info(f"[QUIZ] {self.student_name} submitted answer '{raw_ans}' for question ID {question_id}")

            # Validate and score strictly on the server
            ok, result = self.server.quiz_manager.submit_answer(
                self.connection_id,
                question_id,
                str(raw_ans)
            )

            if not ok:
                self._safe_send(result)
                return

            # 1. Send evaluation result for the current answer
            self._safe_send(result)

            # 2. Check if this answer completed the quiz
            if result.get("quiz_completed"):
                self.server.record_quiz_completed()
                end_summary = self.server.quiz_manager.get_quiz_end_summary(self.connection_id)
                if end_summary:
                    logger.info(
                        f"[QUIZ] Sending final summary to {self.student_name}: "
                        f"{end_summary.get('score')}/{end_summary.get('total_questions')}"
                    )
                    self._safe_send(end_summary)
            else:
                # 3. Deliver the next question
                next_question = self.server.quiz_manager.get_current_question(self.connection_id)
                if next_question:
                    self.server.record_question_sent()
                    logger.info(f"[QUIZ] Sending question {next_question['question_number']} to {self.student_name}")
                    self._safe_send(next_question)
            
        elif msg_type == "ping":
            # Diagnostic ping/pong message
            self._safe_send({
                "type": "pong",
                "connection_id": self.connection_id
            })
            
        elif msg_type == "disconnect":
            logger.info(f"[CLIENT] Client {self.connection_id} requested graceful disconnect.")
            self._safe_send({
                "type": "disconnect_ack",
                "message": "Goodbye"
            })
            self.is_active = False
            
        else:
            logger.warning(f"[CLIENT] Unknown message type '{msg_type}' from {self.connection_id}")
            self._safe_send({
                "type": "error",
                "message": f"Unknown message type '{msg_type}'",
                "connection_id": self.connection_id
            })

    def _safe_send(self, payload: Dict[str, Any]) -> bool:
        """
        Safely sends a JSON payload to the client over TCP.
        Returns True if successful, False if socket error occurred.
        """
        if self._closed:
            return False
        try:
            send_json(self.client_socket, payload)
            self.server.record_message_sent()
            return True
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            logger.warning(f"[SEND ERROR] Could not send to {self.connection_id}: {e}")
            self.is_active = False
            return False

    def close(self) -> None:
        """
        Closes the client socket connection gracefully and informs the server.
        """
        if self._closed:
            return
        self._closed = True
        self.is_active = False
        try:
            self.client_socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.client_socket.close()
        except OSError:
            pass

        # Unregister from the server's active clients registry
        self.server.unregister_client(self.connection_id)
        logger.info(f"[DISCONNECT] Cleaned up resources for client {self.connection_id} ({self.student_name})")

    def get_info(self) -> Dict[str, Any]:
        """
        Returns serializable state information for monitoring and dashboards.
        Includes live quiz progress if a quiz session has been initiated.
        """
        base_info = {
            "connection_id": self.connection_id,
            "student_name": self.student_name or "Joining...",
            "ip": self.client_address[0],
            "port": self.client_address[1],
            "connected_at": self.connected_at,
            "status": "connected" if self.is_active else "disconnected"
        }

        # Attach quiz state if active
        if hasattr(self.server, "quiz_manager"):
            quiz_state = self.server.quiz_manager.get_player_state(self.connection_id)
            if quiz_state:
                base_info.update({
                    "score": quiz_state["score"],
                    "current_question": quiz_state["current_question_index"] + (0 if quiz_state["quiz_completed"] else 1),
                    "total_questions": quiz_state["total_questions"],
                    "quiz_completed": quiz_state["quiz_completed"],
                    "percentage": quiz_state["percentage"]
                })

        return base_info
