# MLOps Cloud E2E

This directory contains compose-based E2E tests for the multi-repository development workspace.

All MLOps Cloud app images are built from local Dockerfiles. SurrealDB, MinIO, and Playwright base images are pulled dependencies. SurrealDB uses `memory`; MinIO uses `tmpfs`, so DB and object-storage state reset with each compose run.

Fixtures are stored in `fixtures/`:

- `test-image.jpeg`: image upload and object preview tests.
- `test-video.mp4`: seeded video inference and GPU pipeline tests.

Always run commands from the `mlops-cloud` repository root.

## Phase 1 UI E2E

Builds `cloud-ui` from `../../mlops-cloud-ui/Dockerfile` and runs Playwright against UI/API flows.

```bash
docker compose -f e2e/compose.phase1.yml up --build --abort-on-container-exit --exit-code-from e2e e2e
docker compose -f e2e/compose.phase1.yml down -v
```

Current expected result: `7 passed, 3 skipped`.

Executed tests include:

- `/api/status` health
- dataset upload and object detail
- dataset/object soft delete
- inference job creation from a seeded video dataset
- `/api/db/query` security allowlist behavior
- removed `/terminal` and `/docs*` routes are not exposed

Skipped tests are `test.fixme` for unsettled product behavior:

- inference creation rejects multiple selected datasets with a visible reason
- inference creation rejects datasets without exactly one video with a visible reason
- training creation is disabled or marked preview while no training worker exists

## Phase 2 Backend Integration

Builds `backend-test` from `../../mlops-cloud-backend/Dockerfile.base` and mounts pytest tests from `e2e/phase2`.

```bash
docker compose -f e2e/compose.phase2.yml up --build --abort-on-container-exit --exit-code-from backend-test backend-test
docker compose -f e2e/compose.phase2.yml down -v
```

Covered areas:

- env config loading and legacy fallback behavior
- SurrealDB query helper extraction and record id handling
- HLS and inference job status transitions
- cleaner dead-file and orphan-annotation DB/S3 cleanup
- inference runner validation for zero, multiple, no-video, multiple-video, and valid single-video dataset inputs

## Phase 3 System E2E

Builds `cloud-ui`, starts SurrealDB and MinIO, and runs a smoke check against `/api/status`, `/`, `/dataset`, and `/inference`.

```bash
docker compose -f e2e/compose.phase3.yml up --build --abort-on-container-exit --exit-code-from system-e2e system-e2e
docker compose -f e2e/compose.phase3.yml down -v
```

## Phase 4 GPU E2E

Builds `mlx-backend` and `cv-backend` from `../../mlops-cloud-backend/Dockerfile.gpu`, seeds one video plus a SAM2 bbox annotation, runs the real `samurai-ulr` inference pipeline, and verifies:

- `inference_job.status` reaches `Completed`
- major progress steps complete
- inference result video and parquet artifacts are registered in DB and exist in S3
- result video is HLS encoded by `cv-backend`
- HLS playlist and segments are registered and stored
- inference UI pages return HTTP 200

This is intended for manual/nightly/self-hosted GPU execution.

```bash
docker compose -f e2e/compose.phase4.yml up --build --abort-on-container-exit --exit-code-from phase4-test phase4-test
docker compose -f e2e/compose.phase4.yml down -v
```

Optional overrides:

```bash
PHASE4_TIMEOUT_SECONDS=7200 docker compose -f e2e/compose.phase4.yml up --build --abort-on-container-exit --exit-code-from phase4-test phase4-test
PHASE4_REQUIRE_SCHEMA_JSON=1 docker compose -f e2e/compose.phase4.yml up --build --abort-on-container-exit --exit-code-from phase4-test phase4-test
```

## Cleanup

Use `down -v` after each run to remove disposable DB/S3 state. This avoids carrying state between phases.
