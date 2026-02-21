import socket
import struct
import threading
from typing import Optional, Tuple

class ConnectionClosed(Exception):
    """Raised when the socket connection is closed by the peer or due to an error."""
    pass

class SocketTransport:
    """Framed message transport over a connected socket."""
    
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self._send_lock = threading.Lock()
        
    def send_frame(self, data: bytes):
        """Send a length-prefixed frame."""
        length_prefix = struct.pack(">I", len(data))
        with self._send_lock:
            try:
                self.sock.sendall(length_prefix + data)
            except (BrokenPipeError, ConnectionResetError, OSError) as e:
                raise ConnectionClosed(str(e)) from e

    def _recv_exact(self, n: int) -> bytes:
        data = bytearray()
        while len(data) < n:
            try:
                chunk = self.sock.recv(n - len(data))
            except (ConnectionResetError, OSError) as e:
                raise ConnectionClosed(str(e)) from e
            if not chunk:
                raise ConnectionClosed("Socket closed by peer")
            data.extend(chunk)
        return bytes(data)

    def recv_frame(self) -> bytes:
        """Receive a length-prefixed frame."""
        try:
            prefix = self._recv_exact(4)
        except ConnectionClosed:
            raise
            
        (length,) = struct.unpack(">I", prefix)
        return self._recv_exact(length)
        
    def close(self):
        """Close the transport."""
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()


class SocketServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 0, unix_path: Optional[str] = None):
        self.unix_path = unix_path
        if unix_path:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.bind(unix_path)
            self.is_unix = True
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Allow address reuse if explicitly bound to a port, 
            # though port=0 generally gets an unused ephemeral port.
            if port != 0:
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((host, port))
            self.is_unix = False
            
        self.sock.listen(5)
        
    def address(self) -> Tuple[str, int]:
        """Returns (host, port) or (unix_path, 0)."""
        if self.is_unix:
            return (self.unix_path, 0)
        return self.sock.getsockname()
        
    def accept(self, timeout: float = 5.0) -> SocketTransport:
        self.sock.settimeout(timeout)
        try:
            conn, _ = self.sock.accept()
        except socket.timeout:
            raise TimeoutError("Accept timed out")
        except OSError as e:
            raise ConnectionError(str(e)) from e
            
        # Reset timeout for connected socket so recv blocks indefinitely by default
        conn.settimeout(None)
        return SocketTransport(conn)
        
    def close(self):
        """Close the server socket."""
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()


class SocketClient:
    @staticmethod
    def connect(host: str = "127.0.0.1", port: int = 0, unix_path: Optional[str] = None, timeout: float = 5.0) -> SocketTransport:
        if unix_path:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            try:
                sock.connect(unix_path)
            except OSError as e:
                sock.close()
                raise ConnectionError(str(e)) from e
            sock.settimeout(None)
            return SocketTransport(sock)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            try:
                sock.connect((host, port))
            except OSError as e:
                sock.close()
                raise ConnectionError(str(e)) from e
            sock.settimeout(None)
            return SocketTransport(sock)
