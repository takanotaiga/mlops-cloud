import { expect, test } from "@playwright/test";
import { waitForHealthyApp } from "../lib/app";

test("health check connects to SurrealDB and MinIO", async ({ request }) => {
  await waitForHealthyApp(request);

  const response = await request.get("/api/status");
  expect(response.ok()).toBeTruthy();
  await expect(response).toBeOK();
  expect(await response.json()).toMatchObject({
    dbOk: true,
    s3Ok: true,
  });
});
