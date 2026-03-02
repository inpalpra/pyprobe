# PyProbe Unified CI Makefile

CI_VERSION := $(shell cat .ci-version)

.PHONY: verify-docker clean help

help:
	@echo "Available commands:"
	@echo "  make verify-docker  - Build wheel and run tests inside clean Docker container (CI_VERSION=$(CI_VERSION))"
	@echo "  make clean          - Remove local build artifacts (dist, build, egg-info)"

verify-docker:
	docker build --build-arg CI_VERSION=$(CI_VERSION) -t pyprobe-test -f docker/Dockerfile .
	docker run --rm pyprobe-test

clean:
	rm -rf dist/ build/ *.egg-info/
	docker rmi pyprobe-test || true
	@echo "✓ Cleaned up local and Docker artifacts"
