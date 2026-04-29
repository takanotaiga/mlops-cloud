import SurrealDb from "surrealdb";
import { env } from "./env";

export function extractRows<T = any>(res: any): T[] {
  if (!Array.isArray(res)) return [];
  if (Array.isArray(res[0])) return res[0] as T[];
  if (Array.isArray(res[0]?.result)) return res[0].result as T[];
  return res.flatMap((r: any) => (Array.isArray(r?.result) ? r.result : Array.isArray(r) ? r : [])) as T[];
}

export function thingToString(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "object" && "tb" in value && "id" in value) {
    const thing = value as { tb: string; id: unknown };
    const id = typeof thing.id === "object" && thing.id !== null
      ? ((thing.id as any).toString?.() ?? JSON.stringify(thing.id))
      : String(thing.id);
    return `${thing.tb}:${id}`;
  }
  return String(value);
}

export async function withDb<T>(fn: (client: any) => Promise<T>): Promise<T> {
  const client = new (SurrealDb as any)();
  try {
    await client.connect(env.surreal.url);
    try {
      await client.signin({ username: env.surreal.user, password: env.surreal.pass });
    } catch {
      await client.signin({ user: env.surreal.user, pass: env.surreal.pass });
    }
    await client.use({ namespace: env.surreal.ns, database: env.surreal.db });
    return await fn(client);
  } finally {
    try {
      await client.close();
    } catch {
      // ignore close errors during test cleanup
    }
  }
}

export async function queryRows<T = any>(sql: string, vars?: Record<string, unknown>): Promise<T[]> {
  return withDb(async (client) => extractRows<T>(await client.query(sql, vars)));
}

export async function resetDb(): Promise<void> {
  await withDb(async (client) => {
    for (const table of ["annotation", "label", "inference_job", "training_job", "hls_job", "hls_playlist", "hls_segment", "merge_group", "hardware_metric", "file"]) {
      await client.query(`DELETE ${table}`);
    }
  });
}
