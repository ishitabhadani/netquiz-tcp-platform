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
from typing import Any, Dict, List, Optional, Tuple

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
        First drains any queued messages that arrived together in a previous TCP segment.
        """
        if not self.sock:
            return None

        # Check if previous TCP recv() chunk already buffered complete messages
        if self.framing_buffer.has_message():
            msg, err = self.framing_buffer.get_message()
            if err:
                print(f"[CLIENT ERROR] Server sent malformed response: {err}")
            return msg

        self.sock.settimeout(timeout)
        try:
            while True:
                data = self.sock.recv(4096)
                if not data:
                    print("[CLIENT] Connection closed by server.")
                    return None

                self.framing_buffer.feed(data)
                if self.framing_buffer.has_message():
                    msg, err = self.framing_buffer.get_message()
                    if err:
                        print(f"[CLIENT ERROR] Server sent malformed response: {err}")
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

    def start_quiz(self) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Sends start_quiz request to the server.
        Returns tuple: (quiz_start_payload, first_question_payload)
        """
        print("[CLIENT] Requesting quiz start...")
        self.send({"type": "start_quiz"})
        
        start_ack = self.receive_message()
        if not start_ack or start_ack.get("type") != "quiz_start":
            print(f"[CLIENT ERROR] Expected quiz_start, got: {start_ack}")
            return None, None
            
        print(f"[CLIENT] Quiz Started! Total Questions: {start_ack.get('total_questions')}")
        
        # Server automatically transmits question 1 right after quiz_start
        first_q = self.receive_message()
        if not first_q or first_q.get("type") != "question":
            print(f"[CLIENT ERROR] Expected first question, got: {first_q}")
            return start_ack, None
            
        return start_ack, first_q

    def submit_answer(self, question_id: int, answer: str) -> Optional[Dict[str, Any]]:
        """
        Submits answer option for a specific question ID to the server.
        """
        self.send({
            "type": "answer",
            "question_id": question_id,
            "answer": answer
        })
        return self.receive_message()

    def run_quiz(self, preset_answers: Optional[List[str]] = None, interactive: bool = False) -> Optional[Dict[str, Any]]:
        """
        Plays through the entire quiz.
        Either accepts user terminal inputs (interactive) or feeds preset answers.
        """
        start_info, current_q = self.start_quiz()
        if not current_q:
            return None

        total_q = start_info.get("total_questions", 10)
        ans_idx = 0

        while current_q and current_q.get("type") == "question":
            q_num = current_q.get("question_number")
            q_id = current_q.get("question_id")
            q_text = current_q.get("question")
            options = current_q.get("options", {})

            print(f"\n==================================================")
            print(f" QUESTION {q_num:02d} / {total_q:02d} (ID: {q_id})")
            print(f"==================================================")
            print(f"{q_text}\n")
            for key in sorted(options.keys()):
                print(f"  [{key}] {options[key]}")
            print(f"==================================================")

            if interactive:
                chosen = ""
                while chosen not in ["A", "B", "C", "D"]:
                    chosen = input("\nYour answer (A/B/C/D): ").strip().upper()
            else:
                if preset_answers and ans_idx < len(preset_answers):
                    chosen = preset_answers[ans_idx]
                else:
                    chosen = "B"  # Default fallback option
                print(f"[AUTO] Submitting Answer: {chosen}")
                ans_idx += 1

            result = self.submit_answer(q_id, chosen)
            if not result or result.get("type") != "answer_result":
                print(f"[CLIENT ERROR] Invalid answer response from server: {result}")
                break

            status_str = "CORRECT" if result.get("correct") else "INCORRECT"
            print(f"--> [{status_str}] Correct: {result.get('correct_answer')} | Score: {result.get('current_score')}/{total_q}")
            if result.get("explanation"):
                print(f"    Concept: {result.get('explanation')}")

            if result.get("quiz_completed"):
                # Receive final summary
                end_summary = self.receive_message()
                if end_summary and end_summary.get("type") == "quiz_end":
                    print("\n" + "=" * 50)
                    print("                QUIZ COMPLETE")
                    print("=" * 50)
                    print(f" Student:    {end_summary.get('student_name')}")
                    print(f" Final Score: {end_summary.get('score')} / {end_summary.get('total_questions')}")
                    print(f" Percentage:  {end_summary.get('percentage')}%")
                    print(f" Correct:    {end_summary.get('correct_answers')}")
                    print(f" Incorrect:  {end_summary.get('incorrect_answers')}")
                    print("=" * 50 + "\n")
                    return end_summary
                break
            else:
                # Receive next question
                current_q = self.receive_message()

        return None

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
    parser.add_argument("--quiz", action="store_true", help="Start and participate in the quiz")
    parser.add_argument("--interactive", action="store_true", help="Prompt user for quiz answers in terminal")
    parser.add_argument("--answers", nargs="+", help="Predefined list of answers for automated run (e.g. B C C B ...)")
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

                if args.quiz or args.interactive or args.answers:
                    client.run_quiz(preset_answers=args.answers, interactive=args.interactive)

                if args.stay > 0:
                    print(f"[CLIENT] Staying connected for {args.stay} seconds...")
                    time.sleep(args.stay)
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()

