import pytest
import threading
import time
import numpy as np

from pyprobe.ipc.socket_channel import SocketIPCChannel
from pyprobe.ipc.socket_transport import SocketClient, SocketServer
from pyprobe.ipc.wire_protocol import MessageType, encode_message, decode_message
from pyprobe.ipc.channels import IPCChannel
from pyprobe.ipc.messages import Message

class MockTracer:
    def __init__(self, port):
        self.port = port
        self.client = None
        
    def connect(self):
        self.client = SocketClient.connect("127.0.0.1", self.port)
        
    def close(self):
        if self.client:
            self.client.close()

    def receive_command(self):
        frame = self.client.recv_frame()
        return decode_message(frame)

    def send_data(self, msg):
        self.client.send_frame(encode_message(msg))


def test_socket_channel_send_command():
    channel = SocketIPCChannel(is_gui_side=True)
    port = channel.port
    
    # Connect mock tracer
    tracer = MockTracer(port)
    tracer.connect()
    
    # Wait for GUI channel to accept connection
    channel.wait_for_connection(timeout=1.0)
    
    # GUI sends command
    msg = Message(msg_type=MessageType.CMD_PAUSE)
    assert channel.send_command(msg) is True
    
    # Tracer receives command
    received = tracer.receive_command()
    assert received.msg_type == MessageType.CMD_PAUSE
    
    channel.cleanup()
    tracer.close()

def test_socket_channel_receive_data():
    channel = SocketIPCChannel(is_gui_side=True)
    port = channel.port
    
    tracer = MockTracer(port)
    tracer.connect()
    channel.wait_for_connection(timeout=1.0)
    
    # Tracer sends data
    msg = Message(msg_type=MessageType.DATA_SCRIPT_END)
    tracer.send_data(msg)
    
    # GUI receives data
    start = time.time()
    received = None
    while time.time() - start < 1.0:
        received = channel.receive_data(timeout=0)
        if received:
            break
        time.sleep(0.01)
        
    assert received is not None
    assert received.msg_type == MessageType.DATA_SCRIPT_END
    
    channel.cleanup()
    tracer.close()

def test_socket_channel_large_array():
    channel = SocketIPCChannel(is_gui_side=True)
    port = channel.port
    
    tracer = MockTracer(port)
    tracer.connect()
    channel.wait_for_connection(timeout=1.0)
    
    # Tracer sends large array
    large_arr = np.ones(1000000, dtype=np.float64)
    msg = Message(msg_type=MessageType.DATA_PROBE_VALUE, payload={"value": large_arr})
    tracer.send_data(msg)
    
    # GUI receives array
    start = time.time()
    received = None
    while time.time() - start < 2.0:
        received = channel.receive_data(timeout=0)
        if received:
            break
        time.sleep(0.01)
        
    assert received is not None
    assert received.msg_type == MessageType.DATA_PROBE_VALUE
    assert isinstance(received.payload["value"], np.ndarray)
    assert np.array_equal(received.payload["value"], large_arr)
    
    channel.cleanup()
    tracer.close()

def test_socket_channel_cleanup():
    channel = SocketIPCChannel(is_gui_side=True)
    port = channel.port
    
    tracer = MockTracer(port)
    tracer.connect()
    channel.wait_for_connection(timeout=1.0)
    
    # Should not leak threads or connections
    channel.cleanup()
    
    # Try sending after cleanup, should gracefully fail or handle it
    tracer.close()
    
    # Clean up again should be safe
    channel.cleanup()

def test_socket_channel_api_compat():
    # duck typing test
    ipc = IPCChannel(is_gui_side=True)
    sipc = SocketIPCChannel(is_gui_side=True)
    
    for method in ['send_command', 'receive_data', 'cleanup']:
        assert hasattr(sipc, method)
        
    sipc.cleanup()
    ipc.cleanup()
