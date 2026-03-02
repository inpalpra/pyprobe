import os

def test_ci_version_exists():
    assert os.path.exists(".ci-version")

def test_ci_version_content():
    with open(".ci-version", "r") as f:
        content = f.read().strip()
    assert content == "v1"

def test_ci_dockerfile_exists():
    assert os.path.exists("docker/ci.Dockerfile")
