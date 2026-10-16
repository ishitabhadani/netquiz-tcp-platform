"""
NetQuiz TCP Socket Server Module

Academic Concepts Demonstrated:
1. socket.AF_INET: Address Family for IPv4 (32-bit internet addresses).
2. socket.SOCK_STREAM: Socket type for connection-oriented TCP byte stream.
3. SO_REUSEADDR: Socket option to reuse local address/port immediately without TIME_WAIT delays.
4. bind(): Associates socket with local IPv4 address and port number.
5. listen(): Marks socket as passive, ready to accept incoming connection requests.
6. accept(): Performs TCP 3-way handshake and returns (new_socket, client_address).
7. Concurrent Client Handling: Dedicated thread spawned for each client connection.
"""

import logging
import socket
import sys
import threading
import time
from typing import Any, Dict, List, Optional

from backend.config import TCP_SERVER_HOST, TCP_SERVER_PORT
from backend.networking.client_handler import ClientHandler

# Configure structured logging for console demonstration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("NetQuiz.TCP.Server")


class TCPServer:
    """
    Multithreaded TCP Server for NetQuiz Platform.
    """
    def __init__(
        self,
        host: str = TCP_SERVER_HOST,
        port: int = TCP_SERVER_PORT,
        quiz_manager: Optional[Any] = None
    ) -> None:
        self.host: str = host
        self.port: int = port
        self.server_socket: Optional[socket.socket] = None
        
        # Concurrency & Client Management
        self.is_running: bool = False
        self.clients: Dict[str, ClientHandler] = {}
        self.lock: threading.Lock = threading.Lock()
        self.accept_thread: Optional[threading.Thread] = None

        # Networking & Quiz Metrics
        self.total_connections: int = 0
        self.messages_sent: int = 0
        self.messages_received: int = 0
        self.questions_sent: int = 0
        self.answers_received: int = 0
        self.completed_quizzes: int = 0

        # Quiz Manager Reference
        if quiz_manager is not None:
            self.quiz_manager = quiz_manager
        else:
            from backend.quiz.quiz_manager import quiz_manager_instance
            self.quiz_manager = quiz_manager_instance

    def start(self, run_in_background: bool = False) -> None:
        """
        Initializes the TCP socket, binds to host:port, begins listening,
        and starts the client acceptance loop.
        """
        try:
            # 1. Create IPv4 TCP socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # 2. Set socket option SO_REUSEADDR to permit fast restarts without TIME_WAIT conflicts
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # 3. Bind socket to host IP and port
            self.server_socket.bind((self.host, self.port))
            
            # 4. Listen for incoming client connections (backlog = 10 pending connections)
            self.server_socket.listen(10)
            self.is_running = True

            logger.info("==================================================")
            logger.info("   NETQUIZ MULTI-USER TCP SERVER INITIALIZED")
            logger.info("==================================================")
            logger.info(f"[SERVER] Address: {self.host}:{self.port}")
            logger.info(f"[SERVER] Protocol: TCP (SOCK_STREAM)")
            logger.info(f"[SERVER] Address Family: IPv4 (AF_INET)")
            logger.info(f"[SERVER] Listening for incoming connections...")
            logger.info("==================================================")

            if run_in_background:
                self.accept_thread = threading.Thread(
                    target=self._accept_loop,
                    name="Thread-TCP-Accept",
                    daemon=True
                )
                self.accept_thread.start()
            else:
                self._accept_loop()

        except Exception as e:
            logger.error(f"[SERVER ERROR] Failed to start TCP server on {self.host}:{self.port}: {e}")
            self.stop()
            raise

    def _accept_loop(self) -> None:
        """
        Continuous loop that accepts incoming TCP connections and spawns
        a dedicated ClientHandler thread for each connection.
        """
        while self.is_running and self.server_socket:
            try:
                # 5. accept() blocks until a new client establishes TCP connection
                client_sock, client_addr = self.server_socket.accept()
                
                with self.lock:
                    self.total_connections += 1

                logger.info(f"[CONNECTION] New client connection from {client_addr[0]}:{client_addr[1]}")

                # 6. Spawn a dedicated thread for concurrent handling
                handler = ClientHandler(
                    client_socket=client_sock,
                    client_address=client_addr,
                    server=self
                )
                
                with self.lock:
                    self.clients[handler.connection_id] = handler

                handler.start()

                logger.info(
                    f"[SERVER] Active Clients: {len(self.clients)} | "
                    f"Total Connections: {self.total_connections}"
                )

            except OSError:
                # Occurs when server_socket is closed during stop()
                break
            except Exception as e:
                if self.is_running:
                    logger.error(f"[SERVER ERROR] Error accepting client connection: {e}")

    def unregister_client(self, connection_id: str) -> None:
        """
        Removes a disconnected client from the active client registry.
        """
        with self.lock:
            if connection_id in self.clients:
                del self.clients[connection_id]
        
        logger.info(f"[SERVER] Active Clients remaining: {len(self.clients)}")

    def record_message_sent(self) -> None:
        """Thread-safe counter increment for outgoing messages."""
        with self.lock:
            self.messages_sent += 1

    def record_message_received(self) -> None:
        """Thread-safe counter increment for incoming messages."""
        with self.lock:
            self.messages_received += 1

    def record_question_sent(self) -> None:
        """Thread-safe counter increment for questions sent."""
        with self.lock:
            self.questions_sent += 1

    def record_answer_received(self) -> None:
        """Thread-safe counter increment for answers received."""
        with self.lock:
            self.answers_received += 1

    def record_quiz_completed(self) -> None:
        """Thread-safe counter increment for completed quizzes."""
        with self.lock:
            self.completed_quizzes += 1

    def get_status(self) -> Dict[str, Any]:
        """
        Returns thread-safe snapshot of TCP server status and active clients.
        Used by the FastAPI bridge and Network Monitoring Dashboard.
        """
        with self.lock:
            active_list = [handler.get_info() for handler in self.clients.values()]
            return {
                "is_running": self.is_running,
                "protocol": "TCP",
                "family": "IPv4 (AF_INET)",
                "socket_type": "SOCK_STREAM",
                "host": self.host,
                "port": self.port,
                "active_clients": len(active_list),
                "total_connections": self.total_connections,
                "messages_sent": self.messages_sent,
                "messages_received": self.messages_received,
                "questions_sent": self.questions_sent,
                "answers_received": self.answers_received,
                "completed_quizzes": self.completed_quizzes,
                "clients": active_list
            }

    def stop(self) -> None:
        """
        Gracefully shuts down the TCP server, closes all active client sockets,
        and releases port 5000.
        """
        if not self.is_running and self.server_socket is None:
            return

        logger.info("[SERVER] Shutting down TCP server...")
        self.is_running = False

        # Close all active client connections cleanly
        with self.lock:
            current_clients = list(self.clients.values())
        
        for handler in current_clients:
            try:
                handler.close()
            except Exception:
                pass

        with self.lock:
            self.clients.clear()

        # Close the listening server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None

        logger.info("[SERVER] TCP server stopped. Port released.")


# Module singleton instance for convenient access across the application
tcp_server_instance = TCPServer()


if __name__ == "__main__":
    server = TCPServer()
    try:
        server.start(run_in_background=False)
    except KeyboardInterrupt:
        logger.info("\n[SERVER] Keyboard interrupt received.")
        server.stop()
        sys.exit(0)
