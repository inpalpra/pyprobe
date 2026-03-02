# PyProbe Artifact Verification Makefile

.PHONY: verify-docker build-artifact test-artifact clean help

help:
	@echo "Available commands:"
	@echo "  make verify-docker  - Run full multi-stage verification pipeline (build + isolated tests)"
	@echo "  make build-artifact - Build the wheel in a Docker container and extract to dist/"
	@echo "  make test-artifact  - Run tests against the built wheel in an isolated container"
	@echo "  make clean          - Remove build artifacts (dist, build, egg-info) and Docker images"

verify-docker:
	./scripts/verify-artifact.sh

build-artifact:
	# Build Stage A and extract
	docker build -t pyprobe-build -f docker/build.Dockerfile .
	mkdir -p dist
	rm -rf dist/*
	$(eval CONTAINER_ID := $(shell docker create pyprobe-build))
	docker cp $(CONTAINER_ID):/workspace/dist/. dist/
	docker rm -f $(CONTAINER_ID)
	@echo "✓ Artifact built and extracted to dist/"

test-artifact:
	# Build Stage B and run
	docker build -t pyprobe-test -f docker/test.Dockerfile .
	docker run --rm pyprobe-test
	@echo "✓ Isolated tests passed!"

clean:
	rm -rf dist/ build/ *.egg-info/
	docker rmi pyprobe-build pyprobe-test || true
	@echo "✓ Cleaned up local and Docker artifacts"
