#!/usr/bin/env python3
import os
import subprocess
import sys
import shutil
import tempfile

def run(cmd, cwd=None, env=None):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        return False
    return True

def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dist_dir = os.path.join(repo_root, "dist")
    
    # 1. Clean previous builds
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    
    # 2. Build wheel
    print("--- Building Wheel ---")
    if not run(["uv", "build"], cwd=repo_root):
        sys.exit(1)
    
    # Find the built wheel
    wheels = [f for f in os.listdir(dist_dir) if f.endswith(".whl")]
    if not wheels:
        print("No wheel found in dist/")
        sys.exit(1)
    wheel_path = os.path.join(dist_dir, wheels[0])
    print(f"Built wheel: {wheel_path}")
    
    # 3. Create fresh venv
    temp_dir = tempfile.mkdtemp(prefix="pyprobe_verify_")
    venv_dir = os.path.join(temp_dir, "venv")
    print(f"--- Creating fresh venv in {venv_dir} ---")
    if not run(["uv", "venv", venv_dir]):
        sys.exit(1)
    
    # Determine python and pip paths
    if sys.platform == "win32":
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        venv_python = os.path.join(venv_dir, "bin", "python")
    
    # 4. Install wheel
    print("--- Installing wheel ---")
    if not run(["uv", "pip", "install", "--python", venv_python, wheel_path]):
        sys.exit(1)
    
    # 5. Run tests
    # We run tests from a DIFFERENT directory to simulate "not in repo root"
    test_run_dir = os.path.join(temp_dir, "test_run")
    os.makedirs(test_run_dir)
    
    # Copy tests directory to the temp run dir
    shutil.copytree(os.path.join(repo_root, "tests"), os.path.join(test_run_dir, "tests"))
    # Copy regression directory because tests expect it (and we want to see it fail)
    # Actually, if we WANT to see the failure, we should maybe NOT copy it if the test expects it in repo root.
    # But the tests currently FAIL because they check for pyprobe/__main__.py in CWD.
    
    print("--- Running Tests from non-repo directory ---")
    # Run specific failing tests identified in logs
    test_files = [
        "tests/report/test_report_schema.py",
        "tests/test_constellation_verify_fast.py",
        "tests/test_e2e_capture_pipeline_fast.py"
    ]
    
    env = os.environ.copy()
    env["PYTHONPATH"] = "" # Ensure we don't pick up the local repo
    
    # Run pytest
    cmd = [venv_python, "-m", "pytest"] + test_files + ["-v"]
    run(cmd, cwd=test_run_dir, env=env)
    
    print(f"\nReproduction environment kept at: {temp_dir}")
    print(f"To clean up: rm -rf {temp_dir}")

if __name__ == "__main__":
    main()
