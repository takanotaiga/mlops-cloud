import { APIRequestContext, expect } from "@playwright/test";

export async function waitForHealthyApp(request: APIRequestContext): Promise<void> {
  await expect.poll(async () => {
    const response = await request.get("/api/status", { timeout: 5_000 }).catch(() => null);
    if (!response || !response.ok()) return null;
    const body = await response.json();
    return body.dbOk === true && body.s3Ok === true;
  }, {
    timeout: 90_000,
    intervals: [1_000, 2_000, 5_000],
  }).toBe(true);
}

export function encodeBase64Utf8(input: string): string {
  return Buffer.from(input, "utf8").toString("base64");
}

export function uniqueName(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}
