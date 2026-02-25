import pytest
import numpy as np
import time
import struct
from pyprobe.ipc.wire_protocol import encode_message, decode_message, ProtocolError
from pyprobe.ipc.messages import Message, MessageType

def test_roundtrip_simple_command():
    payload = {"anchor": {"file": "test.py", "line": 10, "var": "x"}}
    msg = Message(msg_type=MessageType.CMD_ADD_PROBE, payload=payload)
    
    encoded = encode_message(msg)
    decoded = decode_message(encoded)
    
    assert decoded.msg_type == msg.msg_type
    assert decoded.payload == msg.payload
    assert abs(decoded.timestamp - msg.timestamp) < 0.001

def test_roundtrip_scalar_data():
    payload = {"value": 42.5}
    msg = Message(msg_type=MessageType.DATA_PROBE_VALUE, payload=payload)
    
    encoded = encode_message(msg)
    decoded = decode_message(encoded)
    
    assert decoded.msg_type == msg.msg_type
    assert decoded.payload == msg.payload

def test_roundtrip_small_array():
    arr = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    payload = {"value": arr}
    msg = Message(msg_type=MessageType.DATA_PROBE_VALUE, payload=payload)
    
    encoded = encode_message(msg)
    decoded = decode_message(encoded)
    
    assert decoded.msg_type == msg.msg_type
    assert np.array_equal(decoded.payload["value"], arr)
    assert decoded.payload["value"].dtype == arr.dtype

def test_roundtrip_large_array():
    # 1M samples complex128
    arr = np.random.randn(1000000) + 1j * np.random.randn(1000000)
    arr = arr.astype(np.complex128)
    
    payload = {"value": arr}
    msg = Message(msg_type=MessageType.DATA_PROBE_VALUE, payload=payload)
    
    encoded = encode_message(msg)
    decoded = decode_message(encoded)
    
    assert decoded.msg_type == msg.msg_type
    assert np.array_equal(decoded.payload["value"], arr)
    assert decoded.payload["value"].dtype == arr.dtype
    assert decoded.payload["value"].shape == arr.shape

def test_roundtrip_batch_message():
    probes = [
        {"anchor": {"var": "x"}, "value": 1.0},
        {"anchor": {"var": "y"}, "value": np.array([1, 2, 3])}
    ]
    msg = Message(msg_type=MessageType.DATA_PROBE_VALUE_BATCH, payload={"probes": probes})
    
    encoded = encode_message(msg)
    decoded = decode_message(encoded)
    
    assert decoded.msg_type == msg.msg_type
    assert decoded.payload["probes"][0] == probes[0]
    assert np.array_equal(decoded.payload["probes"][1]["value"], probes[1]["value"])

def test_roundtrip_all_message_types():
    for mt in MessageType:
        msg = Message(msg_type=mt, payload={"test": "data"})
        encoded = encode_message(msg)
        decoded = decode_message(encoded)
        assert decoded.msg_type == mt
        assert decoded.payload == {"test": "data"}

def test_decode_truncated_bytes_raises():
    msg = Message(msg_type=MessageType.CMD_PAUSE)
    encoded = encode_message(msg)
    
    with pytest.raises(ProtocolError, match="Message truncated"):
        decode_message(encoded[:-5])

def test_decode_garbage_raises():
    with pytest.raises(ProtocolError, match="Invalid magic"):
        decode_message(b"GARBAGE_AND_MORE_GARBAGE")

def test_large_array_performance():
    # 1M complex128 is 16MB
    arr = np.random.randn(1000000) + 1j * np.random.randn(1000000)
    arr = arr.astype(np.complex128)
    msg = Message(msg_type=MessageType.DATA_PROBE_VALUE, payload={"value": arr})
    
    t0 = time.time()
    encoded = encode_message(msg)
    t1 = time.time()
    decoded = decode_message(encoded)
    t2 = time.time()
    
    encode_time = t1 - t0
    decode_time = t2 - t1
    total_time = t2 - t0
    
    print(f"\nEncode time: {encode_time:.4f}s")
    print(f"Decode time: {decode_time:.4f}s")
    print(f"Total time: {total_time:.4f}s")
    
    # Target: < 100ms for 16MB on modern hardware might be tight but should be okay
    # Rearch plan says 50ms.
    assert total_time < 0.2 # Giving some slack for CI

def test_framing_multiple_messages():
    # This is more for the SocketTransport but let's test if we can extract 
    # multiple messages if we were to split them manually
    msg1 = Message(msg_type=MessageType.CMD_PAUSE)
    msg2 = Message(msg_type=MessageType.CMD_RESUME)
    
    buf = encode_message(msg1) + encode_message(msg2)
    
    # Manual extraction (simulating SocketTransport.recv_frame behavior)
    def extract_one(buffer):
        if len(buffer) < 8: return None, buffer
        total_len = struct.unpack('>I', buffer[4:8])[0]
        if len(buffer) < 8 + total_len: return None, buffer
        return buffer[:8+total_len], buffer[8+total_len:]

    frame1, buf = extract_one(buf)
    frame2, buf = extract_one(buf)
    
    assert decode_message(frame1).msg_type == MessageType.CMD_PAUSE
    assert decode_message(frame2).msg_type == MessageType.CMD_RESUME
