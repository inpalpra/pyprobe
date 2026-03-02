import os

def test_ci_version_exists():
    assert os.path.exists(".ci-version")

def test_ci_version_content():
    with open(".ci-version", "r") as f:
        content = f.read().strip()
    assert content == "v1"

def test_ci_dockerfile_exists():
    assert os.path.exists("docker/ci.Dockerfile")

def test_build_ci_image_workflow_exists():
    assert os.path.exists(".github/workflows/build-ci-image.yml")

def test_ci_workflow_uses_ghcr_image():
    with open(".github/workflows/ci.yml", "r") as f:
        content = f.read()
    assert "ghcr.io/inpalpra/pyprobe-ci" in content

def test_release_workflow_uses_ghcr_image():
    with open(".github/workflows/release.yml", "r") as f:
        content = f.read()
    assert "ghcr.io/inpalpra/pyprobe-ci" in content

def test_local_dockerfile_uses_ghcr_image():
    with open("docker/Dockerfile", "r") as f:
        content = f.read()
    assert "ghcr.io/inpalpra/pyprobe-ci" in content
