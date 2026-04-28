import { expect, test } from "@playwright/test";
import { uniqueName, waitForHealthyApp } from "../lib/app";
import { queryRows, resetDb } from "../lib/db";
import { env } from "../lib/env";
import { imageFixture } from "../lib/fixtures";

test.beforeEach(async ({ request }) => {
  await waitForHealthyApp(request);
  await resetDb();
});

test("browser requests cannot execute arbitrary raw SQL through the DB proxy", async ({ page }) => {
  const dataset = uniqueName("security");
  await queryRows(
    "CREATE file CONTENT { dataset: $dataset, name: $name, key: $key, bucket: $bucket, mime: $mime, size: $size, uploadedAt: time::now() }",
    {
      dataset,
      name: imageFixture.name,
      key: `${dataset}/${imageFixture.name}`,
      bucket: env.s3.bucket,
      mime: imageFixture.mimeType,
      size: imageFixture.buffer.byteLength,
    },
  );

  await page.goto("/");
  const rejected = await page.evaluate(async () => {
    const res = await fetch("/api/db/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sql: "DELETE file", vars: {} }),
    });
    return { status: res.status, body: await res.json().catch(() => ({})) };
  });

  expect(rejected.status).toBe(403);
  expect(String(rejected.body.error)).toContain("Raw SQL");

  const rows = await queryRows("SELECT * FROM file WHERE dataset == $dataset", { dataset });
  expect(rows).toHaveLength(1);
});

test("DB proxy only accepts allowlisted operations with validated input", async ({ page }) => {
  await page.goto("/");

  const unknown = await page.evaluate(async () => {
    const res = await fetch("/api/db/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operation: "deleteEverything", vars: {} }),
    });
    return { status: res.status, body: await res.json().catch(() => ({})) };
  });
  expect(unknown.status).toBe(403);
  expect(String(unknown.body.error)).toContain("not allowed");

  const invalidVars = await page.evaluate(async () => {
    const res = await fetch("/api/db/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operation: "datasetCheckExists", vars: { dataset: ["not", "a", "string"] } }),
    });
    return { status: res.status, body: await res.json().catch(() => ({})) };
  });
  expect(invalidVars.status).toBe(400);
  expect(String(invalidVars.body.error)).toContain("Invalid variable");

  const allowed = await page.evaluate(async () => {
    const res = await fetch("/api/db/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operation: "datasetsListFiles", vars: {} }),
    });
    return { status: res.status, ok: res.ok };
  });
  expect(allowed).toEqual({ status: 200, ok: true });
});
