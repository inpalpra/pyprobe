import json
import struct
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Union
from .messages import Message, MessageType

MAGIC = b'PPRB'  # 0x50 0x50 0x52 0x42

class ProtocolError(Exception):
    """Raised when wire protocol constraints are violated."""
    pass

def _extract_arrays(obj: Any, arrays: List[bytes], array_metadata: List[Dict[str, Any]]) -> Any:
    """
    Recursively find numpy arrays in an object, replace them with placeholders,
    and collect their raw bytes and metadata.
    """
    if isinstance(obj, np.ndarray):
        idx = len(arrays)
        # Ensure it's C-contiguous for reliable tobytes/frombuffer
        if not obj.flags.c_contiguous:
            obj = np.ascontiguousarray(obj)
            
        arrays.append(obj.tobytes())
        array_metadata.append({
            'dtype': str(obj.dtype),
            'shape': list(obj.shape),
            'idx': idx
        })
        return f"__array_idx_{idx}__"
    
    if isinstance(obj, dict):
        return {k: _extract_arrays(v, arrays, array_metadata) for k, v in obj.items()}
    
    if isinstance(obj, list):
        return [_extract_arrays(item, arrays, array_metadata) for item in obj]
    
    if isinstance(obj, tuple):
        return tuple(_extract_arrays(item, arrays, array_metadata) for item in obj)
        
    return obj

def _inject_arrays(obj: Any, arrays: List[np.ndarray]) -> Any:
    """
    Recursively find array placeholders and replace them with actual numpy arrays.
    """
    if isinstance(obj, str) and obj.startswith("__array_idx_") and obj.endswith("__"):
        try:
            idx = int(obj[len("__array_idx_"):-2])
            return arrays[idx]
        except (ValueError, IndexError):
            return obj
            
    if isinstance(obj, dict):
        return {k: _inject_arrays(v, arrays) for k, v in obj.items()}
    
    if isinstance(obj, list):
        return [_inject_arrays(item, arrays) for item in obj]
    
    if isinstance(obj, tuple):
        return tuple(_inject_arrays(item, arrays) for item in obj)
        
    return obj

def encode_message(msg: Message) -> bytes:
    """
    Encode a Message object into a framed byte stream.
    Format: [MAGIC:4][LENGTH:4][JSON_HEADER][\0][BINARY_DATA...]
    """
    binary_blocks = []
    array_metadata = []
    
    # Extract arrays from payload
    serializable_payload = _extract_arrays(msg.payload, binary_blocks, array_metadata)
    
    header = {
        'msg_type': msg.msg_type.name,
        'payload': serializable_payload,
        'timestamp': msg.timestamp,
        'arrays': array_metadata
    }
    
    json_header = json.dumps(header).encode('utf-8') + b'\0'
    
    # Binary data section starts after the JSON header
    payload = json_header + b''.join(binary_blocks)
    
    # Total length of payload (excluding magic and length prefix)
    total_len = len(payload)
    
    return MAGIC + struct.pack('>I', total_len) + payload

def decode_message(data: bytes) -> Message:
    """
    Decode a framed byte stream into a Message object.
    """
    if len(data) < 8:
        raise ProtocolError("Message too short (min 8 bytes)")
        
    magic = data[:4]
    if magic != MAGIC:
        raise ProtocolError(f"Invalid magic: {magic}")
        
    total_len = struct.unpack('>I', data[4:8])[0]
    if len(data) < 8 + total_len:
        raise ProtocolError(f"Message truncated: expected {total_len} payload bytes, got {len(data)-8}")
        
    payload_data = data[8:8+total_len]
    
    # Split header and binary data at the first NUL byte
    try:
        nul_idx = payload_data.index(b'\0')
    except ValueError:
        raise ProtocolError("Missing NUL terminator in JSON header")
        
    json_header_raw = payload_data[:nul_idx]
    binary_data = payload_data[nul_idx+1:]
    
    try:
        header = json.loads(json_header_raw.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ProtocolError(f"Failed to parse JSON header: {e}")
        
    # Reconstruct arrays
    reconstructed_arrays = []
    current_offset = 0
    for meta in header.get('arrays', []):
        dtype = np.dtype(meta['dtype'])
        shape = tuple(meta['shape'])
        # Calculate expected byte size
        size = np.prod(shape) * dtype.itemsize
        
        if current_offset + size > len(binary_data):
            raise ProtocolError(f"Binary data too short for array at index {meta['idx']}")
            
        array_bytes = binary_data[current_offset:current_offset+int(size)]
        arr = np.frombuffer(array_bytes, dtype=dtype).reshape(shape).copy()
        reconstructed_arrays.append(arr)
        current_offset += int(size)
        
    # Inject arrays back into payload
    final_payload = _inject_arrays(header['payload'], reconstructed_arrays)
    
    try:
        msg_type = MessageType[header['msg_type']]
    except KeyError:
        # Fallback for unknown message types (useful for backward compatibility)
        raise ProtocolError(f"Unknown MessageType: {header['msg_type']}")
        
    return Message(
        msg_type=msg_type,
        payload=final_payload,
        timestamp=header['timestamp']
    )
