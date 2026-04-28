import { test } from "@playwright/test";

test.fixme("SQL proxy rejects unauthenticated and unsafe arbitrary SQL", async () => {
  // /api/db/query currently accepts arbitrary SQL. This becomes an active regression test
  // after the proxy is replaced by authenticated, operation-specific APIs.
});
