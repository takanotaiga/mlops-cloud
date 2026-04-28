import { expect, test } from "@playwright/test";
import { waitForHealthyApp } from "../lib/app";

test("system compose exposes healthy UI and core routes", async ({ request }) => {
  await waitForHealthyApp(request);

  const status = await request.get("/api/status");
  await expect(status).toBeOK();
  expect(await status.json()).toMatchObject({ dbOk: true, s3Ok: true });

  for (const path of ["/", "/dataset", "/inference"]) {
    const response = await request.get(path);
    await expect(response, `${path} should return HTTP 200`).toBeOK();
  }
});
