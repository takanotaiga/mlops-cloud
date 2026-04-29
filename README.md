# MLOps Cloud

MLOps Cloud の統合 compose / E2E リポジトリです。アプリ本体の実装は兄弟リポジトリにあります。

| Path | Role |
|---|---|
| `../mlops-cloud-ui` | Next.js UI and API routes |
| `../mlops-cloud-backend` | Python workers for HLS, inference, cleaner, metrics |
| `../mlops-cloud-updater` | Release/update helper |
| `e2e/` | Compose-based E2E tests |

## Development Compose

`docker-compose.dev.yml` はローカル開発向けです。

- UI/backend source をコンテナへ mount
- MLOps Cloud app images はローカル Dockerfile から build
- SurrealDB は `memory`
- MinIO は `tmpfs`
- 起動ごとに DB/Object Storage はリセット
- UI は `npm run dev` で起動し、TTY/stdin を有効化

```bash
docker compose -f docker-compose.dev.yml up --build
```

GPU worker も起動する場合:

```bash
docker compose -f docker-compose.dev.yml --profile gpu up --build
```

停止:

```bash
docker compose -f docker-compose.dev.yml down
```

## Service URLs

| URL | Service |
|---|---|
| http://localhost:3000 | cloud-ui |
| http://localhost:8000 | SurrealDB |
| http://localhost:9000 | MinIO S3 API |
| http://localhost:9001 | MinIO Console |

Default local credentials:

- SurrealDB: `root` / `root`, namespace `mlops`, database `cloud_ui`
- MinIO: `minioadmin` / `minioadmin`, bucket `mlops-datasets`

## E2E

All E2E lives under `e2e/`. See `../E2E_TEST_RUNBOOK.md` for detailed operation notes.

Phase1 UI:

```bash
docker compose -f e2e/compose.phase1.yml up --build --abort-on-container-exit --exit-code-from e2e e2e
docker compose -f e2e/compose.phase1.yml down -v
```

Phase2 backend integration:

```bash
docker compose -f e2e/compose.phase2.yml up --build --abort-on-container-exit --exit-code-from backend-test backend-test
docker compose -f e2e/compose.phase2.yml down -v
```

Phase3 system smoke:

```bash
docker compose -f e2e/compose.phase3.yml up --build --abort-on-container-exit --exit-code-from system-e2e system-e2e
docker compose -f e2e/compose.phase3.yml down -v
```

Phase4 GPU pipeline:

```bash
docker compose -f e2e/compose.phase4.yml up --build --abort-on-container-exit --exit-code-from phase4-test phase4-test
docker compose -f e2e/compose.phase4.yml down -v
```

Phase4 requires NVIDIA container runtime and a compatible GPU.

## Current E2E Notes

- Phase1 currently reports `7 passed, 3 skipped`.
- Skipped Phase1 tests are `test.fixme` for unsettled UI/training constraints:
  - multiple dataset inference rejection
  - dataset video count rejection
  - training creation disabled/preview without a worker
- Security tests for `/api/db/query` run and should pass.
- Phase3 checks CPU hardware metrics from `hm-backend`.
- Phase4 checks GPU hardware metrics from GPU-enabled `hm-backend`.
- Phase2/3/4 are expected to have no skips when their environment requirements are met.

## Image Policy

- `cloud-ui` builds from `../mlops-cloud-ui/Dockerfile`.
- backend base services build from `../mlops-cloud-backend/Dockerfile.base`.
- GPU services build from `../mlops-cloud-backend/Dockerfile.gpu`.
- SurrealDB / MinIO / Playwright base images are pulled.
