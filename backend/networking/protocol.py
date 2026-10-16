"""
NetQuiz TCP Protocol & Message Framing Module

Academic Concept:
TCP (Transmission Control Protocol) is a connection-oriented, reliable byte-stream protocol.
Unlike UDP, TCP does NOT preserve message boundaries:
- One send() call may be split across multiple TCP segments.
- Multiple send() calls may be coalesced into a single TCP segment (Nagle's algorithm).
- A single recv() call might return a partial message or multiple concatenated messages.

To solve this, NetQuiz implements application-layer message framing using:
NEWLINE-DELIMITED JSON (JSON Lines).
Each JSON object ends with a newline character ('\\n').
"""

import json
import socket
from typing import Any, Dict, List, Optional, Tuple


def send_json(sock: socket.socket, message: Dict[str, Any]) -> None:
    """
    Serializes a Python dictionary to JSON, appends a newline delimiter,
    encodes it to UTF-8 bytes, and sends it completely over the TCP socket.
    
    Academic Concept:
    sock.sendall() continues to send data from the byte buffer until either
    all data has been transmitted or an error occurs. This avoids partial sends.
    """
    serialized = json.dumps(message) + "\n"
    sock.sendall(serialized.encode("utf-8"))


class MessageFramingBuffer:
    """
    Accumulates incoming raw TCP byte streams and extracts complete,
    newline-delimited JSON messages into an internal queue.
    
    Maintains incomplete stream fragments in memory until the terminating
    '\\n' delimiter arrives. Handles packet coalescing where multiple messages
    arrive in a single socket.recv() buffer.
    """
    def __init__(self) -> None:
        self.buffer = ""
        self.queue: List[Tuple[Optional[Dict[str, Any]], Optional[str]]] = []

    def feed(self, data: bytes) -> List[Tuple[Optional[Dict[str, Any]], Optional[str]]]:
        """
        Feeds new raw bytes received from socket.recv().
        Enqueues and returns any newly parsed complete messages.
        """
        # Decode incoming bytes to UTF-8 text (replacing invalid characters safely)
        self.buffer += data.decode("utf-8", errors="replace")
        
        new_messages: List[Tuple[Optional[Dict[str, Any]], Optional[str]]] = []
        
        # Extract complete messages separated by newline delimiter
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip()
            if not line:
                # Skip empty lines
                continue
            
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    item = (parsed, None)
                else:
                    item = (None, "Message payload must be a JSON object (dictionary)")
            except json.JSONDecodeError as e:
                item = (None, f"Invalid JSON format: {str(e)} (raw line: '{line}')")

            self.queue.append(item)
            new_messages.append(item)
                
        return new_messages

    def has_message(self) -> bool:
        """Returns True if one or more complete messages are ready in the queue."""
        return len(self.queue) > 0

    def get_message(self) -> Optional[Tuple[Optional[Dict[str, Any]], Optional[str]]]:
        """Pops and returns the oldest parsed message from the queue, or None if empty."""
        if self.queue:
            return self.queue.pop(0)
        return None
