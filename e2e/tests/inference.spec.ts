import { expect, test } from "@playwright/test";
import { uniqueName, waitForHealthyApp } from "../lib/app";
import { queryRows, resetDb } from "../lib/db";
import { env } from "../lib/env";
import { videoFixture } from "../lib/fixtures";
import { emptyBucket, putObject } from "../lib/s3";

test.beforeEach(async ({ request }) => {
  await waitForHealthyApp(request);
  await resetDb();
  await emptyBucket();
});

test("creates an inference job from a seeded video dataset", async ({ page }) => {
  const dataset = uniqueName("e2e-video");
  const jobName = uniqueName("e2e-inference");
  const fileName = videoFixture.name;
  const key = `${dataset}/${fileName}`;

  await putObject(key, videoFixture.buffer, videoFixture.mimeType);
  await queryRows(
    "CREATE file CONTENT { dataset: $dataset, name: $name, key: $key, bucket: $bucket, mime: $mime, size: $size, encode: 'video-none', uploadedAt: time::now() }",
    { dataset, name: fileName, key, bucket: env.s3.bucket, mime: videoFixture.mimeType, size: videoFixture.buffer.byteLength },
  );

  await page.goto("/inference/create");
  await page.getByPlaceholder("my-inference-job").fill(jobName);
  await page.getByLabel(dataset).check({ force: true });

  await page.getByRole("combobox").nth(0).click();
  await page.getByRole("option", { name: "One Shot Object Detection" }).click();
  await page.getByRole("combobox").nth(1).click();
  await page.getByRole("option", { name: /SAMURAI ULR/i }).click();

  await page.getByRole("button", { name: "Start" }).click();
  await expect(page).toHaveURL(/\/inference\/opened-job/);

  const rows = await queryRows<any>("SELECT * FROM inference_job WHERE name == $name", { name: jobName });
  expect(rows).toHaveLength(1);
  expect(rows[0]).toMatchObject({
    name: jobName,
    status: "ProcessWaiting",
    taskType: "one-shot-object-detection",
    model: "samurai-ulr",
    modelSource: "internet",
    datasets: [dataset],
  });
});

test("creates a T260 ULR inference job from a seeded video dataset", async ({ page }) => {
  const dataset = uniqueName("e2e-video");
  const jobName = uniqueName("e2e-t260-inference");
  const fileName = videoFixture.name;
  const key = `${dataset}/${fileName}`;

  await putObject(key, videoFixture.buffer, videoFixture.mimeType);
  await queryRows(
    "CREATE file CONTENT { dataset: $dataset, name: $name, key: $key, bucket: $bucket, mime: $mime, size: $size, encode: 'video-none', uploadedAt: time::now() }",
    { dataset, name: fileName, key, bucket: env.s3.bucket, mime: videoFixture.mimeType, size: videoFixture.buffer.byteLength },
  );

  await page.goto("/inference/create");
  await page.getByPlaceholder("my-inference-job").fill(jobName);
  await page.getByLabel(dataset).check({ force: true });

  await page.getByRole("combobox").nth(0).click();
  await page.getByRole("option", { name: "One Shot Object Detection" }).click();
  await page.getByRole("combobox").nth(1).click();
  await page.getByRole("option", { name: /T260 ULR/i }).click();

  await page.getByRole("button", { name: "Start" }).click();
  await expect(page).toHaveURL(/\/inference\/opened-job/);

  const rows = await queryRows<any>("SELECT * FROM inference_job WHERE name == $name", { name: jobName });
  expect(rows).toHaveLength(1);
  expect(rows[0]).toMatchObject({
    name: jobName,
    status: "ProcessWaiting",
    taskType: "one-shot-object-detection",
    model: "t260-ulr",
    modelSource: "internet",
    inferenceBackend: "pytorch-fp16",
    datasets: [dataset],
  });
});

test.fixme("inference creation rejects multiple selected datasets with a visible reason", async () => {
  // Product behavior is still permissive. Enable this once the UI validation is implemented.
});

test.fixme("inference creation rejects datasets without exactly one video with a visible reason", async () => {
  // Product behavior is still permissive. Enable this once the UI validation is implemented.
});

test.fixme("training creation is disabled or marked preview while no training worker exists", async () => {
  // Product behavior currently creates a waiting training_job without a worker.
});
