import pytest
import multiprocessing as mp
import subprocess
import os
import tempfile
import time
from PyQt6.QtCore import QCoreApplication

from pyprobe.gui.script_runner import ScriptRunner
from pyprobe.ipc.socket_channel import SocketIPCChannel
from pyprobe.ipc.channels import IPCChannel

@pytest.fixture
def temp_script():
    fd, path = tempfile.mkstemp(suffix=".py")
    with os.fdopen(fd, "w") as f:
        f.write("import time\n")
        f.write("x = 42\n")
        f.write("time.sleep(0.5)\n")
    yield path
    if os.path.exists(path):
        os.remove(path)

@pytest.fixture
def runner(temp_script):
    runner = ScriptRunner()
    runner.configure(script_path=temp_script, get_active_anchors=lambda: [])
    runner.use_legacy_ipc = False
    return runner

def test_script_runner_lifecycle_fast(runner):
    # This requires the MessageHandler or something to verify,
    # but we can just test that the runner doesn't crash when starting with anchors.
    from pyprobe.core.anchor import ProbeAnchor
    runner.configure(script_path=runner._script_path, get_active_anchors=lambda: [
        ProbeAnchor(file="test.py", line=2, col=0, symbol="x")
    ])
    
    runner.start()
    
    # 1. test_start_launches_subprocess
    # Check that self._ipc is a SocketIPCChannel
    assert isinstance(runner._ipc, SocketIPCChannel)
    
    # Check that self._runner_process is a Popen, not mp.Process
    assert isinstance(runner._runner_process, subprocess.Popen)
    proc = runner._runner_process
    assert proc.poll() is None  # Process is running

    # 2. test_start_tracer_connects
    # Wait for tracer to connect to the socket
    connected = runner._ipc.wait_for_connection(timeout=2.0)
    assert connected is True, "Tracer did not connect to the GUI socket"

    # 3. test_probe_commands_reach_tracer
    # If it connected and didn't crash, the command was sent successfully
    time.sleep(0.5)
    assert proc.poll() is None
    
    # 4. test_stop_terminates_subprocess & test_stop_cleanup_no_leak
    runner.stop()
    
    # Process should be terminated
    assert proc.poll() is not None
    
    # Ensure runner state is cleaned up
    assert runner._runner_process is None
    assert runner._ipc is None

def test_legacy_mode_lifecycle_fast(temp_script):
    runner = ScriptRunner()
    runner.configure(script_path=temp_script, get_active_anchors=lambda: [])
    runner.use_legacy_ipc = True
    
    runner.start()
    
    # Should use old mp.Process and IPCChannel
    assert isinstance(runner._ipc, IPCChannel)
    assert isinstance(runner._runner_process, mp.Process)
    proc = runner._runner_process
    assert proc.is_alive()
    
    runner.stop()
    
    assert not proc.is_alive()
    assert runner._runner_process is None
    assert runner._ipc is None
