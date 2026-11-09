import { afterEach, describe, expect, it, vi } from "vitest";

import { explainChat } from "@/lib/api";

/** A response whose body arrives in the given pieces, as a server-sent stream would. */
function sse(pieces: string[], type = "text/event-stream") {
  const enc = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const p of pieces) controller.enqueue(enc.encode(p));
      controller.close();
    },
  });
  return new Response(body, { status: 200, headers: { "content-type": type } });
}

const BLANK = String.fromCharCode(10, 10);
const event = (e: object) => `data: ${JSON.stringify(e)}${BLANK}`;

afterEach(() => vi.unstubAllGlobals());

describe("explainChat with streaming", () => {
  it("passes each sentence to onDelta and returns the final reply", async () => {
    const final = { kind: "reply", text: "One. Two.", language: "en" };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        sse([event({ type: "delta", text: "One." }), event({ type: "delta", text: " Two." }), event({ type: "final", result: final })]),
      ),
    );
    const seen: string[] = [];
    const reply = await explainChat("q", "en", [], (t) => seen.push(t));
    expect(seen).toEqual(["One.", " Two."]);
    expect(reply).toEqual(final);
    expect(vi.mocked(fetch).mock.calls[0][0]).toMatch(/\/explain\/chat\/stream$/);
  });

  it("copes with an event split across network chunks", async () => {
    const whole = event({ type: "delta", text: "Split" }) + event({ type: "final", result: { kind: "empty" } });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(sse([whole.slice(0, 9), whole.slice(9, 31), whole.slice(31)])));
    const seen: string[] = [];
    const reply = await explainChat("q", "en", [], (t) => seen.push(t));
    expect(seen).toEqual(["Split"]);
    expect(reply).toEqual({ kind: "empty" });
  });

  it("a lone final event (distress, refusal) calls onDelta never", async () => {
    const final = { kind: "distress", message: "m", helplines: [] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(sse([event({ type: "final", result: final })])));
    const onDelta = vi.fn();
    expect(await explainChat("q", "en", [], onDelta)).toEqual(final);
    expect(onDelta).not.toHaveBeenCalled();
  });

  it("falls back to the plain JSON reply when the server does not stream", async () => {
    const plain = { kind: "reply", text: "ok" };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(plain), { headers: { "content-type": "application/json" } })));
    expect(await explainChat("q", "en", [], vi.fn())).toEqual(plain);
  });

  it("throws when the stream ends without a final event", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(sse([event({ type: "delta", text: "Half" })])));
    await expect(explainChat("q", "en", [], vi.fn())).rejects.toThrow();
  });

  it("throws on an HTTP error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("nope", { status: 500 })));
    await expect(explainChat("q", "en", [], vi.fn())).rejects.toThrow("nope");
  });

  it("without onDelta it uses the plain route", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ kind: "empty" }), { headers: { "content-type": "application/json" } })));
    await explainChat("q", "en", []);
    expect(vi.mocked(fetch).mock.calls[0][0]).toMatch(/\/explain\/chat$/);
  });
});
