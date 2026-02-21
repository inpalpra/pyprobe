"""
Socket-based IPC channel for communication between GUI and pyprobe_tracer.
Replaces multiprocess Queue + SharedMemory with a pure socket transport.
"""

import threading
import queue
from typing import Optional

from pyprobe.logging import get_logger
logger = get_logger(__name__)

from .messages import Message
from .socket_transport import SocketServer, SocketTransport, ConnectionClosed
from .wire_protocol import encode_message, decode_message


class SocketIPCChannel:
    """
    Socket-backed drop-in replacement for IPCChannel.
    GUI acts as the server, Tracer connects as a client.
    """
    def __init__(self, is_gui_side: bool = True):
        self._is_gui = is_gui_side
        
        self._command_queue = queue.Queue(maxsize=100)
        self._data_queue = queue.Queue(maxsize=1000)
        
        self._server: Optional[SocketServer] = None
        self._transport: Optional[SocketTransport] = None
        self._port = 0
        
        self._shutdown_event = threading.Event()
        self._accept_thread = None
        self._recv_thread = None
        
        if self._is_gui:
            self._server = SocketServer(port=0)
            _, self._port = self._server.address()
            self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self._accept_thread.start()
        
    @property
    def port(self) -> int:
        return self._port

    @property
    def command_queue(self) -> queue.Queue:
        return self._command_queue

    @property
    def data_queue(self) -> queue.Queue:
        return self._data_queue
        
    def wait_for_connection(self, timeout: float = 5.0) -> bool:
        """Wait until the tracer client connects."""
        import time
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self._transport is not None:
                return True
            time.sleep(0.01)
        return False
        
    def _accept_loop(self):
        try:
            # We only expect one connection from the tracer
            transport = self._server.accept(timeout=10000.0) # Long timeout, subprocess might take time
            self._transport = transport
            logger.debug(f"Tracer connected to SocketIPCChannel on port {self._port}")
            self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
            self._recv_thread.start()
        except TimeoutError:
            logger.error("Timeout waiting for tracer connection")
        except Exception as e:
            if not self._shutdown_event.is_set():
                logger.error(f"Error accepting connection: {e}")
                
    def _recv_loop(self):
        while not self._shutdown_event.is_set() and self._transport:
            try:
                frame = self._transport.recv_frame()
                msg = decode_message(frame)
                if self._is_gui:
                    self._data_queue.put(msg)
                else:
                    self._command_queue.put(msg)
            except ConnectionClosed:
                break
            except Exception as e:
                logger.error(f"Error receiving data: {e}")
                break

    def send_command(self, msg: Message, timeout: float = 1.0) -> bool:
        if not self._is_gui:
            raise RuntimeError("Tracer shouldn't send_command")
        if not self._transport:
            return False
            
        try:
            self._transport.send_frame(encode_message(msg))
            return True
        except ConnectionClosed:
            return False

    def receive_data(self, timeout: float = 0.01) -> Optional[Message]:
        if not self._is_gui:
            raise RuntimeError("Tracer shouldn't receive_data")
            
        try:
            if timeout == 0:
                return self._data_queue.get(block=False)
            else:
                return self._data_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def cleanup(self):
        self._shutdown_event.set()
        
        if self._transport:
            self._transport.close()
            self._transport = None
            
        if self._server:
            self._server.close()
            self._server = None
            
        # Drain queues
        while not self._data_queue.empty():
            try:
                self._data_queue.get_nowait()
            except queue.Empty:
                break
