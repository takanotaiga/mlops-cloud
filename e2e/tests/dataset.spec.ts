import { expect, test } from "@playwright/test";
import { encodeBase64Utf8, uniqueName, waitForHealthyApp } from "../lib/app";
import { queryRows, resetDb, thingToString } from "../lib/db";
import { env } from "../lib/env";
import { imageFixture } from "../lib/fixtures";
import { emptyBucket, objectExists, putObject } from "../lib/s3";

test.beforeEach(async ({ request }) => {
  await waitForHealthyApp(request);
  await resetDb();
  await emptyBucket();
});

test("uploads an image dataset, opens object detail, and soft deletes the object", async ({ page }) => {
  const dataset = uniqueName("e2e-image");
  const fileName = imageFixture.name;

  await page.goto("/dataset/upload");
  await page.getByPlaceholder("Write here").fill(dataset);
  await page.locator('input[type="file"]').setInputFiles({
    name: fileName,
    mimeType: imageFixture.mimeType,
    buffer: imageFixture.buffer,
  });
  await expect(page.getByText(fileName)).toBeVisible();

  await page.getByRole("button", { name: /Upload to cloud/i }).click();
  await expect(page.getByText(/Upload Complete/i)).toBeVisible({ timeout: 30_000 });

  const rows = await queryRows<any>("SELECT * FROM file WHERE dataset == $dataset", { dataset });
  expect(rows).toHaveLength(1);
  expect(rows[0]).toMatchObject({
    dataset,
    name: fileName,
    key: `${dataset}/${fileName}`,
    bucket: env.s3.bucket,
    mime: imageFixture.mimeType,
  });
  expect(await objectExists(`${dataset}/${fileName}`)).toBe(true);

  await page.goto("/dataset");
  await expect(page.getByText(dataset)).toBeVisible();
  await page.getByText(dataset).click();
  await expect(page.getByText(fileName)).toBeVisible();
  await page.getByText(fileName).click();
  await expect(page.locator('img[alt="preview"]')).toBeVisible();

  await page.getByRole("button", { name: "Remove" }).first().click();
  await page.getByRole("dialog").getByRole("button", { name: "Remove" }).click();

  const fileId = thingToString(rows[0].id);
  await expect.poll(async () => {
    const deleted = await queryRows<any>("SELECT dead FROM file WHERE id == <record> $id", { id: fileId });
    return deleted[0]?.dead;
  }).toBe(true);
});

test("opens a seeded dataset and object detail", async ({ page }) => {
  const dataset = uniqueName("e2e-seeded");
  const fileName = imageFixture.name;
  const key = `${dataset}/${fileName}`;

  await emptyBucket();
  await putObject(key, imageFixture.buffer, imageFixture.mimeType);
  await queryRows(
    "CREATE file CONTENT { dataset: $dataset, name: $name, key: $key, bucket: $bucket, mime: $mime, size: $size, uploadedAt: time::now() }",
    { dataset, name: fileName, key, bucket: env.s3.bucket, mime: imageFixture.mimeType, size: imageFixture.buffer.byteLength },
  );

  await page.goto(`/dataset/opened-dataset?d=${encodeBase64Utf8(dataset)}`);
  await expect(page.getByText(fileName)).toBeVisible();
});
