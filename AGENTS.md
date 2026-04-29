# AGENTS.md

このリポジトリは MLOps Cloud の統合 compose と E2E テストを管理します。UI / backend の実装本体は兄弟リポジトリ `../mlops-cloud-ui` と `../mlops-cloud-backend` にあります。

## 責務

- 本番寄り compose: `docker-compose.yml`
- 開発 compose: `docker-compose.dev.yml`
- E2E compose / tests: `e2e/`
- リリース時の統合入口

## 開発 compose

```bash
docker compose -f docker-compose.dev.yml up --build
```

GPU worker も使う場合:

```bash
docker compose -f docker-compose.dev.yml --profile gpu up --build
```

停止:

```bash
docker compose -f docker-compose.dev.yml down
```

開発 compose の特徴:

- `../mlops-cloud-ui` と `../mlops-cloud-backend` を mount します。
- `cloud-ui` は Dockerfile から build し、`npm run dev` で起動します。
- backend は `Dockerfile.base` / `Dockerfile.gpu` から build します。
- SurrealDB は `memory`、MinIO は `tmpfs` です。起動ごとに DB/S3 はリセットされます。
- `mlx-backend` / `cv-backend` は GPU profile です。

## E2E

E2E は全て `e2e/` に集約します。UI repo や backend repo に分散させないでください。

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

Phase4 は NVIDIA container runtime と十分な GPU リソースが必要です。PRごとの必須テストにはしません。

## 現在の期待値

- Phase1: `6 passed, 3 skipped`
- Phase2: skip なし
- Phase3: skip なし
- Phase4: skip なし。ただし GPU 環境依存

Phase1 の skip は未実装ではなく、仕様未確定箇所を `test.fixme` で明示したものです。

## Docker image 方針

- MLOps Cloud app image はローカル Dockerfile から build します。
- SurrealDB / MinIO / Playwright base image は pull で構いません。
- 古い `Dockerfile.cv` / `Dockerfile.mlx` 参照を追加しないでください。現在は `Dockerfile.base` / `Dockerfile.gpu` です。

## 作業ルール

- main へ直接 commit しないでください。
- compose サービス名、env、E2E 実行手順を変更した場合は `README.md`, `e2e/README.md`, ワークスペース直下の `E2E_TEST_RUNBOOK.md` も更新してください。
- E2E 実行後は必ず `down -v` で片付けてください。
