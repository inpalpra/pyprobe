"""
Inter-process communication layer with support for both
Queue-based messaging and shared memory for large arrays.
"""

import multiprocessing as mp
from multiprocessing import shared_memory
from typing import Optional, Dict, Any
from dataclasses import dataclass
from queue import Empty, Full
import numpy as np
import threading

from .messages import Message


@dataclass
class SharedArrayHandle:
    """Handle to a numpy array in shared memory."""
    shm_name: str
    dtype: str
    shape: tuple


class IPCChannel:
    """
    Bidirectional IPC channel between GUI and Runner processes.

    Design:
    - Commands (GUI -> Runner): Small messages via Queue
    - Data (Runner -> GUI):
      - Small data via Queue (< 10KB)
      - Large arrays via shared memory
    """

    # Threshold for using shared memory vs queue (10 KB)
    SHARED_MEM_THRESHOLD = 10 * 1024

    def __init__(self, is_gui_side: bool = True):
        """
        Args:
            is_gui_side: True if this is the GUI process, False for runner
        """
        self._is_gui = is_gui_side

        # Command queue: GUI -> Runner
        self._command_queue: mp.Queue = mp.Queue(maxsize=100)

        # Data queue: Runner -> GUI
        self._data_queue: mp.Queue = mp.Queue(maxsize=1000)

        # Shared memory pool for large arrays
        self._shm_pool: Dict[str, shared_memory.SharedMemory] = {}
        self._shm_lock = threading.Lock()

        # Ring buffer index for shared memory naming
        self._shm_idx = 0

    @property
    def command_queue(self) -> mp.Queue:
        """Queue for GUI -> Runner commands."""
        return self._command_queue

    @property
    def data_queue(self) -> mp.Queue:
        """Queue for Runner -> GUI data."""
        return self._data_queue

    def send_command(self, msg: Message, timeout: float = 1.0) -> bool:
        """Send a command from GUI to Runner."""
        try:
            self._command_queue.put(msg, timeout=timeout)
            return True
        except Full:
            return False

    def receive_command(self, timeout: float = 0.1) -> Optional[Message]:
        """Receive a command in the Runner process."""
        try:
            return self._command_queue.get(timeout=timeout)
        except Empty:
            return None

    def send_data(self, msg: Message, timeout: float = 0.1) -> bool:
        """
        Send data from Runner to GUI.
        Automatically uses shared memory for large arrays.
        """
        # Check if payload contains large numpy arrays
        if msg.payload and 'value' in msg.payload:
            value = msg.payload['value']
            if isinstance(value, np.ndarray) and value.nbytes > self.SHARED_MEM_THRESHOLD:
                # Use shared memory for large arrays
                handle = self._put_array_in_shared_mem(value)
                msg.payload['value'] = None  # Don't serialize the array
                msg.payload['shm_handle'] = handle

        try:
            self._data_queue.put(msg, timeout=timeout)
            return True
        except Full:
            return False

    def receive_data(self, timeout: float = 0.01) -> Optional[Message]:
        """
        Receive data in the GUI process.
        Automatically retrieves arrays from shared memory.
        """
        try:
            msg = self._data_queue.get(timeout=timeout)

            # Check if we need to retrieve from shared memory
            if msg.payload and 'shm_handle' in msg.payload:
                handle = msg.payload['shm_handle']
                msg.payload['value'] = self._get_array_from_shared_mem(handle)
                del msg.payload['shm_handle']

            return msg
        except Empty:
            return None

    def _put_array_in_shared_mem(self, arr: np.ndarray) -> SharedArrayHandle:
        """Put a numpy array into shared memory."""
        with self._shm_lock:
            # Create unique name for this array
            name = f"pyprobe_arr_{self._shm_idx}"
            self._shm_idx = (self._shm_idx + 1) % 100  # Ring buffer of 100 slots

            # Clean up old shared memory if exists
            if name in self._shm_pool:
                try:
                    self._shm_pool[name].close()
                    self._shm_pool[name].unlink()
                except Exception:
                    pass

            # Create new shared memory
            shm = shared_memory.SharedMemory(create=True, size=arr.nbytes, name=name)

            # Copy array data to shared memory
            shm_arr = np.ndarray(arr.shape, dtype=arr.dtype, buffer=shm.buf)
            shm_arr[:] = arr[:]

            self._shm_pool[name] = shm

            return SharedArrayHandle(
                shm_name=name,
                dtype=str(arr.dtype),
                shape=arr.shape
            )

    def _get_array_from_shared_mem(self, handle: SharedArrayHandle) -> np.ndarray:
        """Retrieve a numpy array from shared memory."""
        with self._shm_lock:
            if handle.shm_name not in self._shm_pool:
                # Open existing shared memory
                shm = shared_memory.SharedMemory(name=handle.shm_name)
                self._shm_pool[handle.shm_name] = shm
            else:
                shm = self._shm_pool[handle.shm_name]

            # Create numpy array view of shared memory
            arr = np.ndarray(
                handle.shape,
                dtype=np.dtype(handle.dtype),
                buffer=shm.buf
            )

            # Return a copy (so shared memory can be reused)
            return arr.copy()

    def cleanup(self):
        """Clean up shared memory resources."""
        with self._shm_lock:
            for name, shm in self._shm_pool.items():
                try:
                    shm.close()
                    if self._is_gui:
                        shm.unlink()
                except Exception:
                    pass
            self._shm_pool.clear()
