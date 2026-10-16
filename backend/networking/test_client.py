"""
NetQuiz Standalone TCP Test Client

Academic Concepts Demonstrated:
1. Client socket creation with socket.AF_INET and socket.SOCK_STREAM.
2. socket.connect((host, port)): Initiates TCP 3-way handshake with server.
3. Message framing: Sends newline-delimited JSON messages.
4. Robust receiving: Accumulates stream fragments until newline delimiter.
5. Graceful termination: TCP connection teardown via shutdown() and close().
"""

import argparse
import socket
import sys
import time
from typing import Any, Dict, Optional

from backend.config import TCP_SERVER_HOST, TCP_SERVER_PORT
from backend.networking.protocol import MessageFramingBuffer, send_json


class QuizTCPClient:
    """
    TCP Client representing a student participating in NetQuiz.
    """
    def __init__(self, host: str = TCP_SERVER_HOST, port: int = TCP_SERVER_PORT) -> None:
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.framing_buffer = MessageFramingBuffer()
        self.connection_id: Optional[str] = None
        self.student_name: Optional[str] = None

    def connect(self) -> bool:
        """
        Establishes a TCP connection with the NetQuiz server.
        """
        print(f"[CLIENT] Connecting to {self.host}:{self.port}...")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Connect triggers the TCP 3-way handshake (SYN -> SYN-ACK -> ACK)
            self.sock.connect((self.host, self.port))
            print(f"[CLIENT] Connected successfully to {self.host}:{self.port}")
            return True
        except ConnectionRefusedError:
            print(f"[CLIENT ERROR] Could not connect: Server is offline at {self.host}:{self.port}")
            return False
        except Exception as e:
            print(f"[CLIENT ERROR] Connection failed: {e}")
            return False

    def send(self, message: Dict[str, Any]) -> None:
        """Sends a JSON message framed with newline."""
        if not self.sock:
            raise RuntimeError("Client is not connected.")
        send_json(self.sock, message)

    def receive_message(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        Receives bytes from socket until at least one complete message is parsed.
        """
        if not self.sock:
            return None

        self.sock.settimeout(timeout)
        try:
            while True:
                # Check if buffer already has a complete message
                data = self.sock.recv(4096)
                if not data:
                    print("[CLIENT] Connection closed by server.")
                    return None

                parsed_items = self.framing_buffer.feed(data)
                for msg, err in parsed_items:
                    if err:
                        print(f"[CLIENT ERROR] Server sent malformed response: {err}")
                    elif msg:
                        return msg
        except socket.timeout:
            print("[CLIENT ERROR] Timed out waiting for server response.")
            return None
        except Exception as e:
            print(f"[CLIENT ERROR] Error receiving: {e}")
            return None

    def join(self, student_name: str) -> bool:
        """
        Sends join request and waits for join_ack.
        """
        self.student_name = student_name
        print(f"[CLIENT] Sending join request for '{student_name}'...")
        self.send({
            "type": "join",
            "student_name": student_name
        })

        response = self.receive_message()
        if response and response.get("type") == "join_ack":
            self.connection_id = response.get("connection_id")
            print(f"[CLIENT] Server: {response.get('message')}")
            print(f"[CLIENT] Connection ID: {self.connection_id}")
            return True
        else:
            print(f"[CLIENT] Unexpected response: {response}")
            return False

    def ping(self) -> bool:
        """Sends a ping message and waits for pong."""
        print("[CLIENT] Sending ping...")
        self.send({"type": "ping"})
        response = self.receive_message()
        if response and response.get("type") == "pong":
            print(f"[CLIENT] Server responded: PONG (Connection ID: {response.get('connection_id')})")
            return True
        else:
            print(f"[CLIENT] Ping failed, got: {response}")
            return False

    def send_raw(self, raw_bytes: bytes) -> None:
        """Sends raw bytes directly to test server robustness against malformed streams."""
        if not self.sock:
            raise RuntimeError("Client is not connected.")
        self.sock.sendall(raw_bytes)

    def disconnect(self) -> None:
        """Sends disconnect message and cleanly closes socket."""
        if self.sock:
            print("[CLIENT] Disconnecting...")
            try:
                self.send({"type": "disconnect"})
                # Wait briefly for ack
                self.receive_message(timeout=1.0)
            except Exception:
                pass
            self.close()

    def close(self) -> None:
        """Closes the socket."""
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
            print("[CLIENT] Socket closed.")


def main():
    parser = argparse.ArgumentParser(description="NetQuiz TCP Test Client")
    parser.add_argument("name", nargs="?", default="Ishita", help="Student name")
    parser.add_argument("--ping", action="store_true", help="Send a ping test after joining")
    parser.add_argument("--stay", type=int, default=0, help="Seconds to stay connected before exiting")
    parser.add_argument("--malformed", action="store_true", help="Send malformed JSON to test server resilience")
    args = parser.parse_args()

    client = QuizTCPClient()
    if not client.connect():
        sys.exit(1)

    try:
        if args.malformed:
            print("[CLIENT] Sending intentionally malformed JSON bytes...")
            client.send_raw(b"{bad_json_not_formatted\n")
            resp = client.receive_message()
            print(f"[CLIENT] Server handled malformed payload: {resp}")
        else:
            if client.join(args.name):
                if args.ping:
                    client.ping()

                if args.stay > 0:
                    print(f"[CLIENT] Staying connected for {args.stay} seconds...")
                    time.sleep(args.stay)
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
