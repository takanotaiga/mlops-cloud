export const env = {
  baseUrl: process.env.BASE_URL || "http://127.0.0.1:3000",
  surreal: {
    url: process.env.SURREAL_URL || "ws://127.0.0.1:8000/rpc",
    ns: process.env.SURREAL_NS || "mlops_e2e",
    db: process.env.SURREAL_DB || "cloud_ui",
    user: process.env.SURREAL_USER || "root",
    pass: process.env.SURREAL_PASS || "root",
  },
  s3: {
    endpoint: process.env.MINIO_ENDPOINT_INTERNAL || "http://127.0.0.1:9000",
    region: process.env.MINIO_REGION || "us-east-1",
    accessKeyId: process.env.MINIO_ACCESS_KEY_ID || "minioadmin",
    secretAccessKey: process.env.MINIO_SECRET_ACCESS_KEY || "minioadmin",
    bucket: process.env.MINIO_BUCKET || "mlops-e2e",
    forcePathStyle: (process.env.MINIO_FORCE_PATH_STYLE || "true").toLowerCase() !== "false",
  },
} as const;
