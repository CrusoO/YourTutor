import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { studentLogin } from "@/lib/api";

const reply = (status: number, body: unknown = {}) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

let calls: Record<string, string>[] = [];
function stub(statuses: number[]) {
  calls = [];
  const queue = [...statuses];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (_url: string, init: RequestInit) => {
      calls.push(JSON.parse(String(init.body)));
      const status = queue.shift() ?? 401;
      return status === 200 ? reply(200, { access_token: "tok" }) : reply(status, { detail: "no" });
    }),
  );
}

beforeEach(() => vi.unstubAllGlobals());
afterEach(() => vi.unstubAllGlobals());

describe("studentLogin", () => {
  it("tries the other name form once after a plain 401", async () => {
    stub([401, 200]);
    await studentLogin("abcd2345", "1234");
    expect(calls).toHaveLength(2);
    expect(calls[0]).toHaveProperty("username");
    expect(calls[1]).toHaveProperty("family_code");
  });

  it("tries the other form after a 404 too", async () => {
    stub([404, 200]);
    await studentLogin("ABC234", "1234");
    expect(calls).toHaveLength(2);
  });

  it.each([423, 429, 500])("never retries or hides a %i", async (status) => {
    stub([status, 200]);
    await expect(studentLogin("abcd2345", "1234")).rejects.toThrow(/no/);
    expect(calls).toHaveLength(1);
  });

  it("gives up after both forms say no", async () => {
    stub([401, 401]);
    await expect(studentLogin("ABC234", "1234")).rejects.toThrow();
    expect(calls).toHaveLength(2);
  });
});
