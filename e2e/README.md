# MLOps Cloud E2E

This directory contains all implemented test phases from `../../E2E_TEST_PLAN.md`.

All MLOps Cloud app images are built from local Dockerfiles. SurrealDB and MinIO are service dependencies and are pulled as base services. SurrealDB uses `memory`; MinIO uses `tmpfs`, so DB and object-storage state reset with each compose run.

Fixtures are stored in `fixtures/`:

- `test-image.jpeg` is used for image upload and object preview tests.
- `test-video.mp4` is used for seeded video inference job tests.

## Phase 1 UI E2E

Builds `cloud-ui` from `../../mlops-cloud-ui/Dockerfile` and runs Playwright against UI flows.

```bash
docker compose -f e2e/compose.phase1.yml up --build --abort-on-container-exit --exit-code-from e2e e2e
docker compose -f e2e/compose.phase1.yml down -v
```

## Phase 2 Backend Integration

Builds `backend-test` from `../../mlops-cloud-backend/Dockerfile.base` and mounts pytest tests from `e2e/phase2`.

```bash
docker compose -f e2e/compose.phase2.yml up --build --abort-on-container-exit --exit-code-from backend-test backend-test
docker compose -f e2e/compose.phase2.yml down -v
```

Covered now:

- env config loading and legacy fallback behavior
- SurrealDB query helper extraction and record id handling
- HLS and inference job status transitions
- cleaner dead-file and orphan-annotation DB/S3 cleanup
- inference runner validation for zero, multiple, no-video, multiple-video, and valid single-video dataset inputs

## Phase 3 System E2E

Builds `cloud-ui` from `../../mlops-cloud-ui/Dockerfile`, starts SurrealDB and MinIO, and runs a system smoke against `/api/status`, `/`, `/dataset`, and `/inference`.

```bash
docker compose -f e2e/compose.phase3.yml up --build --abort-on-container-exit --exit-code-from system-e2e system-e2e
docker compose -f e2e/compose.phase3.yml down -v
```

## Phase 4 GPU E2E

Builds `mlx-backend` and `cv-backend` from `../../mlops-cloud-backend/Dockerfile.gpu`, seeds one video plus a SAM2 bbox annotation, runs the real `samurai-ulr` inference pipeline, and verifies:

- `inference_job.status` reaches `Completed`
- inference result video and parquet artifacts are registered in DB and exist in S3
- the result video is HLS encoded by `cv-backend`
- the inference UI pages return HTTP 200

This is intended for manual/nightly/self-hosted GPU execution. It requires the NVIDIA container runtime and enough time for SAMURAI/RT-DETR processing.

```bash
docker compose -f e2e/compose.phase4.yml up --build --abort-on-container-exit --exit-code-from phase4-test phase4-test
docker compose -f e2e/compose.phase4.yml down -v
```

Optional environment overrides:

```bash
PHASE4_TIMEOUT_SECONDS=7200 docker compose -f e2e/compose.phase4.yml up --build --abort-on-container-exit --exit-code-from phase4-test phase4-test
PHASE4_REQUIRE_SCHEMA_JSON=1 docker compose -f e2e/compose.phase4.yml up --build --abort-on-container-exit --exit-code-from phase4-test phase4-test
```
