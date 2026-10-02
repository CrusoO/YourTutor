import { describe, expect, it } from "vitest";
import { GET } from "../app/api/health/route";

describe("health", () => {
  it("returns ok", async () => {
    const response = GET();
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body).toEqual({ status: "ok", service: "web" });
  });
});
