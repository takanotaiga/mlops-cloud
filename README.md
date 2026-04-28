# MLOps Cloud

## Development Compose

`docker-compose.dev.yml` はローカル開発向けの構成です。

- `../mlops-cloud-ui` と `../mlops-cloud-backend` をコンテナへマウント
- `mlops-cloud-*` 系サービス（UI/Backend）はローカルの Dockerfile から build
- `surrealdb` / `minio` は通常どおり pull
- SurrealDB は `memory` モードで起動
- MinIO は `tmpfs` (`/data`) を使って起動
- `cloud-ui` は `npm run dev` で起動（TTY + stdin open）

上記により、DB/Object Storage のデータはコンテナ起動ごとにリセットされます。

## 起動方法

`mlops-cloud` ディレクトリで実行:

```bash
docker compose -f docker-compose.dev.yml up
```

GPU ワーカー (`mlx-backend`, `cv-backend`) も起動する場合:

```bash
docker compose -f docker-compose.dev.yml --profile gpu up
```

停止:

```bash
docker compose -f docker-compose.dev.yml down
```

## Phase 1 E2E

UI E2E tests live in `e2e/`.

```bash
docker compose -f e2e/compose.phase1.yml up --build --abort-on-container-exit --exit-code-from e2e e2e
```

The E2E compose builds `cloud-ui` from `../mlops-cloud-ui/Dockerfile` and builds the test runner from `e2e/Dockerfile`. SurrealDB and MinIO use disposable in-memory/tmpfs storage.
