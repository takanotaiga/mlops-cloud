import { expect, test } from "@playwright/test";
import { waitForHealthyApp } from "../lib/app";
import { queryRows } from "../lib/db";

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

test("system compose records CPU hardware metrics", async ({ request }) => {
  await waitForHealthyApp(request);

  await expect.poll(async () => {
    const metrics = await queryRows<any>("SELECT * FROM hardware_metric ORDER BY ts DESC LIMIT 10;");
    return metrics.filter((row) => {
      const system = row?.system;
      return typeof system?.cpu_percent === "number"
        && typeof system?.memory?.total === "number"
        && system.memory.total > 0;
    }).length;
  }, {
    timeout: 60_000,
    intervals: [1_000, 2_000, 5_000],
  }).toBeGreaterThan(0);
});
