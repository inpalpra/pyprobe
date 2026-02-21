import os
import sys
import threading
import time
import pytest

from pyprobe.ipc.socket_transport import SocketServer, SocketClient, SocketTransport, ConnectionClosed

@pytest.fixture
def server():
    srv = SocketServer(host="127.0.0.1", port=0)
    yield srv
    srv.close()

def test_server_accepts_connection(server):
    host, port = server.address()
    
    def client_thread():
        client = SocketClient.connect(host, port)
        client.close()

    t = threading.Thread(target=client_thread)
    t.start()
    
    transport = server.accept(timeout=2.0)
    assert isinstance(transport, SocketTransport)
    transport.close()
    t.join()

def test_send_recv_small(server):
    host, port = server.address()
    payload = b"A" * 100

    def client_thread():
        client = SocketClient.connect(host, port)
        client.send_frame(payload)
        client.close()

    t = threading.Thread(target=client_thread)
    t.start()

    transport = server.accept(timeout=2.0)
    received = transport.recv_frame()
    assert received == payload

    transport.close()
    t.join()

def test_send_recv_large(server):
    host, port = server.address()
    payload = os.urandom(10 * 1024 * 1024)  # 10 MB

    def client_thread():
        client = SocketClient.connect(host, port)
        client.send_frame(payload)
        client.close()

    t = threading.Thread(target=client_thread)
    t.start()

    transport = server.accept(timeout=5.0)
    received = transport.recv_frame()
    assert received == payload

    transport.close()
    t.join()

def test_bidirectional(server):
    host, port = server.address()
    client_payload = b"client_data"
    server_payload = b"server_data"

    def client_thread():
        client = SocketClient.connect(host, port)
        client.send_frame(client_payload)
        received = client.recv_frame()
        assert received == server_payload
        client.close()

    t = threading.Thread(target=client_thread)
    t.start()

    transport = server.accept(timeout=2.0)
    received = transport.recv_frame()
    assert received == client_payload
    transport.send_frame(server_payload)

    transport.close()
    t.join()

def test_client_disconnect_detected(server):
    host, port = server.address()

    def client_thread():
        client = SocketClient.connect(host, port)
        client.close()

    t = threading.Thread(target=client_thread)
    t.start()

    transport = server.accept(timeout=2.0)
    t.join()  # ensure client has closed
    
    with pytest.raises(ConnectionClosed):
        transport.recv_frame()
    transport.close()

def test_server_shutdown_detected(server):
    host, port = server.address()

    transport = None
    def accept_thread():
        nonlocal transport
        transport = server.accept(timeout=2.0)
        transport.close()

    t = threading.Thread(target=accept_thread)
    t.start()

    client = SocketClient.connect(host, port)
    t.join()  # ensure server closed transport

    with pytest.raises(ConnectionClosed):
        client.recv_frame()
    client.close()

def test_concurrent_send_recv(server):
    host, port = server.address()
    num_messages = 100
    msg1 = b"th1_data" * 1000
    msg2 = b"th2_data" * 1000
    
    def client_thread():
        client = SocketClient.connect(host, port)
        
        def send1():
            for _ in range(num_messages):
                client.send_frame(msg1)
                
        def send2():
            for _ in range(num_messages):
                client.send_frame(msg2)
                
        t1 = threading.Thread(target=send1)
        t2 = threading.Thread(target=send2)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        client.send_frame(b"EOF")
        client.close()

    t = threading.Thread(target=client_thread)
    t.start()

    transport = server.accept(timeout=2.0)
    msg1_count = 0
    msg2_count = 0
    while True:
        msg = transport.recv_frame()
        if msg == b"EOF":
            break
        elif msg == msg1:
            msg1_count += 1
        elif msg == msg2:
            msg2_count += 1
        else:
            pytest.fail("Corrupted message received")
            
    assert msg1_count == num_messages
    assert msg2_count == num_messages

    transport.close()
    t.join()

@pytest.mark.skipif(sys.platform == "win32", reason="Unix domain sockets not supported on Windows")
def test_unix_socket_transport():
    import tempfile
    import os
    fd, socket_path = tempfile.mkstemp(prefix="pyprobe_", dir="/tmp")
    os.close(fd)
    os.remove(socket_path)
    
    srv = SocketServer(unix_path=socket_path)
    
    payload = b"unix_socket_test"
    
    def client_thread():
        client = SocketClient.connect(unix_path=socket_path)
        client.send_frame(payload)
        client.close()

    t = threading.Thread(target=client_thread)
    t.start()

    transport = srv.accept(timeout=2.0)
    assert transport.recv_frame() == payload
    
    transport.close()
    t.join()
    srv.close()
    
    if os.path.exists(socket_path):
        try:
            os.remove(socket_path)
        except OSError:
            pass

def test_connect_timeout():
    start_time = time.time()
    # Connecting to a non-listening port raises ConnectionRefusedError usually immediately.
    # Wait timeout is mostly for IP drop scenarios, but we will test standard behaviour
    # Or try a 192.0.2.x test if we want actual TimeoutError, but ConnectionError suffices
    with pytest.raises(ConnectionError):
        # 45678 is assumed free. Wait 2 sec.
        SocketClient.connect("127.0.0.1", port=45678, timeout=2.0)
    duration = time.time() - start_time
    assert duration < 2.5
