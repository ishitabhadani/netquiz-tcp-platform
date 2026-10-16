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
                parsed_items = self.framing_buffer.feed(data)
                
                for message, error in parsed_items:
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
        """
        return {
            "connection_id": self.connection_id,
            "student_name": self.student_name or "Joining...",
            "ip": self.client_address[0],
            "port": self.client_address[1],
            "connected_at": self.connected_at,
            "status": "connected" if self.is_active else "disconnected"
        }
